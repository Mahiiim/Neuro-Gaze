# Neuro-Gaze

**Neuro-Gaze** is a professional **Eye-Controlled Assistive Communication System** built with Python and PySide6. It enables individuals with speech or motor impairments to control a computer and communicate using only head movements and eye blinks — no physical mouse or keyboard required.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Head Movement → Mouse** | Nose tip position drives the system cursor via MediaPipe Face Landmarker |
| **Blink → Click** | Eye Aspect Ratio (EAR) blink detection triggers mouse clicks |
| **Quick Phrases** | 7 pre-set phrases spoken instantly via text-to-speech |
| **Eye Keyboard** | Full on-screen keyboard — type freely and speak with ENTER |
| **Settings** | Configurable blink threshold, sensitivity, camera, speech, and more |
| **Emergency Stop** | One-click or ESC key halts all mouse control instantly |
| **Auto Model Download** | MediaPipe model auto-downloads on first launch |

---

## 🖥️ Application Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Neuro-Gaze  │ Eye-Controlled Assistive Communication      │
│  [Camera: ●] [Face: ●] [Tracking: ●] [Voice: ●]           │
├───────────┬──────────────────────────────────────────────────┤
│ Dashboard │  Live webcam feed + EAR display + controls      │
│ Keyboard  │                                                  │
│ Phrases   │                                                  │
│ Settings  │                                                  │
│ About     │                                                  │
├───────────┴──────────────────────────────────────────────────┤
│  ESC — Emergency Stop    [🛑 EMERGENCY STOP]                 │
└──────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
Neuro-Gaze/
│
├── main.py                    # Entry point & startup sequence
├── requirements.txt
├── Neuro-Gaze.spec           # PyInstaller build spec
├── README.md
│
├── models/
│   └── face_landmarker.task   # Auto-downloaded on first launch
│
├── assets/
│   └── app_icon.ico
│
├── ui/
│   ├── main_window.py         # Root QMainWindow (sidebar + header)
│   ├── dashboard.py           # Live camera feed & tracking controls
│   ├── keyboard.py            # Eye-controlled virtual keyboard
│   ├── phrases.py             # Quick phrase buttons
│   ├── settings.py            # All configurable settings
│   └── about.py               # App info page
│
├── core/
│   ├── face_tracker.py        # QThread — MediaPipe + EAR + mouse loop
│   ├── eye_tracker.py         # Pure EAR calculation functions
│   ├── mouse_controller.py    # Smoothing + PyAutoGUI calls
│   ├── speech_engine.py       # Pyttsx3 TTS (background thread)
│   └── camera.py              # Camera open/release + model download
│
└── utils/
    ├── resource.py            # Path resolution (dev + PyInstaller)
    ├── config.py              # JSON config load/save/defaults
    └── logger.py              # Rotating file logger → ~/.Neuro-Gaze/app.log
```

---

## ⚙️ Requirements

- Python 3.10+
- Windows 10/11 (tested)
- Webcam

---

## 🚀 Installation & Running

### 1. Clone and set up

```bash
git clone https://github.com/Mahiiim/Neuro-Gaze.git
cd Neuro-Gaze
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### 2. Run

```bash
python main.py
```

On first launch, the MediaPipe model (`~3.5 MB`) will be downloaded automatically.

---

## 🎮 How to Use

1. Launch the app — the **Dashboard** opens with the live camera feed.
2. Click **▶ START TRACKING** to enable head movement → cursor control.
3. Navigate to **Quick Phrases** or **Eye Keyboard** using the sidebar.
4. Use **head movement** to position the cursor over buttons.
5. **Blink** to click the selected button.
6. Press **ESC** or click **🛑 EMERGENCY STOP** at any time to halt tracking.

---

## 🏗️ Build Windows .exe

```bash
pip install pyinstaller
pyinstaller Neuro-Gaze.spec
```

The output will be in `dist/Neuro-Gaze/Neuro-Gaze.exe`.

> **Note:** First copy or pre-download `models/face_landmarker.task` before building, or the app will download it on first run.

---

## ⚙️ Configuration

Settings are stored at `~/.Neuro-Gaze/config.json` and can be changed in the **Settings** page:

- Blink threshold & click cooldown
- X/Y sensitivity & cursor smoothing
- Camera selection
- TTS voice, speed & volume
- Landmark overlay toggle

---

## 📋 Interaction Pipeline

```
WEBCAM
   ↓
MediaPipe Face Landmarker
   ↓
Face Landmarks (468 points)
   ↓
Nose tip (pt 1) ──────────→ Dynamic smoothing → PyAutoGUI.moveTo()
   ↓
Eye Aspect Ratio (EAR)
   ↓
EAR < threshold ──────────→ PyAutoGUI.click()
   ↓
Qt button under cursor receives click
   ↓
Phrase / key press → pyttsx3.say()
```

---

## 🪵 Logs

Application logs are written to:

```
~/.Neuro-Gaze/app.log
```

---

## 🛡️ Safety

- **Emergency Stop** button always visible at the bottom of every screen.
- **ESC** keyboard shortcut always active.
- Mouse control only starts when the user explicitly presses **▶ START TRACKING**.
