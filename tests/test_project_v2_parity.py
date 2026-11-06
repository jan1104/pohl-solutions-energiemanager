"""Staged v2 contract checks; no UI or persistence activation."""

from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from core.project import MAX_BYTES
from core.project_v2 import (_json_budget, configuration_issues_v2, migrate_project_v1_to_v2,
                             validate_project_v2)

ROOT = Path(__file__).resolve().parents[1]


def run_browser(payload):
    if shutil.which("node") is None:
        pytest.skip("Node.js is required for cross-runtime checks")
    script = """
const fs = require('node:fs'), m = require('./preview/project-model.js');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const migrations = input.legacy.map(p => {
  const before = JSON.stringify(p), result = m.migrateProjectV1ToV2(p);
  if (JSON.stringify(p) !== before) throw Error('mutated legacy');
  result.settings.copy_probe = true;
  if (p.settings.copy_probe) throw Error('shared settings');
  delete result.settings.copy_probe;
  return result;
});
const cases = input.cases.map(p => {
  const before = JSON.stringify(p);
  try {
    const result = m.validateProjectV2(p), issues = m.configurationIssuesV2(p);
    if (JSON.stringify(p) !== before) throw Error('mutated input');
    result.name = 'Changed';
    if (p.name === 'Changed') throw Error('shared object');
    let v1Rejected = false;
    try { m.validateProject(p); } catch { v1Rejected = true; }
    if (!v1Rejected) throw Error('v1 accepted v2');
    return {valid: true, issues};
  } catch (error) {
    if (JSON.stringify(p) !== before) throw Error('mutated invalid input');
    return {valid: false};
  }
});
process.stdout.write(JSON.stringify({migrations, cases}));
"""
    result = subprocess.run(["node", "-e", script], input=json.dumps(payload),
                            capture_output=True, encoding="utf-8", cwd=ROOT,
                            check=True, timeout=30)
    return json.loads(result.stdout)


def test_staged_browser_migration_validation_and_issues_match_backend():
    legacy = [json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
              for name in ("simple-project.json", "reference-project.json")]
    empty = {"format": "pohl-energy-project", "schema_version": 1, "id": "test",
             "name": "Test", "mode": "planning_only", "settings": {},
             **{k: [] for k in ("grids", "areas", "nodes", "connections", "devices", "channels", "measurements")}}
    legacy.append(empty)
    migrated = [migrate_project_v1_to_v2(p) for p in legacy]
    draft = deepcopy(migrated[2])
    draft["plants"] = [{"id": "plant", "name": "Anlage", "grid_ids": ["grid"]}]
    draft["grids"] = [{"id": "grid", "name": "Netz"}]
    draft["nodes"] = [{"id": "root", "name": "HAK", "grid_id": "grid", "parent_id": None,
                       "description": "", "location": "📍" * 512, "phases": 3.0, "fuse_a": 63.0}]
    shared = deepcopy(draft)
    shared["plants"].append({"id": "shared", "name": "Zweite Anlage", "grid_ids": ["grid"]})
    separate = deepcopy(draft)
    separate["grids"].append({"id": "other", "name": "Anderer Anschluss"})
    separate["nodes"].append({"id": "other", "name": "Andere Wurzel", "grid_id": "other", "parent_id": None})
    separate["plants"][0]["grid_ids"].append("other")
    cases = [(p, True) for p in [*migrated, draft, shared, separate]]

    def invalid(base, change):
        candidate = deepcopy(base)
        change(candidate)
        cases.append((candidate, False))

    for change in (
        lambda p: p["plants"].append(deepcopy(p["plants"][0])),
        lambda p: p["plants"][0].update(grid_ids=[]),
        lambda p: p["plants"][0].update(grid_ids=["missing"]),
        lambda p: p["plants"][0].update(grid_ids=["grid", "grid"]),
        lambda p: p["plants"][0].update(assignment_confirmed=None),
        lambda p: p["plants"][0].update(location=5),
        lambda p: p["plants"][0].update(name="📍" * 161),
        lambda p: p["nodes"][0].update(fuse_a=True),
        lambda p: p["nodes"][0].update(fuse_a=0),
        lambda p: p["nodes"][0].update(phases=True),
        lambda p: p["nodes"][0].update(phases=2),
        lambda p: p["nodes"][0].update(description="x" * 2049),
        lambda p: p["nodes"][0].update(location="📍" * 513),
        lambda p: p["nodes"][0].update(unrecognized=True),
        lambda p: p["settings"].update(nested={"token": "synthetic"}),
        lambda p: p.update(schema_version=True),
        lambda p: p.update(mode="live"),
    ):
        invalid(draft, change)
    invalid(migrated[0], lambda p: p["areas"][0].update(plant_id="missing"))
    invalid(migrated[0], lambda p: p["measurements"].append({**p["measurements"][0], "id": "duplicate"}))
    mismatch = deepcopy(migrated[0])
    mismatch["plants"].append({"id": "empty", "name": "Ohne Anschluss", "grid_ids": []})
    invalid(mismatch, lambda p: p["areas"][0].update(plant_id="empty"))
    browser = run_browser({"legacy": legacy, "cases": [p for p, _ in cases]})
    assert browser["migrations"] == migrated
    for (data, expected), result in zip(cases, browser["cases"], strict=True):
        before = deepcopy(data)
        if expected:
            assert validate_project_v2(data) == data
            assert result == {"valid": True, "issues": configuration_issues_v2(data)}
        else:
            with pytest.raises(ValueError):
                validate_project_v2(data)
            assert result == {"valid": False}
        assert data == before


