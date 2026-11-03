"""Meaningful format-v1 topology, strict import and offline export tests."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from core.project import export_project_json, load_project_json, project_summary, validate_project


ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return {"format": "pohl-energy-project", "schema_version": 1, "id": "demo", "name": "Demo",
            "mode": "planning_only", "grids": [{"id": "g1", "name": "Netz 1"}],
            "areas": [{"id": "a1", "name": "Halle", "grid_id": "g1"}],
            "nodes": [{"id": "n1", "name": "Netz", "grid_id": "g1", "parent_id": None},
                      {"id": "n2", "name": "Zweig", "grid_id": "g1", "parent_id": "n1"}],
            "connections": [{"id": "c1", "name": "Gateway", "kind": "modbus_tcp_rtu_gateway"}],
            "devices": [{"id": "gateway", "name": "Gateway", "kind": "gateway", "area_id": "a1", "node_id": "n1", "connection_id": "c1"},
                        {"id": "meter", "name": "Zähler", "kind": "meter", "area_id": "a1", "node_id": "n1", "connection_id": "c1", "via_device_id": "gateway", "unit_id": 2},
                        {"id": "wr", "name": "WR", "kind": "hybrid_inverter", "area_id": "a1", "node_id": "n2", "capabilities": []},
                        {"id": "battery", "name": "Batterie", "kind": "battery", "area_id": "a1", "node_id": "n2", "parent_id": "wr"}],
            "channels": [{"id": "p1", "name": "Netzleistung", "device_id": "meter", "quantity": "active_power", "unit": "kW", "phase": "total", "source": {"kind": "unconfigured"}}],
            "measurements": [{"id": "m1", "name": "Netz", "role": "grid", "node_id": "n1", "channel_id": "p1", "includes_device_ids": ["wr", "battery"]}],
            "settings": {}}


def test_copy_roundtrip_and_summary_do_not_mutate():
    data = fixture()
    before = deepcopy(data)
    copied = validate_project(data)
    copied["devices"][0]["name"] = "Anders"
    assert data == before
    assert load_project_json(export_project_json(data)) == data
    summary = project_summary(data)
    assert summary["counts"]["devices"] == 4
    assert len(summary["warnings"]) == 2
    assert data == before


@pytest.mark.parametrize("filename", ["simple-project.json", "reference-project.json"])
def test_shared_examples(filename):
    path = ROOT / "examples" / filename
    data = load_project_json(path.read_text(encoding="utf-8"))
    assert data == load_project_json(export_project_json(data))


@pytest.mark.parametrize("text", ['{"id":1,"id":2}', '{"x":NaN}', '{"x":Infinity}', '{', '[]', 'null'])
def test_malformed_duplicate_and_nonfinite_json(text):
    with pytest.raises(ValueError):
        load_project_json(text)


@pytest.mark.parametrize("mutate,match", [
    (lambda p: p.update(mode="live"), "mode"),
    (lambda p: p.update(schema_version=True), "schema_version"),
    (lambda p: p.update(extra=True), "Unbekannte"),
    (lambda p: p["devices"].append(deepcopy(p["devices"][0])), "Doppelte"),
    (lambda p: p["areas"][0].update(grid_id="missing"), "grid_id"),
    (lambda p: p["nodes"][0].update(parent_id="n2"), "Zyklischer"),
    (lambda p: p["nodes"][1].update(parent_id=None), "Wurzel"),
    (lambda p: p["devices"][0].update(via_device_id="gateway"), "Zyklischer"),
    (lambda p: p["devices"][3].update(parent_id="meter"), "Batterie"),
    (lambda p: p["devices"][2].update(parent_id="gateway"), "Nur Batterien"),
    (lambda p: p["devices"][2].update(capabilities=["switch", "switch"]), "Doppelte"),
    (lambda p: p["devices"][1].update(unit_id=True), "Zahl"),
    (lambda p: p["devices"][1].update(unit_id=248), "Bereich"),
    (lambda p: p["measurements"][0].update(node_id="n2"), "Wurzel"),
    (lambda p: p["measurements"].clear(), "Netzmessung"),
    (lambda p: p["channels"][0].update(quantity="soc", unit="%"), "Wirkleistung"),
    (lambda p: p["settings"].update(nested={"API_KEY": "private"}), "Zugangsdaten"),
    (lambda p: p["settings"].update(actuator_enabled=False), "Steuerfreigaben"),
    (lambda p: p["devices"][0].update(password="secret"), "Zugangsdaten"),
    (lambda p: p["devices"][2].update(max_power_kw=float("nan")), "endlich"),
])
def test_invalid_projects_leave_input_unchanged(mutate, match):
    data = fixture()
    mutate(data)
    before = export_for_comparison(data)
    with pytest.raises(ValueError, match=match):
        validate_project(data)
    assert export_for_comparison(data) == before


def export_for_comparison(data):
    return json.dumps(data, sort_keys=True)


def second_grid(data):
    data["grids"].append({"id": "g2", "name": "Netz 2"})
    data["areas"].append({"id": "a2", "name": "Halle 2", "grid_id": "g2"})
    data["nodes"].append({"id": "n3", "name": "Netz 2", "grid_id": "g2", "parent_id": None})
    data["devices"].append({"id": "meter2", "name": "Zähler 2", "kind": "meter", "area_id": "a2", "node_id": "n3", "connection_id": "c1", "via_device_id": "gateway", "unit_id": 3})
    data["channels"].append({"id": "p2", "name": "Netz 2", "device_id": "meter2", "quantity": "active_power", "unit": "kW", "source": {"kind": "unconfigured"}})
    data["measurements"].append({"id": "m2", "name": "Netz 2", "role": "grid", "node_id": "n3", "channel_id": "p2", "includes_device_ids": []})


def test_gateway_can_serve_separate_grids_but_devices_cannot_be_counted_across():
    data = fixture()
    second_grid(data)
    validate_project(data)
    data["measurements"][1]["includes_device_ids"] = ["wr"]
    with pytest.raises(ValueError, match="fremder Netzanschluss"):
        validate_project(data)


def test_measurement_source_device_cannot_cross_grid():
    data = fixture()
    second_grid(data)
    data["channels"][1]["device_id"] = "meter"
    with pytest.raises(ValueError, match="Messgerät und Messknoten"):
        validate_project(data)


def test_included_device_must_belong_to_measured_subtree():
    data = fixture()
    data["nodes"].append({"id": "sibling", "name": "Anderer Zweig", "grid_id": "g1", "parent_id": "n1"})
    data["devices"].append({"id": "heater", "name": "Heizung", "kind": "heater", "area_id": "a1", "node_id": "sibling"})
    data["channels"].append({"id": "branch_p", "name": "Zweigleistung", "device_id": "meter", "quantity": "active_power", "unit": "kW", "source": {"kind": "unconfigured"}})
    data["measurements"].append({"id": "branch", "name": "WR-Zweig", "role": "branch", "node_id": "n2", "channel_id": "branch_p", "includes_device_ids": ["battery", "wr"]})
    validate_project(data)
    data["measurements"][-1]["includes_device_ids"].append("heater")
    with pytest.raises(ValueError, match="Teilbaums"):
        validate_project(data)


def test_electrical_parent_cannot_cross_grid():
    data = fixture()
    second_grid(data)
    data["nodes"][1]["parent_id"] = "n3"
    with pytest.raises(ValueError, match="anderem Netzanschluss"):
        validate_project(data)


def test_battery_owner_cannot_cross_grid():
    data = fixture()
    second_grid(data)
    data["devices"][3].update(area_id="a2", node_id="n3")
    with pytest.raises(ValueError, match="selben Netzanschluss"):
        validate_project(data)


def test_gateway_connection_must_match_but_area_can_differ():
    data = fixture()
    second_grid(data)
    data["devices"][0].update(area_id="a2", node_id="n3")
    validate_project(data)
    data["connections"].append({"id": "c2", "name": "Zweite", "kind": "mqtt"})
    data["devices"][1]["connection_id"] = "c2"
    with pytest.raises(ValueError, match="dieselbe Verbindung"):
        validate_project(data)


@pytest.mark.parametrize("source", [
    {"kind": "modbus", "address": 1, "function_code": 6, "data_type": "u16"},
    {"kind": "modbus", "address": 1, "function_code": 3},
    {"kind": "modbus", "address": 1, "function_code": 3, "data_type": "u16", "scale": 0},
    {"kind": "mqtt"}, {"kind": "ha"}, {"kind": "unconfigured", "address": 1},
    {"kind": "mqtt", "topic": "valid", "entity_id": "sensor.other"},
])
def test_invalid_sources(source):
    data = fixture()
    data["channels"][0]["source"] = source
    with pytest.raises(ValueError, match="source"):
        validate_project(data)


def test_bounds_and_depth():
    data = fixture()
    data["settings"] = {"large": "x" * (2 * 1024 * 1024)}
    with pytest.raises(ValueError, match="2 MiB"):
        validate_project(data)
    data = fixture()
    cursor = data["settings"]
    for _ in range(30):
        cursor["nested"] = {}
        cursor = cursor["nested"]
    with pytest.raises(ValueError, match="Tiefe"):
        validate_project(data)


def test_duplicate_measurement_channel_rejected():
    data = fixture()
    row = deepcopy(data["measurements"][0])
    row.update(id="other", name="Weitere", role="load", node_id="n2")
    data["measurements"].append(row)
    with pytest.raises(ValueError, match="bereits zugeordnet"):
        validate_project(data)


def test_long_gateway_cycle_and_later_malformed_parent_fail_as_value_errors():
    data = fixture()
    data["devices"][0]["via_device_id"] = "wr"
    data["devices"][2]["via_device_id"] = "gateway"
    with pytest.raises(ValueError, match="Zyklischer"):
        validate_project(data)
    data = fixture()
    data["nodes"].reverse()
    del data["nodes"][1]["grid_id"]
    with pytest.raises(ValueError):
        validate_project(data)


def test_collection_limit_and_optional_nulls():
    data = fixture()
    data["devices"][0].update(model=None, parent_id=None, capabilities=None, phases=None)
    validate_project(data)
    data["grids"] = [{"id": f"g{i}", "name": "Netz"} for i in range(501)]
    with pytest.raises(ValueError, match="500"):
        validate_project(data)


def test_cli_validation_and_atomic_roundtrip(tmp_path):
    source, output = tmp_path / "input.json", tmp_path / "output.json"
    source.write_text(export_project_json(fixture()), encoding="utf-8")
    command = [sys.executable, str(ROOT / "tools" / "project.py")]
    result = subprocess.run([*command, "validate", str(source)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["counts"]["grids"] == 1
    result = subprocess.run([*command, "roundtrip", str(source), "--output", str(output)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert load_project_json(output.read_text(encoding="utf-8")) == fixture()
    original = output.read_bytes()
    source.write_text('{"mode":"live"}', encoding="utf-8")
    result = subprocess.run([*command, "roundtrip", str(source), "--output", str(output)], capture_output=True, text=True)
    assert result.returncode == 2
    assert output.read_bytes() == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ["input.json", "output.json"]

