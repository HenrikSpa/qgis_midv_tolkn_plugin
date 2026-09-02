#!/usr/bin/env python3
"""Regenerate resources.py from resources.qrc, then re-patch its import line.

pyrcc5 always emits ``from PyQt5 import QtCore`` at the top of the generated
file. Midvatten plugins need the Qt-binding-agnostic ``from qgis.PyQt import
QtCore`` instead (see the Qt5+Qt6 migration notes), so this script runs
pyrcc5 and then rewrites that one line.

There is no pyrcc6 equivalent yet in general use; pyrcc5's output is binary
data plus a plain import line, so running it and patching the import keeps
the generated module working under both PyQt5 and PyQt6 (via qgis.PyQt).

Usage:
    python3 scripts/compile_resources.py
"""
import re
import subprocess
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent
QRC_FILE = PLUGIN_DIR / "resources.qrc"
RESOURCES_PY = PLUGIN_DIR / "resources.py"

OLD_IMPORT = "from PyQt5 import QtCore"
NEW_IMPORT = "from qgis.PyQt import QtCore"


def compile_resources() -> None:
    subprocess.run(
        ["pyrcc5", "-o", str(RESOURCES_PY), str(QRC_FILE)],
        check=True,
    )

    text = RESOURCES_PY.read_text(encoding="utf-8")
    patched, count = re.subn(
        rf"^{re.escape(OLD_IMPORT)}$",
        NEW_IMPORT,
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count == 0:
        print(
            f"warning: expected line {OLD_IMPORT!r} not found in "
            f"{RESOURCES_PY}; import left unpatched",
            file=sys.stderr,
        )
        return
    RESOURCES_PY.write_text(patched, encoding="utf-8")


if __name__ == "__main__":
    compile_resources()
