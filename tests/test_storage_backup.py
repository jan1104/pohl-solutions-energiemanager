"""Explicit create-only SQLite backups, using synthetic local documents."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
from threading import Event

import pytest

from core import storage
from core.storage import SQLiteStorage, StorageSchemaError


def populated(tmp_path):
    repository = SQLiteStorage(tmp_path / 'shared.sqlite')
    repository.initialize()
    for project, module in [('a', 'project'), ('a', 'forecast'), ('b', 'metering')]:
        handle = repository.for_module(project, module, schema_version=1)
        handle.put_many({'first': (None, {'value': 1}), 'second': (None, {'value': 1})})
        handle.put('first', {'value': 2}, expected_revision=1)
    return repository


def assert_no_temporary(tmp_path):
    assert not list(tmp_path.glob('.pohl-backup-*'))


def test_backup_retains_all_scopes_revisions_and_is_independent(tmp_path):
    source = populated(tmp_path)
    destination = tmp_path / 'Sicherung #1 ü.sqlite'
    assert source.backup(destination) == destination
    backup = SQLiteStorage(destination)
    for project, module in [('a', 'project'), ('a', 'forecast'), ('b', 'metering')]:
        handle = backup.for_module(project, module, schema_version=1)
        assert handle.get('first').revision == 2
        assert handle.get('first').data == {'value': 2}
        assert handle.get('second').data == {'value': 1}
    source.for_module('a', 'forecast', schema_version=1).put('first', {'value': 3}, expected_revision=2)
    assert backup.for_module('a', 'forecast', schema_version=1).get('first').data == {'value': 2}
    assert_no_temporary(tmp_path)


@pytest.mark.parametrize('destination_kind', ['file', 'directory', 'source', 'dangling_symlink'])
def test_backup_never_overwrites_existing_destination(tmp_path, destination_kind):
    source = populated(tmp_path)
    destination = tmp_path / 'backup.sqlite'
    if destination_kind == 'file':
        destination.write_bytes(b'existing unrelated data')
    elif destination_kind == 'directory':
        destination.mkdir()
    elif destination_kind == 'source':
        destination = source.path
    else:
        try:
            destination.symlink_to(tmp_path / 'absent')
        except OSError:
            pytest.skip('Creating symlinks is unavailable on this system')
    before = destination.read_bytes() if destination.is_file() else None
    with pytest.raises(FileExistsError):
        source.backup(destination)
    if before is not None:
        assert destination.read_bytes() == before
    elif destination_kind == 'directory':
        assert destination.is_dir()
    else:
        assert destination.is_symlink()
    assert_no_temporary(tmp_path)


@pytest.mark.parametrize('kind', ['missing', 'foreign', 'future'])
def test_invalid_source_never_publishes_backup(tmp_path, kind):
    path = tmp_path / 'source.sqlite'
    if kind == 'foreign':
        with sqlite3.connect(path) as connection:
            connection.execute('CREATE TABLE unrelated (value TEXT)')
    elif kind == 'future':
        SQLiteStorage(path).initialize()
        with sqlite3.connect(path) as connection:
            connection.execute('PRAGMA user_version=999')
    before = path.read_bytes() if path.exists() else None
    with pytest.raises((sqlite3.OperationalError, StorageSchemaError)):
        SQLiteStorage(path).backup(tmp_path / 'backup.sqlite')
    assert not (tmp_path / 'backup.sqlite').exists()
    assert (path.read_bytes() if path.exists() else None) == before
    assert_no_temporary(tmp_path)


def test_timeout_and_publication_failure_clean_only_owned_temporary(tmp_path, monkeypatch):
    source = populated(tmp_path)
    destination = tmp_path / 'backup.sqlite'
    # Force the progress callback over budget without waiting for wall time.
    times = iter([0.0, 100.0])
    with monkeypatch.context() as patch:
        patch.setattr(storage, 'monotonic', lambda: next(times, 100.0))
        with pytest.raises(TimeoutError):
            source.backup(destination)
    assert not destination.exists()
    assert_no_temporary(tmp_path)

    def failed_publication(*args):
        raise OSError('synthetic unsupported hard links')

    with monkeypatch.context() as patch:
        patch.setattr(storage.os, 'link', failed_publication)
        with pytest.raises(OSError, match='unsupported'):
            source.backup(destination)
    assert not destination.exists()
    assert_no_temporary(tmp_path)
    assert source.for_module('a', 'forecast', schema_version=1).get('first').revision == 2


def test_racing_destination_is_preserved(tmp_path, monkeypatch):
    source = populated(tmp_path)
    destination = tmp_path / 'backup.sqlite'
    original_link = storage.os.link

    def racing_link(src, dst):
        Path(dst).write_bytes(b'concurrent owner')
        return original_link(src, dst)

    monkeypatch.setattr(storage.os, 'link', racing_link)
    with pytest.raises(FileExistsError):
        source.backup(destination)
    assert destination.read_bytes() == b'concurrent owner'
    assert_no_temporary(tmp_path)


def test_backup_reads_committed_wal_snapshot_not_uncommitted_transaction(tmp_path):
    source = populated(tmp_path)
    started, release = Event(), Event()

    def writer():
        with sqlite3.connect(source.path) as connection:
            connection.execute('PRAGMA journal_mode=WAL')
            # These committed changes remain in WAL while this connection stays open.
            connection.execute("UPDATE module_documents SET body=?,revision=3 WHERE project_id='a' AND module_id='forecast'",
                               ('{"value":3}',))
            connection.commit()
            connection.execute("UPDATE module_documents SET body=?,revision=4 WHERE project_id='a' AND module_id='forecast'",
                               ('{"value":4}',))
            started.set()
            assert release.wait(5)
            connection.commit()

    with ThreadPoolExecutor(max_workers=1) as pool:
        task = pool.submit(writer)
        try:
            assert started.wait(5)
            destination = source.backup(tmp_path / 'backup.sqlite')
        finally:
            release.set()
        task.result()
    handle = SQLiteStorage(destination).for_module('a', 'forecast', schema_version=1)
    assert handle.get('first').data == handle.get('second').data == {'value': 3}
    assert handle.get('first').revision == handle.get('second').revision == 3
    assert source.for_module('a', 'forecast', schema_version=1).get('first').data == {'value': 4}
    assert_no_temporary(tmp_path)

@pytest.mark.parametrize('failure', ['copy', 'metadata', 'integrity'])
def test_copy_or_validation_failure_never_publishes(tmp_path, monkeypatch, failure):
    source = populated(tmp_path)
    destination = tmp_path / 'backup.sqlite'
    original_connect = sqlite3.connect

    class FailingConnection(sqlite3.Connection):
        def backup(self, target, **kwargs):
            if failure == 'copy':
                raise sqlite3.DatabaseError('synthetic copy failure')
            return super().backup(target, **kwargs)

        def execute(self, sql, *args):
            if failure == 'integrity' and sql == 'PRAGMA quick_check':
                class Result:
                    def fetchall(self):
                        return [('ok',), ('synthetic additional integrity error',)]
                return Result()
            return super().execute(sql, *args)

    def connect(*args, **kwargs):
        return original_connect(*args, **kwargs, factory=FailingConnection)

    with monkeypatch.context() as patch:
        patch.setattr(storage.sqlite3, 'connect', connect)
        if failure == 'metadata':
            original_check = SQLiteStorage._check_database
            checks = []

            def validate(connection):
                checks.append(connection)
                original_check(connection)
                if len(checks) == 2:
                    raise StorageSchemaError('synthetic copied metadata rejection')

            patch.setattr(SQLiteStorage, '_check_database', staticmethod(validate))
        with pytest.raises((sqlite3.DatabaseError, StorageSchemaError)):
            source.backup(destination)
    assert not destination.exists()
    assert_no_temporary(tmp_path)
    assert source.for_module('a', 'forecast', schema_version=1).get('first').revision == 2
