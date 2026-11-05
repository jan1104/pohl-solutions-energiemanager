"""Development-only organization-first project schema. No HA/UI activation.

V1 remains the deployed import/export format. This module is an explicit future
model/migration API; it never silently rewrites saved configuration.
"""

from copy import deepcopy
import json

from .project import (COLLECTIONS, MAX_BYTES, _fields, _id, _json_tree, _number,
                      _ref, _text, _validate_project_v1, validate_project)


def validate_project_v2(data):
    _json_tree(data)
    if len(json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")) > MAX_BYTES:
        raise ValueError("Projekt überschreitet 2 MiB")
    _fields(data, ("format", "schema_version", "id", "name", "mode", "plants", *COLLECTIONS, "settings"), (), "$")
    if type(data["schema_version"]) not in (int, float) or data["schema_version"] != 2:
        raise ValueError("Projektformat 2 erwartet")
    if not isinstance(data["plants"], list) or len(data["plants"]) > 500:
        raise ValueError("Höchstens 500 Anlagen erlaubt")
    if any(not isinstance(data[key], list) for key in COLLECTIONS):
        raise ValueError("Projektobjekte müssen Listen sein")
    if sum(len(data[key]) for key in COLLECTIONS) + len(data["plants"]) > 2500:
        raise ValueError("Höchstens 2500 Objekte einschließlich Anlagen erlaubt")
    base = deepcopy(data)
    base.pop("plants")
    base["schema_version"] = 1
    plants = {}
    for plant in data["plants"]:
        _fields(plant, ("id", "name", "grid_ids"), ("description", "location", "assignment_confirmed"), "$.plants")
        _id(plant["id"], "$.plants.id")
        _text(plant["name"], "$.plants.name")
        if plant["id"] in plants:
            raise ValueError("Doppelte Anlagenkennung")
        plants[plant["id"]] = plant
        _optional_text(plant, "description", 2048)
        _optional_text(plant, "location", 512)
        if "assignment_confirmed" in plant and type(plant["assignment_confirmed"]) is not bool:
            raise ValueError("Anlagenbestätigung muss boolesch sein")
    # Strip only explicitly validated v2 additions before sharing electrical,
    # channel and communication invariants with the strict v1 implementation.
    for area in base["areas"]:
        _fields(area, ("id", "name", "grid_id", "plant_id"), (), "$.areas")
        _ref(area.pop("plant_id"), plants, "$.areas.plant_id")
    for node in base["nodes"]:
        _fields(node, ("id", "name", "grid_id", "parent_id"),
                ("description", "location", "fuse_a", "phases"), "$.nodes")
        _optional_text(node, "description", 2048)
        _optional_text(node, "location", 512)
        if node.get("fuse_a") is not None:
            _number(node["fuse_a"], "$.nodes.fuse_a", positive=True)
        if node.get("phases") is not None:
            _number(node["phases"], "$.nodes.phases", integer=True)
            if node["phases"] not in (1, 3):
                raise ValueError("Anschlussphasen müssen 1 oder 3 sein")
        for key in ("description", "location", "fuse_a", "phases"):
            node.pop(key, None)
    _validate_project_v1(base, require_grid_measurement=False)
    grids = {grid["id"]: grid for grid in data["grids"]}
    linked = set()
    for plant in plants.values():
        if not isinstance(plant["grid_ids"], list):
            raise ValueError("Netzanschlusszuordnung muss eine Liste sein")
        seen = set()
        for grid_id in plant["grid_ids"]:
            _ref(grid_id, grids, "$.plants.grid_ids")
            if grid_id in seen:
                raise ValueError("Doppelter Netzanschluss in Anlage")
            seen.add(grid_id)
        linked.update(seen)
    if linked != grids.keys():
        raise ValueError("Jeder Netzanschluss muss mindestens einer Anlage zugeordnet sein")
    for area in data["areas"]:
        if area["grid_id"] not in plants[area["plant_id"]]["grid_ids"]:
            raise ValueError("Bereich und Anlage müssen den Netzanschluss gemeinsam referenzieren")
    return deepcopy(data)


def _optional_text(row, key, limit):
    value = row.get(key)
    if value is not None and (not isinstance(value, str) or len(value) > limit):
        raise ValueError(f"{key}: Text mit höchstens {limit} Zeichen erwartet")


def migrate_project_v1_to_v2(data):
    """Explicit preview copy; preserve all electrical IDs/values, infer no sites.

    Existing content gets one clearly unconfirmed organizational container, not
    one invented plant per electrical grid or an assumed physical regrouping.
    """
    result = validate_project(data)
    result["schema_version"] = 2
    result["plants"] = []
    if any(result[key] for key in COLLECTIONS):
        result["plants"] = [{"id": "imported_plant", "name": "Importierte Anlage",
                             "grid_ids": [g["id"] for g in result["grids"]],
                             "assignment_confirmed": False,
                             "description": "Organisatorische Zuordnung nach Import bitte prüfen."}]
        for area in result["areas"]:
            area["plant_id"] = "imported_plant"
    return validate_project_v2(result)


def configuration_issues_v2(data):
    """Describe unfinished setup, without asserting planning/data readiness."""
    project = validate_project_v2(data)
    issues = []
    for plant in project["plants"]:
        if plant.get("assignment_confirmed") is False:
            issues.append({"code": "plant_assignment_unconfirmed", "plant_id": plant["id"]})
    nodes = {n["id"]: n for n in project["nodes"]}
    measured = {nodes[m["node_id"]]["grid_id"] for m in project["measurements"] if m["role"] == "grid"}
    for grid in project["grids"]:
        if grid["id"] not in measured:
            issues.append({"code": "grid_measurement_missing", "grid_id": grid["id"]})
    channels = {c["id"]: c for c in project["channels"]}
    for measurement in project["measurements"]:
        if channels[measurement["channel_id"]]["source"]["kind"] == "unconfigured":
            issues.append({"code": "measurement_source_unconfigured",
                           "measurement_id": measurement["id"],
                           "channel_id": measurement["channel_id"]})
    return issues
