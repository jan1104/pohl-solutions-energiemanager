"""Temporary local SQLite only: isolation, durable writes and stale editors."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import sqlite3
from threading import Barrier

import pytest

from core.storage import SQLiteStorage, StorageConflict, StorageSchemaError


def repository(tmp_path, **kwargs):
    result = SQLiteStorage(tmp_path / "energy.sqlite", **kwargs)
    result.initialize()
    return result


def test_constructor_and_premature_read_never_create_file(tmp_path):
    path = tmp_path / "not-created.sqlite"
    store = SQLiteStorage(path)
    assert not path.exists()
    with pytest.raises(sqlite3.OperationalError):
        store.for_module("project", "forecast", schema_version=1)
    assert not path.exists()


def test_module_data_survives_reopen_and_initialization_is_idempotent(tmp_path):
    store = repository(tmp_path)
    module = store.for_module("project", "forecast", schema_version=1)
    assert module.get("settings") is None
    first = module.put("settings", {"provider": "manual", "enabled": False}, expected_revision=None)
    assert first.revision == 1
    store.initialize()
    other = SQLiteStorage(store.path).for_module("project", "forecast", schema_version=1)
    assert other.get("settings") == first
    next_value = other.put("settings", {"provider": "manual", "enabled": True}, expected_revision=1)
    assert module.get("settings") == next_value and next_value.revision == 2


def test_projects_and_modules_share_one_database_without_sharing_documents(tmp_path):
    store = repository(tmp_path)
    for project, name in (("a", "forecast"), ("b", "forecast"), ("a", "metering")):
        handle = store.for_module(project, name, schema_version=1)
        handle.put("settings", {"label": project + name}, expected_revision=None)
    assert store.for_module("a", "forecast", schema_version=1).get("settings").data == {"label": "aforecast"}
    assert store.for_module("b", "forecast", schema_version=1).get("settings").data == {"label": "bforecast"}
    assert store.for_module("a", "metering", schema_version=1).get("settings").data == {"label": "ametering"}
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM module_namespaces").fetchone()[0] == 3


def test_atomic_batch_rolls_back_earlier_write_when_later_document_conflicts(tmp_path):
    module = repository(tmp_path).for_module("a", "forecast", schema_version=1)
    module.put("existing", {"value": 1}, expected_revision=None)
    with pytest.raises(StorageConflict):
        module.put_many({"new": (None, {"created": True}), "existing": (None, {"value": 2})})
    assert module.get("new") is None
    assert module.get("existing").data == {"value": 1}
    assert module.get("existing").revision == 1


def test_competing_repository_instances_cannot_overwrite_same_revision(tmp_path):
    store = repository(tmp_path)
    store.for_module("a", "forecast", schema_version=1).put("settings", {"n": 0}, expected_revision=None)
    barrier = Barrier(2)
    def writer(value):
        handle = SQLiteStorage(store.path).for_module("a", "forecast", schema_version=1)
        barrier.wait(timeout=5)
        try:
            return handle.put("settings", {"n": value}, expected_revision=1).data["n"]
        except StorageConflict:
            return "conflict"
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(writer, (1, 2)))
    assert results.count("conflict") == 1
    final = store.for_module("a", "forecast", schema_version=1).get("settings")
    assert final.revision == 2 and final.data["n"] in (1, 2)


@pytest.mark.parametrize("data", [[], {"n": float("nan")}, {"n": float("inf")},
                                  {"password": "synthetic"}, {"nested": {"token": "synthetic"}},
                                  {"text": "x" * (2 * 1024 * 1024)}])
def test_invalid_or_secret_documents_preserve_existing_data(tmp_path, data):
    module = repository(tmp_path).for_module("a", "forecast", schema_version=1)
    module.put("settings", {"n": 1}, expected_revision=None)
    with pytest.raises(ValueError):
        module.put("settings", data, expected_revision=1)
    assert module.get("settings").data == {"n": 1}
    assert module.get("settings").revision == 1


def test_newer_or_older_module_schema_never_relabels_existing_data(tmp_path):
    store = repository(tmp_path)
    module = store.for_module("a", "forecast", schema_version=2)
    module.put("settings", {"v": 2}, expected_revision=None)
    for version in (1, 3):
        with pytest.raises(StorageSchemaError):
            store.for_module("a", "forecast", schema_version=version)
    assert module.get("settings").data == {"v": 2}
    # An unrelated module can still be registered.
    assert store.for_module("a", "metering", schema_version=1).get("settings") is None


def test_database_version_and_unrelated_database_are_not_modified(tmp_path):
    store = repository(tmp_path)
    with sqlite3.connect(store.path) as connection:
        connection.execute("PRAGMA user_version=99")
    with pytest.raises(StorageSchemaError):
        store.initialize()
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 99
    other = SQLiteStorage(tmp_path / "unrelated.sqlite")
    with sqlite3.connect(other.path) as connection:
        connection.execute("CREATE TABLE existing (value TEXT)")
        connection.execute("INSERT INTO existing VALUES ('keep')")
    with pytest.raises(StorageSchemaError):
        other.initialize()
    with sqlite3.connect(other.path) as connection:
        assert connection.execute("SELECT value FROM existing").fetchone()[0] == "keep"


def test_foreign_view_only_database_is_not_claimed_as_empty(tmp_path):
    store = SQLiteStorage(tmp_path / "foreign.sqlite")
    with sqlite3.connect(store.path) as connection:
        connection.execute("CREATE VIEW existing_view AS SELECT 42 AS answer")
    with pytest.raises(StorageSchemaError):
        store.initialize()
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT answer FROM existing_view").fetchone()[0] == 42
        assert connection.execute("PRAGMA application_id").fetchone()[0] == 0
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []


def test_database_path_with_unicode_and_uri_characters_roundtrips(tmp_path):
    store = SQLiteStorage(tmp_path / "Konfiguration #1 ü.sqlite")
    store.initialize()
    module = store.for_module("a", "forecast", schema_version=1)
    module.put("settings", {"value": 1}, expected_revision=None)
    assert module.get("settings").data == {"value": 1}


def test_inputs_and_outputs_are_detached_and_only_bound_parameters_reach_sql(tmp_path):
    module = repository(tmp_path).for_module("a", "forecast", schema_version=1)
    value = {"nested": {"text": "'); DROP TABLE module_documents; --"}}
    before = deepcopy(value)
    saved = module.put("settings", value, expected_revision=None)
    saved.data["nested"]["text"] = "changed"
    assert value == before and module.get("settings").data == before
    with pytest.raises(ValueError):
        module.put("bad';DROP", {}, expected_revision=None)


def test_lock_contention_fails_without_partial_changes(tmp_path):
    store = repository(tmp_path, timeout=.01)
    module = store.for_module("a", "forecast", schema_version=1)
    with sqlite3.connect(store.path, isolation_level=None) as lock:
        lock.execute("BEGIN IMMEDIATE")
        try:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                module.put("new", {"v": 1}, expected_revision=None)
        finally:
            lock.rollback()
    assert module.get("new") is None


@pytest.mark.parametrize("revision", [0, -1, True, "1"])
def test_invalid_expected_revision_is_rejected(tmp_path, revision):
    module = repository(tmp_path).for_module("a", "forecast", schema_version=1)
    with pytest.raises(ValueError):
        module.put("settings", {}, expected_revision=revision)
