"""Development-only organization-first project schema. No HA/UI activation.

V1 remains the deployed import/export format. This module is an explicit future
model/migration API; it never silently rewrites saved configuration.
"""

from copy import deepcopy
import json

from .project import (COLLECTIONS, MAX_BYTES, _fields, _id, _json_tree, _number,
                      _parse_project_json, _project_summary, _ref, _text, _validate_project_v1,
                      validate_project)


MAX_SAFE_NUMBER = 9007199254740991


def _json_budget(value):
    """Stable upper bound on spaced UTF-8 JSON, independent of float spelling.

    Call _json_tree first for depth, secrets and ordinary JSON types. Numbers
    reserve 32 bytes; no persisted numerical value may exceed binary64's exact
    integer range. Unicode must consist of scalar values, including object keys.
    """
    if isinstance(value, str):
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ValueError("JSON enthält einzelne Unicode-Surrogate")
        return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))
    if value is None:
        return 4
    if type(value) is bool:
        return 4 if value else 5
    if type(value) in (int, float):
        if abs(value) > MAX_SAFE_NUMBER:
            raise ValueError("JSON-Zahl überschreitet den sicheren Wertebereich")
        return 32
    if isinstance(value, list):
        return 2 + max(0, len(value) - 1) * 2 + sum(_json_budget(v) for v in value)
    return (2 + max(0, len(value) - 1) * 2
            + sum(_json_budget(key) + 2 + _json_budget(child) for key, child in value.items()))


def validate_project_v2(data):
    _json_tree(data)
    if _json_budget(data) > MAX_BYTES:
        raise ValueError("Projektbudget überschreitet 2 MiB")
    _fields(data, ("format", "schema_version", "id", "name", "mode", "plants", *COLLECTIONS, "settings"), (), "$")
    if type(data["schema_version"]) not in (int, float) or data["schema_version"] != 2:
        raise ValueError("Projektformat 2 erwartet")
    if not isinstance(data["plants"], list) or len(data["plants"]) > 500:
        raise ValueError("Höchstens 500 Anlagen erlaubt")
    if any(not isinstance(data[key], list) for key in COLLECTIONS):
        raise ValueError("Projektobjekte müssen Listen sein")
    if sum(len(data[key]) for key in COLLECTIONS) + len(data["plants"]) > 2500:
        raise ValueError("Höchstens 2500 Objekte einschließlich Anlagen erlaubt")
    # Both runtimes agree on whitespace-only display names (JS also trims BOM).
    for row in [data, *data["plants"], *(r for key in COLLECTIONS for r in data[key])]:
        if isinstance(row, dict) and isinstance(row.get("name"), str):
            if all(ch.isspace() or ch == "\ufeff" for ch in row["name"]):
                raise ValueError("Name darf nicht nur aus Leerraum bestehen")
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
    return _configuration_issues(validate_project_v2(data))


def _configuration_issues(project):
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


def validate_project_document(data):
    """Validate a supported project version without converting it."""
    version = data.get("schema_version") if isinstance(data, dict) else None
    if type(version) in (int, float) and version == 2:
        return validate_project_v2(data)
    return validate_project(data)


def load_project_v2_json(text):
    return validate_project_v2(_parse_project_json(text))


def export_project_v2_json(data):
    """Compact encoding fits the same raw text limit as the import."""
    return json.dumps(validate_project_v2(data), ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def project_summary_v2(data):
    project = validate_project_v2(data)
    return {**_project_summary(project, ("plants", *COLLECTIONS)),
            "schema_version": 2, "issues": _configuration_issues(project)}
