"""Build-Treiber: PyInstaller (--onedir) und/oder Nuitka (--standalone), danach Selftest der exe.

Aufruf: .venv\\Scripts\\python build.py pyinstaller | nuitka | all [--version X.Y.Z] [--tool-arg=FLAG ...]
        (Linux: .venv/bin/python). Paket-/Daten-Flags setzen 013_build_pyinstaller.sh / 014_build_nuitka.sh.
Ausgabe: dist\\pyinstaller\\PromptEnginEEr\\ und dist\\nuitka\\PromptEnginEEr\\, Logs in build\\.
Windows: PromptEnginEEr.exe, Nuitka mit MSVC, --version setzt die Versionsressource der exe.
Linux: PromptEnginEEr (GTK/WebKit2), Nuitka mit gcc + patchelf.
Exit 0 nur wenn alle angeforderten Builds und Selftests gruen sind.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "main.py"
STATIC = ROOT / "static"
BUILD = ROOT / "build"
DIST = ROOT / "dist"
NAME = "PromptEnginEEr"
RUNTIME_FILES = (".env", "history.db", "app.log")
WINDOWS = sys.platform == "win32"
EXE = f"{NAME}.exe" if WINDOWS else NAME
PYINSTALLER_FLAGS = [
    "--onedir", "--windowed", "--noconfirm", "--clean", "--name", NAME,
    "--add-data", f"{STATIC}{os.pathsep}static",
    "--paths", str(ROOT),
    "--distpath", str(DIST / "pyinstaller"),
    "--workpath", str(BUILD / "pyinstaller"),
    "--specpath", str(BUILD / "pyinstaller"),
]

NUITKA_FLAGS = [
    "--standalone",
    f"--include-data-dir={STATIC}=static",
    "--include-package-data=webview",
    f"--output-dir={DIST / 'nuitka'}",
    f"--output-filename={EXE}",
    "--remove-output",
]
if WINDOWS:
    NUITKA_FLAGS += [
        "--windows-console-mode=disable", "--msvc=latest",
        "--include-package-data=pythonnet",
        "--include-package-data=clr_loader",
    ]

DOWNLOAD_HINTS = ("download", "Is it OK to")


def run(cmd: list, log: Path) -> int:
    print(">", " ".join(map(str, cmd)), flush=True)
    with open(log, "w", encoding="utf-8", errors="replace") as fh:
        return subprocess.run(cmd, cwd=ROOT, stdin=subprocess.DEVNULL,
                              stdout=fh, stderr=subprocess.STDOUT).returncode


def win_version(version: str) -> str:
    """X.Y.Z -> X.Y.Z.0 (Windows-Versionsressource)."""
    return f"{version}.0"


def pyinstaller_version_flags(version: str | None) -> list:
    """Windows: Versionsressource der exe; Linux ignoriert sie, daher keine Flags."""
    if not (WINDOWS and version):
        return []
    v = win_version(version)
    t = ", ".join(v.split("."))
    ver_file = BUILD / "version_info.txt"
    ver_file.write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({t}), prodvers=({t}), mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('ProductName', '{NAME}'),
      StringStruct('FileVersion', '{v}'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""", encoding="utf-8")
    return ["--version-file", str(ver_file)]


def nuitka_version_flags(version: str | None) -> list:
    if not (WINDOWS and version):
        return []
    v = win_version(version)
    return [f"--product-name={NAME}", f"--product-version={v}", f"--file-version={v}"]


def build_pyinstaller(version: str | None = None, extra: list = ()) -> tuple[int, Path | None]:
    shutil.rmtree(DIST / "pyinstaller", ignore_errors=True)
    flags = [*PYINSTALLER_FLAGS, *pyinstaller_version_flags(version), *extra]
    code = run([sys.executable, "-m", "PyInstaller", *flags, str(MAIN)],
               BUILD / "pyinstaller.log")
    return code, DIST / "pyinstaller" / NAME / EXE


def build_nuitka(version: str | None = None, extra: list = ()) -> tuple[int, Path | None]:
    shutil.rmtree(DIST / "nuitka", ignore_errors=True)
    log = BUILD / "nuitka.log"
    flags = [*NUITKA_FLAGS, *nuitka_version_flags(version), *extra]
    code = run([sys.executable, "-m", "nuitka", *flags, str(MAIN)], log)
    if code != 0 and any(h in log.read_text(encoding="utf-8", errors="replace")
                         for h in DOWNLOAD_HINTS):
        print("BLOCKED: Nuitka verlangt Download (Nutzerfreigabe noetig), siehe", log)
        return code, None
    src = DIST / "nuitka" / f"{MAIN.stem}.dist"
    dst = DIST / "nuitka" / NAME
    if code == 0 and src.is_dir():
        src.rename(dst)
    return code, dst / EXE


def selftest(label: str, exe: Path) -> bool:
    try:
        code = subprocess.run([str(exe), "--selftest"], cwd=exe.parent, timeout=150).returncode
    except subprocess.TimeoutExpired:
        code = "timeout"
    leaked = [n for n in RUNTIME_FILES if (exe.parent / n).exists()]
    print(f"[{label}] selftest exit={code} leaked={leaked}", flush=True)
    return code == 0 and not leaked


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=("pyinstaller", "nuitka", "all"))
    parser.add_argument("--version", help="X.Y.Z, Versionsressource der exe (nur Windows)")
    parser.add_argument("--tool-arg", action="append", default=[], metavar="FLAG",
                        help="zusaetzliches Flag fuer PyInstaller/Nuitka, mehrfach (Form --tool-arg=--x=y)")
    args = parser.parse_args()
    if args.version and not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        parser.error("--version erwartet X.Y.Z")
    BUILD.mkdir(parents=True, exist_ok=True)

    targets = {"pyinstaller": build_pyinstaller, "nuitka": build_nuitka}
    labels = list(targets) if args.target == "all" else [args.target]
    ok = True
    for label in labels:
        start = time.monotonic()
        code, exe = targets[label](args.version, args.tool_arg)
        duration = time.monotonic() - start
        if code != 0 or exe is None or not exe.exists():
            print(f"[{label}] build FAILED exit={code} ({duration:.0f} s), log: {BUILD / (label + '.log')}")
            ok = False
            continue
        size_mb = exe.stat().st_size / 1_000_000
        print(f"[{label}] build ok ({duration:.0f} s, exe {size_mb:.1f} MB): {exe}", flush=True)
        ok = selftest(label, exe) and ok
    print("RESULT:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
