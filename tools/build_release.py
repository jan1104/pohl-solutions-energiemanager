"""Build the integration-only ZIP consumed by HACS; never package private inputs."""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "pohl_solutions_energiemanager"


def build(output: Path) -> Path:
    """Package files relative to the integration root, as required by HACS."""
    component = ROOT / "custom_components" / DOMAIN
    manifest = json.loads((component / "manifest.json").read_text(encoding="utf-8"))
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    if manifest["domain"] != DOMAIN or not manifest.get("version"):
        raise ValueError("Integration domain/version is invalid")
    if not hacs.get("zip_release") or hacs.get("filename") != output.name:
        raise ValueError("Release filename must match hacs.json")
    files = sorted(p for p in component.rglob("*")
                   if p.is_file() and not p.is_symlink()
                   and "__pycache__" not in p.parts
                   and (p.suffix in {".py", ".json", ".yaml"}
                        or "frontend" in p.relative_to(component).parts
                        and p.suffix in {".js", ".css", ".html"}))
    if not files:
        raise ValueError("Integration source files are missing")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(component).as_posix())
    with ZipFile(output) as archive:
        names = archive.namelist()
        if archive.testzip() is not None or "manifest.json" not in names or "__init__.py" not in names:
            raise ValueError("Release ZIP validation failed")
        if json.loads(archive.read("manifest.json"))["version"] != manifest["version"]:
            raise ValueError("Release ZIP version mismatch")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HACS-Integrationspaket bauen")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / f"{DOMAIN}.zip")
    args = parser.parse_args()
    print(build(args.output))
