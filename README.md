# Norify

A lightweight, modern, and privacy-focused desktop notification and utility application built with Python and PyQt6.

> **Note:** Norify currently supports Windows only.

---

## Features

- **Modern Interface** – Clean UI with customizable themes, opacity controls, and polished animations.
- **100% Local-First** – No telemetry, no accounts, and no cloud services. Your data stays on your device.
- **Smart Notifications** – Stackable toast notifications with configurable positioning, timing, and behavior.
- **Persistent Settings** – Automatically saves preferences and restores them between sessions.
- **Lightweight** – Built with Python and PyQt6 with minimal overhead.
- **Open Source** – MIT licensed and fully transparent.

---

## Installation

### Download (Recommended)

Download the latest installer from the GitHub Releases page:

https://github.com/EchoKuroneko/Norify/releases

---

## Running from Source

### 1. Clone the Repository

```bash
git clone https://github.com/EchoKuroneko/Norify.git
cd Norify
```

### 2. Create and Activate a Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python main.py
```

## Building the Executable & Installer
To build the standalone executable and compile the Inno Setup installer locally:
1. Run the PyInstaller build script:
```bash
   python build.py
```
2. Compile the installer using Inno Setup with `setup.iss`.

## License
This project is licensed under the MIT License.