"""Copy the shared project UI into the HACS component; never include user data."""

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
ASSETS = (
    "styles.css", "project.css", "project.html", "project-model.js",
    "project-actions.js", "project-ui.js", "project-examples.js",
)


def sync() -> None:
    destination = ROOT / "custom_components/pohl_solutions_energiemanager/frontend"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ASSETS:
        shutil.copyfile(ROOT / "preview" / name, destination / name)


if __name__ == "__main__":
    sync()
