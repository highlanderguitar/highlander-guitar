from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TUXGUITAR = (
    Path.home()
    / "Downloads"
    / "tuxguitar-2.0.1-windows-swt-x86_64"
    / "tuxguitar-2.0.1-windows-swt-x86_64"
)


def _installation() -> Path:
    return Path(os.environ.get("TUXGUITAR_HOME", DEFAULT_TUXGUITAR))


def test_every_generated_tg_passes_native_parser_save_and_reopen(tmp_path):
    installation = _installation()
    java = installation / "jre" / "bin" / "java.exe"
    ecj = Path(os.environ.get("TUXGUITAR_ECJ_JAR", ROOT / "tmp" / "ecj-3.39.0.jar"))
    if not java.exists() or not ecj.exists():
        pytest.skip("TuxGuitar 2.0.1 and Eclipse compiler are required")

    jars = sorted((installation / "lib").glob("*.jar"))
    classpath = os.pathsep.join(str(path) for path in jars)
    classes = tmp_path / "classes"
    classes.mkdir()
    subprocess.run(
        [
            str(java), "-jar", str(ecj), "-21", "-cp", classpath,
            "-d", str(classes), str(ROOT / "scripts" / "TuxGuitarNativeProbe.java"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    generated = sorted(
        path
        for path in (ROOT / "reviews" / "bh_5432").rglob("*.tg")
        if "_invalid_generated_tg" not in path.parts
    )
    assert len(generated) == 11
    for index, source in enumerate(generated):
        saved = tmp_path / f"{index:02d}-{source.name}"
        completed = subprocess.run(
            [
                str(java), "-cp", os.pathsep.join((str(classes), classpath)),
                "TuxGuitarNativeProbe", str(source), str(saved),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        assert "native_parser_accepted=true" in completed.stdout
        assert "native_save=true reopen_verified=true" in completed.stdout
