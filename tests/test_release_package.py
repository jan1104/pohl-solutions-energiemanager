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


def test_hacs_installs_the_real_panel_and_shared_ui(tmp_path):
    component = ROOT / "custom_components/pohl_solutions_energiemanager"
    asset_names = ("styles.css", "project.css", "project.html", "project-model.js",
                   "project-actions.js", "project-ui.js", "project-examples.js")
    for name in asset_names:
        assert (component / "frontend" / name).read_bytes() == (ROOT / "preview" / name).read_bytes(), name
    package = tmp_path / "pohl_solutions_energiemanager.zip"
    subprocess.run([sys.executable, str(ROOT / "tools/build_release.py"), "--output", str(package)],
                   capture_output=True, check=True, timeout=15)
    with ZipFile(package) as archive:
        assert "frontend/pohl-panel.js" in archive.namelist()
        for name in asset_names:
            assert archive.read("frontend/" + name) == (ROOT / "preview" / name).read_bytes()
    manifest = json.loads((component / "manifest.json").read_text(encoding="utf-8"))
    assert {"frontend", "http", "websocket_api", "panel_custom"} <= set(manifest["dependencies"])
