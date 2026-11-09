"""Explicit project persistence transition with source preservation.

Call only from an explicit migration workflow with a format-2-capable UI.
No storage is created by import, and preview performs reads only.
"""

from dataclasses import dataclass
from hashlib import sha256
import json

from .project import validate_project
from .project_v2 import configuration_issues_v2, migrate_project_v1_to_v2
from .storage import StorageConflict, StorageSchemaError


def _content_sha(project):
    return sha256(json.dumps(project, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ProjectMigrationPreview:
    source_revision: int
    source_sha256: str
    project: dict
    issues: list


def preview_project_v2(namespace):
    if (namespace.project_id, namespace.module_id) != ("global", "project"):
        raise StorageSchemaError("Project migration requires the active-project namespace")
    if namespace.schema_version != 1:
        raise StorageSchemaError("Project migration requires source schema 1")
    current = namespace.get("active")
    if current is None:
        raise ValueError("Create a project before requesting migration")
    original = validate_project(current.data)
    candidate = migrate_project_v1_to_v2(original)
    return ProjectMigrationPreview(current.revision, _content_sha(original), candidate,
                                   configuration_issues_v2(candidate))


def commit_project_v2(namespace, *, expected_revision, expected_sha256):
    """Recompute from persisted source; never trust a modified preview object.

    Preserve original data and legacy-migration metadata in the same transaction.
    Callers must support reopening the resulting schema.
    """
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValueError("A positive source revision is required")
    preview = preview_project_v2(namespace)
    if preview.source_revision != expected_revision or preview.source_sha256 != expected_sha256:
        raise StorageConflict("Project changed after migration preview")
    current = namespace.get("active")
    if current is None or current.revision != expected_revision:
        raise StorageConflict("Project changed after migration preview")
    original = validate_project(current.data)
    if _content_sha(original) != expected_sha256:
        raise StorageConflict("Project content changed after migration preview")
    changes = {
        "active": (expected_revision, preview.project),
        "original_v1": (None, original),
        "project_format_migration": (None, {"source_schema": 1, "target_schema": 2,
                                            "source_revision": expected_revision,
                                            "source_sha256": expected_sha256}),
    }
    metadata = namespace.get("migration")
    if metadata is not None:
        changes["migration"] = (metadata.revision, metadata.data)
    return namespace.migrate(2, changes)
