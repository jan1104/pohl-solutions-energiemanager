"""Offline project CLI: validate INPUT; roundtrip INPUT --output OUTPUT.

Outputs only a summary on validation; roundtrip validates before atomic export.
No device access, no secrets, no Home Assistant runtime.
"""

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "pohl_solutions_energiemanager"))

from core.project import MAX_BYTES, export_project_json, load_project_json, project_summary  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Pohl Energiemanager · Projekt offline prüfen")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "roundtrip"):
        command = commands.add_parser(name)
        command.add_argument("input", type=Path)
        if name == "roundtrip":
            command.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    temporary = None
    try:
        with args.input.open("rb") as stream:
            payload = stream.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise ValueError("Datei überschreitet 2 MiB")
        project = load_project_json(payload.decode("utf-8"))
        if args.command == "roundtrip":
            text = export_project_json(project)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                             dir=args.output.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, args.output)
            temporary = None
        print(json.dumps(project_summary(project), ensure_ascii=False, indent=2))
    except (OSError, UnicodeError, ValueError) as err:
        parser.exit(2, f"Projekt nicht übernommen: {err}\n")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
