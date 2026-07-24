import os
import shutil
import subprocess
import sys


def clean_build_artifacts():
    print("Cleaning up old build artifacts...")
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    spec_file = "Norify.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)


def run_pyinstaller():
    print("Building Norify with PyInstaller...")

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

    # Run the command and stream output
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\nBuild successful! Your executable is located in the 'dist' folder.")
    else:
        print("\nBuild failed. Check the errors above.")


if __name__ == "__main__":
    clean_build_artifacts()
    run_pyinstaller()
