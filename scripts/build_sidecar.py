from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
BINARIES = ROOT / "frontend" / "src-tauri" / "binaries"


def default_target_triple() -> str:
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Windows":
        return "x86_64-pc-windows-msvc" if "64" in machine or machine in {"amd64", "x86_64"} else "i686-pc-windows-msvc"
    if system == "Darwin":
        return "aarch64-apple-darwin" if machine in {"arm64", "aarch64"} else "x86_64-apple-darwin"
    if system == "Linux":
        return "aarch64-unknown-linux-gnu" if machine in {"aarch64", "arm64"} else "x86_64-unknown-linux-gnu"
    raise SystemExit(f"Unsupported platform: {system} {machine}")


def executable_name(base: str) -> str:
    return f"{base}.exe" if platform.system() == "Windows" else base


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Python API sidecar for Tauri.")
    parser.add_argument("--target-triple", default=default_target_triple())
    args = parser.parse_args()

    BINARIES.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            "--onefile",
            "--name",
            "word-batch-sidecar",
            "--collect-submodules",
            "app",
            "--hidden-import",
            "multipart",
            "--hidden-import",
            "python_multipart",
            "--hidden-import",
            "pythoncom",
            "--hidden-import",
            "pywintypes",
            "--hidden-import",
            "win32com",
            "--hidden-import",
            "win32com.client",
            "sidecar.py",
        ],
        cwd=BACKEND,
        check=True,
    )

    built = BACKEND / "dist" / executable_name("word-batch-sidecar")
    target = BINARIES / executable_name(f"word-batch-sidecar-{args.target_triple}")
    shutil.copy2(built, target)
    print(f"Sidecar copied to {target}")


if __name__ == "__main__":
    main()
