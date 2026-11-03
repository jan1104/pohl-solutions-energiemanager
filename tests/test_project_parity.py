"""Browser imports and backend imports must agree on the same project files."""

from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from core.project import load_project_json

ROOT = Path(__file__).resolve().parents[1]


def test_browser_and_backend_import_contract():
    if shutil.which("node") is None:
        pytest.skip("Node.js is required for the cross-runtime contract check")
    reference = json.loads((ROOT / "examples/reference-project.json").read_text(encoding="utf-8"))
    simple = json.loads((ROOT / "examples/simple-project.json").read_text(encoding="utf-8"))
    cases = [("reference", reference, True), ("simple", simple, True)]
    numeric = deepcopy(simple)
    numeric["schema_version"] = 1.0
    numeric["devices"][0]["unit_id"] = 3.0
    cases.append(("integral JSON numbers", numeric, True))
    long_endpoint = deepcopy(simple)
    long_endpoint["connections"][0]["host"] = "x" * 300
    cases.append(("shared endpoint text limits", long_endpoint, True))

    def change(name, mutate):
        candidate = deepcopy(reference)
        mutate(candidate)
        cases.append((name, candidate, False))

    change("future version", lambda p: p.update(schema_version=2))
    change("live mode", lambda p: p.update(mode="live"))
    change("duplicate identity", lambda p: p["devices"].append(deepcopy(p["devices"][0])))
    change("missing gateway", lambda p: p["devices"][1].update(via_device_id="absent"))
    change("electrical cycle", lambda p: p["nodes"][0].update(parent_id=p["nodes"][1]["id"]))
    change("invalid battery owner", lambda p: next(d for d in p["devices"] if d["kind"] == "battery").update(parent_id="meter_grid"))
    change("invented single phase", lambda p: p["devices"][0].update(phases=2))
    change("password", lambda p: p["settings"].update(password="must-not-export"))
    change("nested secret", lambda p: p["settings"].update(nested={"api_key": "must-not-export"}))
    change("unknown device field", lambda p: p["devices"][0].update(unrecognized=True))
    change("unmapped modbus", lambda p: p["channels"][0].update(source={"kind": "modbus"}))
    change("duplicate measurement", lambda p: p["measurements"].append({**p["measurements"][0], "id": "duplicate_grid"}))
    change("wrong power unit", lambda p: p["channels"][0].update(unit="kWh"))
    change("gateway cycle", lambda p: p["devices"][0].update(via_device_id="meter_grid"))
    change("invalid endpoint port", lambda p: p["connections"][0].update(port=70000))
    change("sibling branch inclusion", lambda p: p["measurements"][-2]["includes_device_ids"].append("charger_1"))
    payloads = [json.dumps(data, ensure_ascii=False) for _, data, _ in cases]
    payloads += ['{"format":"a","format":"b"}', '{"x":NaN}', "[]"]
    labels = [name for name, _, _ in cases] + ["duplicate JSON key", "NaN", "array root"]
    expected = [valid for _, _, valid in cases] + [False] * 3
    python_results = []
    for payload in payloads:
        try:
            load_project_json(payload)
            python_results.append(True)
        except ValueError:
            python_results.append(False)
    script = """
const fs = require('node:fs');
const model = require('./preview/project-model.js');
const payloads = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(payloads.map(text => {
  try { model.loadProjectJson(text); return true; } catch { return false; }
})));
"""
    result = subprocess.run(["node", "-e", script], input=json.dumps(payloads),
                            capture_output=True, text=True, encoding="utf-8", cwd=ROOT,
                            check=True, timeout=30)
    browser_results = json.loads(result.stdout)
    for label, want, python, browser in zip(labels, expected, python_results, browser_results, strict=True):
        assert python == want, f"Backend: {label} expected {want}"
        assert browser == want, f"Browser: {label} expected {want}"


def test_bundled_browser_examples_match_export_files():
    if shutil.which("node") is None:
        pytest.skip("Node.js is required to check bundled offline example integrity")
    script = "process.stdout.write(JSON.stringify(require('./preview/project-examples.js')));"
    result = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True,
                            encoding="utf-8", check=True, timeout=10)
    bundled = json.loads(result.stdout)
    for key, filename in (("reference", "reference-project.json"), ("simple", "simple-project.json")):
        assert bundled[key] == json.loads((ROOT / "examples" / filename).read_text(encoding="utf-8"))
