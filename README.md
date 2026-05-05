# ⏰ Alarm Clock — Python Project

A full-featured alarm clock application in Python, with a **Tkinter GUI** and a fallback **CLI** version.

---

## 📁 Project Structure

```
alarm_clock/
├── alarm_clock.py       # GUI version (Tkinter) ← main app
├── alarm_clock_cli.py   # CLI version (terminal only)
├── requirements.txt
└── README.md
```

---

## 🔧 Installation

### 1. Python Version
Requires **Python 3.10+** (uses modern type hints).

### 2. Install Dependencies
```bash
pip install playsound==1.2.2
```

> `playsound` is **optional** — if not installed, the app falls back to
> `winsound` (Windows) or terminal bell (`\a`) automatically.

> Tkinter is **bundled with standard Python** on Windows and macOS.
> On Linux, install it with:
> ```bash
> sudo apt install python3-tk     # Debian/Ubuntu
> sudo dnf install python3-tkinter  # Fedora
> ```

---

## ▶️ How to Run

### GUI Version (recommended)
```bash
python alarm_clock.py
```

### CLI Version (no display required)
```bash
python alarm_clock_cli.py
```

---

## ✨ Features

| Feature | GUI | CLI |
|---|---|---|
| Set multiple alarms | ✅ | ✅ |
| 12h / 24h time input | ✅ | ✅ |
| Input validation | ✅ | ✅ |
| Sound playback | ✅ | ✅ |
| Snooze (5 min) | ✅ | ✅ |
| Delete / toggle alarm | ✅ | ✅ |
| Custom sound file | ✅ | ❌ |
| Live clock display | ✅ | ✅ |
| Alarm list | ✅ | ✅ |
| Midnight auto-reset | ✅ | ✅ |

---

## 🕐 Accepted Time Formats

| Input | Interpretation |
|---|---|
| `07:30:00` | 07:30:00 AM (24h) |
| `07:30` | 07:30:00 AM (24h) |
| `7:30 AM` | 07:30:00 AM (12h) |
| `07:30 PM` | 19:30:00 (12h) |
| `19:45:30` | 19:45:30 (24h) |

---

## 🔊 Sound Fallback Chain

1. **Custom MP3/WAV** (GUI only, if a file is chosen)
2. **playsound** library (cross-platform)
3. **winsound.Beep** (Windows only)
4. **Terminal bell** (`\a`) — works everywhere

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| `No module named tkinter` | `sudo apt install python3-tk` |
| No sound on Linux | Install `gstreamer` or use the CLI version |
| `playsound` errors | Use `pip install playsound==1.2.2` (not 1.3.0) |
