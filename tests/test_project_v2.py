"""Development schema only: organization before electrical setup, no I/O."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from core.project import validate_project
from core.project_v2 import (configuration_issues_v2, migrate_project_v1_to_v2,
                             validate_project_v2)


def empty():
    return {"format": "pohl-energy-project", "schema_version": 2, "id": "test", "name": "Test",
            "mode": "planning_only", "plants": [], "grids": [], "areas": [], "nodes": [],
            "connections": [], "devices": [], "channels": [], "measurements": [], "settings": {}}


def draft():
    project = empty()
    project["plants"] = [{"id": "plant_a", "name": "Anlage A", "grid_ids": ["grid"]}]
    project["grids"] = [{"id": "grid", "name": "Hauptanschluss"}]
    project["nodes"] = [{"id": "hak", "name": "HAK", "grid_id": "grid", "parent_id": None,
                         "description": "Synthetischer Testanschluss", "location": "Technikraum",
                         "fuse_a": 63, "phases": 3}]
    return project


def legacy(filename="simple-project.json"):
    return json.loads((Path(__file__).resolve().parents[1] / "examples" / filename).read_text(encoding="utf-8"))


def test_project_then_empty_plant_then_unmetered_connection_are_separate_valid_steps():
    project = empty()
    assert validate_project_v2(project) == project
    project["plants"].append({"id": "plant_a", "name": "Erste Anlage", "grid_ids": []})
    assert validate_project_v2(project) == project
    assert not project["grids"] and not project["devices"] and not project["measurements"]
    assert validate_project_v2(draft()) == draft()
    assert configuration_issues_v2(draft()) == [{"code": "grid_measurement_missing", "grid_id": "grid"}]


@pytest.mark.parametrize("filename", ["simple-project.json", "reference-project.json"])
def test_explicit_migration_preserves_every_existing_id_and_electrical_relationship(filename):
    original = legacy(filename)
    before = deepcopy(original)
    migrated = migrate_project_v1_to_v2(original)
    assert original == before and migrated["schema_version"] == 2
    assert len(migrated["plants"]) == 1 and migrated["plants"][0]["assignment_confirmed"] is False
    assert migrated["plants"][0]["grid_ids"] == [g["id"] for g in before["grids"]]
    for key in ("grids", "nodes", "connections", "devices", "channels", "measurements", "settings"):
        assert migrated[key] == before[key]
    for old, new in zip(before["areas"], migrated["areas"], strict=True):
        assert {k: v for k, v in new.items() if k != "plant_id"} == old
    assert {issue["code"] for issue in configuration_issues_v2(migrated)} == {
        "plant_assignment_unconfirmed", "measurement_source_unconfigured"}


def test_empty_legacy_project_does_not_invent_a_plant():
    data = empty()
    data.pop("plants")
    data["schema_version"] = 1
    migrated = migrate_project_v1_to_v2(data)
    assert migrated["plants"] == migrated["grids"] == []


def test_multiple_plants_can_share_one_actual_grid_and_gateway():
    project = draft()
    project["plants"].append({"id": "plant_b", "name": "Anlage B", "grid_ids": ["grid"]})
    project["areas"] = [{"id": "area_a", "name": "A", "grid_id": "grid", "plant_id": "plant_a"},
                        {"id": "area_b", "name": "B", "grid_id": "grid", "plant_id": "plant_b"}]
    project["connections"] = [{"id": "gateway_tcp", "name": "Gemeinsam", "kind": "modbus_tcp_rtu_gateway"}]
    project["devices"] = [{"id": "gw", "name": "Gateway", "kind": "gateway", "area_id": "area_a", "node_id": "hak", "connection_id": "gateway_tcp"},
                          {"id": "meter", "name": "Zähler", "kind": "meter", "area_id": "area_b", "node_id": "hak", "connection_id": "gateway_tcp", "via_device_id": "gw", "unit_id": 2}]
    assert len(validate_project_v2(project)["grids"]) == 1


def test_separate_grids_remain_separate_inside_one_organizational_plant():
    project = draft()
    project["grids"].append({"id": "other", "name": "Zweiter Anschluss"})
    project["nodes"].append({"id": "other_root", "name": "Zweite Wurzel", "grid_id": "other", "parent_id": None})
    project["plants"][0]["grid_ids"].append("other")
    assert {issue["grid_id"] for issue in configuration_issues_v2(project)} == {"grid", "other"}
    assert len(validate_project_v2(project)["grids"]) == 2


@pytest.mark.parametrize("change", [
    lambda p: p["plants"].append(deepcopy(p["plants"][0])),
    lambda p: p["plants"][0].update(grid_ids=["unknown"]),
    lambda p: p["plants"][0].update(grid_ids=["grid", "grid"]),
    lambda p: p["plants"][0].update(grid_ids=[]),
    lambda p: p["plants"][0].update(assignment_confirmed="yes"),
    lambda p: p["plants"][0].update(location=42),
    lambda p: p["nodes"][0].update(fuse_a=0),
    lambda p: p["nodes"][0].update(fuse_a=True),
    lambda p: p["nodes"][0].update(phases=2),
    lambda p: p["nodes"][0].update(description=42),
    lambda p: p["nodes"][0].update(unrecognized=True),
    lambda p: p["settings"].update(password="synthetic"),
    lambda p: p.update(schema_version=True),
])
def test_invalid_v2_input_never_mutates_existing_data(change):
    project = draft()
    change(project)
    before = deepcopy(project)
    with pytest.raises(ValueError):
        validate_project_v2(project)
    assert project == before


def test_area_requires_existing_plant_and_explicit_grid_membership():
    project = draft()
    project["plants"].append({"id": "unlinked", "name": "Noch leer", "grid_ids": []})
    project["areas"] = [{"id": "area", "name": "Bereich", "grid_id": "grid", "plant_id": "missing"}]
    with pytest.raises(ValueError):
        validate_project_v2(project)
    project["areas"][0]["plant_id"] = "unlinked"
    with pytest.raises(ValueError, match="gemeinsam referenzieren"):
        validate_project_v2(project)


def test_existing_meter_and_role_constraints_are_not_relaxed():
    project = migrate_project_v1_to_v2(legacy())
    duplicate = deepcopy(project["measurements"][0])
    duplicate["id"] = "duplicate"
    project["measurements"].append(duplicate)
    with pytest.raises(ValueError, match="bereits zugeordnet"):
        validate_project_v2(project)


def test_deployed_v1_import_stays_strict_and_rejects_v2():
    with pytest.raises(ValueError):
        validate_project(draft())
    old = legacy()
    old["measurements"] = []
    with pytest.raises(ValueError, match="Netzmessung"):
        validate_project(old)
    assert validate_project(legacy()) == legacy()


def test_validation_returns_detached_copy_and_does_not_interpret_descriptions():
    project = draft()
    project["nodes"][0]["description"] = "Absicherung eventuell anders; nur Notiz"
    project["nodes"][0].pop("fuse_a")
    copied = validate_project_v2(project)
    assert "fuse_a" not in copied["nodes"][0]
    copied["plants"][0]["name"] = "Geändert"
    assert project["plants"][0]["name"] == "Anlage A"
