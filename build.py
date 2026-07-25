from datetime import datetime
import os
import shutil
import subprocess
import sys

from config import APP_NAME, APP_VERSION


def parse_version_tuple(version_str: str) -> tuple[int, int, int, int]:
    """Parses a version string like '1.1.0' into a 4-element integer tuple (1, 1, 0, 0)."""
    parts = [int(p) for p in version_str.split(".") if p.isdigit()]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


def generate_version_info_file():
    """Dynamically generates file_version_info.txt using config settings and current year."""
    print("Generating file_version_info.txt...")

    current_year = datetime.now().year
    version_tuple = parse_version_tuple(APP_VERSION)
    exe_name = f"{APP_NAME}.exe"

    copyright_str = (
        f"Copyright (c) 2026–{current_year}"
        if current_year > 2026
        else "Copyright (c) 2026"
    )
    content = f"""# Automatically generated version file by build script
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', '{APP_NAME}'),
            StringStruct('FileDescription', '{APP_NAME}'),
            StringStruct('FileVersion', '{APP_VERSION}'),
            StringStruct('InternalName', '{APP_NAME}'),
            StringStruct('LegalCopyright', '{copyright_str}'),
            StringStruct('OriginalFilename', '{exe_name}'),
            StringStruct('ProductName', '{APP_NAME}'),
            StringStruct('ProductVersion', '{APP_VERSION}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    with open("file_version_info.txt", "w", encoding="utf-8") as f:
        f.write(content.strip())


def clean_build_artifacts():
    print("Cleaning up old build artifacts...")
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    for temp_file in [f"{APP_NAME}.spec", "file_version_info.txt"]:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def run_pyinstaller():
    print(f"Building {APP_NAME} v{APP_VERSION} with PyInstaller...")
    
    generate_version_info_file()

    # Define the separator based on OS (Windows uses ';', Mac/Linux uses ':')
    sep = ";" if sys.platform == "win32" else ":"

    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--icon=assets/icons/app_icon.ico",
        f"--add-data=assets{sep}assets",
        f"--add-data=gui{sep}gui",
        "--name=Norify",
        "main.py",
    ]

    if sys.platform == "win32" and os.path.exists("file_version_info.txt"):
        cmd.append("--version-file=file_version_info.txt")

    # Run the command and stream output
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print(f"\nBuild successful! Executable is located at 'dist/{APP_NAME}.exe'")
    else:
        print("\nBuild failed. Check the errors above.")


if __name__ == "__main__":
    clean_build_artifacts()
    run_pyinstaller()
