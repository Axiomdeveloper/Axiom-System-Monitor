# Axiom System Monitor
### Professional System Monitor (Persian UI)

A desktop application that displays live, real system information — similar to Task Manager — with a fully **Persian (Farsi)** and **right-to-left (RTL)** user interface, built with Python and Tkinter.

---

## Project Introduction

Axiom System Monitor shows real, live data about your computer (CPU, RAM, storage and network) and lets you view and terminate running processes. All displayed data is read from the actual system via the `psutil` library — nothing is randomly generated or fake. The interface text is entirely in Persian, but this document explains the project in English for developers and contributors.

## Features

- Live dashboard with information cards for CPU, RAM, Disk and Network
- Real-time charts for CPU usage, RAM usage and network download speed
- "System Status" card (healthy / moderate load / high load) based on CPU, RAM and disk usage
- "System Score" card — an approximate, non-precise benchmark for a quick overview
- Process manager: search, sort by any column, refresh, and terminate processes with a Persian confirmation dialog and an extra warning for sensitive system processes
- "System Information" section: OS, OS version, hostname, architecture, uptime, CPU details and RAM size
- Settings: update interval, dark/light mode toggle, show/hide any dashboard section
- Modern dark UI with card-based, glass-like styling within what plain Tkinter allows
- Highly fault-tolerant: whenever a piece of data is unavailable, the app shows "Not available" instead of crashing
- Performance-friendly: uses Tkinter's `after()` scheduler so the UI never freezes

---

## Requirements

- Python 3.9 or newer
- `tkinter` (usually bundled with Python; on some Linux distributions install it separately, e.g. `sudo apt install python3-tk`)
- `psutil` (installed via `requirements.txt`)

## Installation

1. Install Python from the official site: https://www.python.org/downloads/
   On Windows, make sure to check "Add Python to PATH" during installation.
2. Verify the installation:

```bash
python --version
```

3. From the project folder, install the required library:

```bash
pip install -r requirements.txt
```

## Running the Application

```bash
python main.py
```

---

## Vazirmatn Font Installation Guide

The application uses the **Vazirmatn** font for correct and beautiful rendering of Persian text. If this font is not installed on your system, the app **will not crash** — it automatically falls back to another font (e.g. Tahoma) and shows a warning banner inside the app.

### How to download and install Vazirmatn

1. Official download link: **https://github.com/rastikerdar/vazirmatn/releases/latest**
   (Alternative source: https://fontsfarsi.com/vazirmatn/)
2. Download the latest release and extract the archive.
3. **Windows:** Right-click the `.ttf` files and choose "Install".
4. **macOS:** Double-click the `.ttf` files and click "Install Font" in Font Book.
5. **Linux:** Copy the `.ttf` files into `~/.local/share/fonts` and run `fc-cache -f -v`.
6. After installing the font, **fully close and re-run the application** so it can detect and use the new font.

---

## Troubleshooting

| Issue | Solution |
|---|---|
| "No module named psutil" | Run `pip install -r requirements.txt` |
| "No module named tkinter" (Linux) | Run `sudo apt install python3-tk` |
| Persian text doesn't render correctly | Install the Vazirmatn font as described above |
| Access denied when terminating a process | Run the app with administrator/root privileges |
| No GPU or temperature sensor data | The app only relies on `psutil`, which does not expose GPU/temperature data on every system. You may optionally install specialized libraries (e.g. `GPUtil` or `py3nvml` for NVIDIA GPUs) and extend the code — their absence never prevents the app from running. |

---

## Project Structure

```
Axiom-System-Monitor/
├── main.py           ← All application code (UI and logic)
├── requirements.txt   ← Required Python packages
├── README_FA.md        ← Persian documentation (this project's primary README)
└── README_EN.md        ← This file, English documentation
```

Everything lives in a single `main.py` file to keep the project simple to use and distribute.

---

## Simple Explanation for Beginners

**What is this program?**
Axiom System Monitor is a small application that shows you what your computer is doing right now: how busy its "brain" (the processor) is, how much temporary memory is in use, how full your storage drive is, and how fast the computer is sending or receiving data over the internet.

**What is a CPU?**
CPU stands for "Central Processing Unit" — think of it as the computer's brain. Everything the computer does (opening an app, playing a video, running a game) is processed by the CPU. When the CPU is very busy (e.g. 90% or higher), the computer may feel slow.

**What is RAM?**
RAM is the computer's temporary memory. When you open a program, its data is temporarily stored in RAM so the computer can access it quickly. If RAM fills up, the computer slows down because it has to rely on the much slower hard drive instead.

**Why is this information shown?**
Seeing this information helps you understand why your computer might be running slowly, which program is using the most resources, and whether you need to close something or not worry at all.

**How do I run the program?**
1. Install Python (see above).
2. Run `pip install -r requirements.txt` once, inside the project folder.
3. From then on, just run `python main.py` in that same folder whenever you want to open the app.
4. The application window will open, and you can switch between the "Dashboard", "Processes", "System Information" and "Settings" tabs.