def test_v2_json_encoding_boundaries_agree_between_runtimes():
    empty = {"format": "pohl-energy-project", "schema_version": 2, "id": "test",
             "name": "Test", "mode": "planning_only", "settings": {}, "plants": [],
             **{k: [] for k in ("grids", "areas", "nodes", "connections", "devices", "channels", "measurements")}}
    cases = []
    for value in (None, True, False, 0, -0.0, 1.0, 1e-7, 5e-324,
                  9007199254740991, -9007199254740991,
                  {"📍": "ä\n\t\b\f\r\\\"📍"}):
        p = deepcopy(empty)
        p["settings"]["value"] = value
        cases.append((p, True))
    for value in (9007199254740992, -9007199254740992, 1e100,
                  "\ud800", "\udfff", {"\ud800": "invalid key"}):
        p = deepcopy(empty)
        p["settings"]["value"] = value
        cases.append((p, False))
    for value in ("\u001c", "\ufeff", " \u0085\ufeff"):
        p = deepcopy(empty)
        p["name"] = value
        cases.append((p, False))
    for key in ("paſſword", "paßword", "ſecret"):
        p = deepcopy(empty)
        p["settings"][key] = "synthetic"
        cases.append((p, False))
    at_limit = deepcopy(empty)
    at_limit["settings"]["padding"] = ""
    at_limit["settings"]["padding"] = "x" * (MAX_BYTES - _json_budget(at_limit))
    assert _json_budget(at_limit) == MAX_BYTES
    cases.append((at_limit, True))
    over_limit = deepcopy(at_limit)
    over_limit["settings"]["padding"] += "x"
    cases.append((over_limit, False))
    # Reserve equal space for numbers regardless of 1 vs 1.0 serialization.
    assert _json_budget({"n": 1}) == _json_budget({"n": 1.0}) == _json_budget({"n": 5e-324})
    browser = run_browser({"legacy": [], "cases": [p for p, _ in cases]})
    for (p, valid), result in zip(cases, browser["cases"], strict=True):
        assert result["valid"] is valid
        if valid:
            assert validate_project_v2(p) == p
            assert len(json.dumps(p, ensure_ascii=False).encode("utf-8")) <= _json_budget(p)
        else:
            with pytest.raises(ValueError):
                validate_project_v2(p)
