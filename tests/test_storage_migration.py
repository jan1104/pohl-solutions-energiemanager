"""Explicit migration transactions on temporary databases only."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from threading import Barrier

import pytest

from core.project_migration import commit_project_v2, preview_project_v2
from core.project_v2 import migrate_project_v1_to_v2
from core.storage import SQLiteStorage, StorageConflict, StorageSchemaError


def setup(tmp_path):
    store = SQLiteStorage(tmp_path / "test.sqlite")
    store.initialize()
    module = store.for_module("global", "project", schema_version=1)
    return store, module


def legacy():
    return json.loads((Path(__file__).resolve().parents[1] / "examples/reference-project.json").read_text(encoding="utf-8"))


def test_project_preview_is_read_only_and_commit_preserves_source_on_restart(tmp_path):
    store, module = setup(tmp_path)
    original = legacy()
    module.put("active", original, expected_revision=None)
    provenance = {"status": "migrated_legacy", "legacy_sha256": "synthetic", "legacy_retained": True}
    module.put("migration", provenance, expected_revision=None)
    before = store.path.read_bytes()
    preview = preview_project_v2(module)
    assert store.path.read_bytes() == before
    assert preview.project == migrate_project_v1_to_v2(original)
    preview.project["name"] = "Tampered preview must not be stored"
    new = commit_project_v2(module, expected_revision=preview.source_revision,
                            expected_sha256=preview.source_sha256)
    assert new.schema_version == 2
    assert new.get("active").revision == 2
    assert new.get("active").data == migrate_project_v1_to_v2(original)
    assert new.get("original_v1").data == original
    assert new.get("migration").data == provenance
    assert new.get("project_format_migration").data["source_sha256"] == preview.source_sha256
    reopened = SQLiteStorage(store.path).for_module("global", "project", schema_version=2)
    assert reopened.get("active") == new.get("active")
    with pytest.raises(StorageSchemaError):
        store.for_module("global", "project", schema_version=1)
    for call in (lambda: module.get("active"),
                 lambda: module.put("active", original, expected_revision=1),
                 lambda: module.migrate(2, {"active": (1, original)})):
        with pytest.raises(StorageSchemaError):
            call()


@pytest.mark.parametrize("interference", ["edit", "aba", "backup", "unknown", "metadata"])
def test_project_migration_conflicts_preserve_all_documents(tmp_path, interference):
    store, module = setup(tmp_path)
    original = legacy()
    module.put("active", original, expected_revision=None)
    preview = preview_project_v2(module)
    if interference in ("edit", "aba"):
        changed = {**original, "name": "Concurrent edit"}
        module.put("active", changed, expected_revision=1)
        if interference == "aba":
            module.put("active", original, expected_revision=2)
    else:
        module.put({"backup": "original_v1", "unknown": "unexpected", "metadata": "project_format_migration"}[interference],
                   {"preserve": True}, expected_revision=None)
    before = store.path.read_bytes()
    with pytest.raises(StorageConflict):
        commit_project_v2(module, expected_revision=preview.source_revision,
                         expected_sha256=preview.source_sha256)
    assert store.path.read_bytes() == before
    assert module.get("active").data["schema_version"] == 1


def test_migration_rolls_back_documents_and_schema_when_final_update_fails(tmp_path):
    store, module = setup(tmp_path)
    original = legacy()
    module.put("active", original, expected_revision=None)
    preview = preview_project_v2(module)
    with sqlite3.connect(store.path) as connection:
        connection.execute("CREATE TRIGGER fail_schema BEFORE UPDATE ON module_namespaces BEGIN SELECT RAISE(ABORT, 'injected failure'); END")
    with pytest.raises(sqlite3.IntegrityError, match="injected failure"):
        commit_project_v2(module, expected_revision=preview.source_revision,
                         expected_sha256=preview.source_sha256)
    assert module.get("active").revision == 1
    assert module.get("active").data == original
    assert module.get("original_v1") is None
    assert module.get("project_format_migration") is None


@pytest.mark.parametrize("target", [True, 1, 0, 2.0, 1000000])
def test_invalid_migration_target_preserves_data(tmp_path, target):
    _, module = setup(tmp_path)
    module.put("active", {"n": 1}, expected_revision=None)
    with pytest.raises(ValueError):
        module.migrate(target, {"active": (1, {"n": 2})})
    assert module.get("active").data == {"n": 1}


def test_full_namespace_migration_supports_more_than_one_write_batch_and_isolates_modules(tmp_path):
    store, module = setup(tmp_path)
    unrelated = store.for_module("other", "forecast", schema_version=1)
    unrelated.put("settings", {"keep": True}, expected_revision=None)
    for i in range(129):
        module.put(f"doc_{i}", {"n": i}, expected_revision=None)
    changes = {f"doc_{i}": (1, {"n": i + 1}) for i in range(129)}
    before = deepcopy(changes)
    new = module.migrate(2, changes)
    assert changes == before
    assert new.get("doc_128").data == {"n": 129}
    assert new.get("doc_128").revision == 2
    assert unrelated.get("settings").revision == 1
    assert unrelated.get("settings").data == {"keep": True}


def test_competing_schema_migrations_have_one_winner(tmp_path):
    store, module = setup(tmp_path)
    module.put("active", {"n": 0}, expected_revision=None)
    barrier = Barrier(2)
    def writer(n):
        handle = SQLiteStorage(store.path).for_module("global", "project", schema_version=1)
        barrier.wait(timeout=5)
        try:
            return handle.migrate(2, {"active": (1, {"n": n})}).schema_version
        except StorageSchemaError:
            return "stale"
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(writer, (1, 2)))
    assert outcomes.count(2) == outcomes.count("stale") == 1
    result = store.for_module("global", "project", schema_version=2).get("active")
    assert result.revision == 2 and result.data["n"] in (1, 2)


def test_missing_project_wrong_namespace_and_invalid_v2_source_never_migrate(tmp_path):
    store, module = setup(tmp_path)
    with pytest.raises(ValueError):
        preview_project_v2(module)
    other = store.for_module("other", "project", schema_version=1)
    with pytest.raises(StorageSchemaError):
        preview_project_v2(other)
    original = legacy()
    original["settings"]["too_large"] = 9007199254740992
    module.put("active", original, expected_revision=None)
    with pytest.raises(ValueError, match="Wertebereich"):
        preview_project_v2(module)
    assert module.get("active").data == original
    assert module.get("original_v1") is None


@pytest.mark.parametrize("changes", [
    {"active": (1, {"ok": True}), "bad": (None, {"token": "synthetic"})},
    {"new": (None, {"ok": True})},
    {"active": (2, {"ok": True})},
])
def test_invalid_or_incomplete_replacements_never_change_schema(tmp_path, changes):
    _, module = setup(tmp_path)
    module.put("active", {"original": True}, expected_revision=None)
    with pytest.raises(ValueError):
        module.migrate(2, changes)
    assert module.get("active").data == {"original": True}
    assert module.get("active").revision == 1
    assert module.get("new") is None


def test_wrong_preview_digest_cannot_approve_current_project(tmp_path):
    _, module = setup(tmp_path)
    module.put("active", legacy(), expected_revision=None)
    with pytest.raises(StorageConflict):
        commit_project_v2(module, expected_revision=1, expected_sha256="wrong")
    assert module.get("active").revision == 1
    assert module.get("original_v1") is None


def test_compatible_open_uses_existing_version_and_default_for_new_namespace(tmp_path):
    store, source = setup(tmp_path)
    source.put("active", {"data": "v1"}, expected_revision=None)
    source.migrate(2, {"active": (1, {"data": "v2"})})
    before = store.path.read_bytes()
    opened = store.for_module("global", "project", schema_version=1, compatible_versions=(2,))
    assert opened.schema_version == 2 and opened.get("active").data == {"data": "v2"}
    assert store.path.read_bytes() == before
    with pytest.raises(StorageSchemaError):
        store.for_module("global", "project", schema_version=1, compatible_versions=(3,))
    fresh = store.for_module("other", "project", schema_version=1, compatible_versions=(2,))
    assert fresh.schema_version == 1
