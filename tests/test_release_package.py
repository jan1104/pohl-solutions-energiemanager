"""Check the exact archive HACS will install, including version consistency."""

import json
from pathlib import Path
import subprocess
import sys
import tomllib
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def test_hacs_release_layout_and_versions(tmp_path):
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    manifest_path = ROOT / "custom_components/pohl_solutions_energiemanager/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    package = tmp_path / hacs["filename"]
    result = subprocess.run([sys.executable, str(ROOT / "tools/build_release.py"),
                             "--output", str(package)], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    with ZipFile(package) as archive:
        names = archive.namelist()
        assert archive.testzip() is None
        assert {"manifest.json", "__init__.py", "core/project.py", "translations/de.json"} <= set(names)
        assert all(not n.startswith(("custom_components/", "private/", "preview/")) for n in names)
        assert all("__pycache__" not in n and ".." not in Path(n).parts for n in names)
        assert archive.read("manifest.json") == manifest_path.read_bytes()
        assert len(names) == len(set(names))
    with (ROOT / "pyproject.toml").open("rb") as stream:
        assert tomllib.load(stream)["project"]["version"] == manifest["version"]
    assert hacs["zip_release"] is True
