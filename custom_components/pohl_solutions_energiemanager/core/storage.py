"""Central SQLite configuration storage, isolated by project and module.

Synchronous I/O: callers must use an executor outside HA's event loop. No file
or connection is opened on construction. This does not replace HA ProjectStore.
"""

from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3

from .project import MAX_BYTES, _json_tree

APPLICATION_ID = 0x5053454D
DATABASE_VERSION = 1


class StorageConflict(ValueError):
    """Expected document revision is obsolete; no writes were committed."""


class StorageSchemaError(ValueError):
    """Unsupported database or module schema; migration must be explicit."""


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,128}", value):
        raise ValueError("Use a nonempty bounded stable storage identifier")


def _encode(data):
    if not isinstance(data, dict):
        raise ValueError("Configuration document must be an object")
    _json_tree(data)
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(encoded.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Configuration document exceeds 2 MiB")
    return encoded


def _prepare_changes(changes, *, max_documents=128):
    if (not isinstance(changes, dict) or not changes
            or (max_documents is not None and len(changes) > max_documents)):
        raise ValueError("Provide a nonempty document batch within the supported limit")
    prepared = {}
    for key, (expected, data) in changes.items():
        _identifier(key)
        if expected is not None and (type(expected) is not int or expected < 1):
            raise ValueError("Expected revision must be positive or None for create-only")
        prepared[key] = (expected, _encode(data))
    return prepared


@dataclass(frozen=True, slots=True)
class StoredDocument:
    revision: int
    data: dict


class SQLiteStorage:
    """One file, shared schema, independent module namespaces and revisions."""

    def __init__(self, path, *, timeout=3.0):
        if type(timeout) not in (int, float) or not 0 < timeout <= 30:
            raise ValueError("Storage timeout must be greater than 0 and at most 30 seconds")
        self.path = Path(path).absolute()
        self.timeout = float(timeout)

    @contextmanager
    def _connection(self, *, create=False):
        if create:
            connection = sqlite3.connect(self.path, timeout=self.timeout, isolation_level=None)
        else:
            connection = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True,
                                         timeout=self.timeout, isolation_level=None)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA synchronous=FULL")
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _check_database(connection):
        app = connection.execute("PRAGMA application_id").fetchone()[0]
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if app != APPLICATION_ID or version != DATABASE_VERSION:
            raise StorageSchemaError("Unsupported energy-manager database")

    def initialize(self):
        """Explicitly create schema, never modify an unrelated/newer database."""
        with self._connection(create=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                app = connection.execute("PRAGMA application_id").fetchone()[0]
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                objects = connection.execute("SELECT name FROM sqlite_master").fetchall()
                if app == 0 and version == 0 and not objects:
                    connection.execute("CREATE TABLE module_namespaces (project_id TEXT NOT NULL, module_id TEXT NOT NULL, schema_version INTEGER NOT NULL CHECK(schema_version>0), PRIMARY KEY(project_id,module_id))")
                    connection.execute("CREATE TABLE module_documents (project_id TEXT NOT NULL, module_id TEXT NOT NULL, document_key TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0), body TEXT NOT NULL, PRIMARY KEY(project_id,module_id,document_key), FOREIGN KEY(project_id,module_id) REFERENCES module_namespaces(project_id,module_id))")
                    connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
                    connection.execute(f"PRAGMA user_version={DATABASE_VERSION}")
                else:
                    self._check_database(connection)
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    @contextmanager
    def _transaction(self):
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                self._check_database(connection)
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def for_module(self, project_id, module_id, *, schema_version):
        """Explicitly register a namespace; no arbitrary module SQL or code runs."""
        _identifier(project_id)
        _identifier(module_id)
        if type(schema_version) is not int or not 1 <= schema_version <= 999999:
            raise ValueError("Module configuration schema version is required")
        with self._transaction() as connection:
            row = connection.execute("SELECT schema_version FROM module_namespaces WHERE project_id=? AND module_id=?", (project_id, module_id)).fetchone()
            if row is None:
                connection.execute("INSERT INTO module_namespaces VALUES (?,?,?)", (project_id, module_id, schema_version))
            elif row[0] != schema_version:
                raise StorageSchemaError("Module configuration requires an explicit migration")
        return ModuleStorage(self, project_id, module_id, schema_version)


@dataclass(frozen=True, slots=True)
class ModuleStorage:
    """Scoped repository handle; ordinary modules never receive raw SQL access."""

    _repository: SQLiteStorage
    project_id: str
    module_id: str
    schema_version: int

    def _check_schema(self, connection):
        row = connection.execute("SELECT schema_version FROM module_namespaces WHERE project_id=? AND module_id=?", (self.project_id, self.module_id)).fetchone()
        if row is None or row[0] != self.schema_version:
            raise StorageSchemaError("Module configuration schema changed")

    def get(self, key):
        _identifier(key)
        with self._repository._connection() as connection:
            connection.execute("BEGIN")
            self._repository._check_database(connection)
            self._check_schema(connection)
            row = connection.execute("SELECT revision,body FROM module_documents WHERE project_id=? AND module_id=? AND document_key=?", (self.project_id, self.module_id, key)).fetchone()
        if row is None:
            return None
        data = json.loads(row[1])
        _encode(data)  # Check stored data as strictly as new writes.
        return StoredDocument(row[0], data)

    def put(self, key, data, *, expected_revision):
        return self.put_many({key: (expected_revision, data)})[key]

    def put_many(self, changes):
        """Commit all documents or none. None revision means create-only."""
        prepared = _prepare_changes(changes)
        revisions = {}
        with self._repository._transaction() as connection:
            self._check_schema(connection)
            for key, (expected, encoded) in prepared.items():
                row = connection.execute("SELECT revision FROM module_documents WHERE project_id=? AND module_id=? AND document_key=?", (self.project_id, self.module_id, key)).fetchone()
                actual = row[0] if row else None
                if actual != expected:
                    raise StorageConflict(f"Document changed: {key}")
                revision = 1 if actual is None else actual + 1
                connection.execute("INSERT INTO module_documents VALUES (?,?,?,?,?) ON CONFLICT(project_id,module_id,document_key) DO UPDATE SET revision=excluded.revision,body=excluded.body", (self.project_id, self.module_id, key, revision, encoded))
                revisions[key] = StoredDocument(revision, json.loads(encoded))
        return revisions

    def migrate(self, target_schema_version, changes):
        """Explicit atomic schema replacement, preserving every document key.

        Supply a revision-checked replacement for every current document and
        optionally create new ones. No callbacks or implicit transforms execute.
        Old handles become unusable after commit. No automatic downgrade.
        """
        if (type(target_schema_version) is not int
                or not self.schema_version < target_schema_version <= 999999):
            raise ValueError("Migration target must be a newer supported schema")
        prepared = _prepare_changes(changes, max_documents=None)
        with self._repository._transaction() as connection:
            self._check_schema(connection)
            rows = dict(connection.execute(
                "SELECT document_key,revision FROM module_documents WHERE project_id=? AND module_id=?",
                (self.project_id, self.module_id)).fetchall())
            if not rows.keys() <= prepared.keys():
                raise StorageConflict("Migration must preserve every existing document")
            for key, (expected, _) in prepared.items():
                if rows.get(key) != expected:
                    raise StorageConflict(f"Document changed: {key}")
            for key, (expected, encoded) in prepared.items():
                revision = 1 if expected is None else expected + 1
                connection.execute(
                    "INSERT INTO module_documents VALUES (?,?,?,?,?) ON CONFLICT(project_id,module_id,document_key) DO UPDATE SET revision=excluded.revision,body=excluded.body",
                    (self.project_id, self.module_id, key, revision, encoded))
            connection.execute(
                "UPDATE module_namespaces SET schema_version=? WHERE project_id=? AND module_id=?",
                (target_schema_version, self.project_id, self.module_id))
        return ModuleStorage(self._repository, self.project_id, self.module_id, target_schema_version)
