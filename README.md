# Neuro-Gaze 👁️⚡

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PySide6 / Qt6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-41CD52.svg)](https://www.qt.io/)
[![MediaPipe](https://img.shields.io/badge/Vision-MediaPipe%20Face%20Landmarker-FFA800.svg)](https://developers.google.com/mediapipe)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)](https://microsoft.com/windows)
[![Offline First](https://img.shields.io/badge/Privacy-100%25%20Offline%20Vision-green.svg)](#-privacy--security)
[![License: Open Source](https://img.shields.io/badge/License-MIT%20%2F%20Open%20Source-teal.svg)](LICENSE)

> **Next-Generation Multi-Modal Assistive Ecosystem & Eye-Controlled Autonomous Platform**  
> Engineered for individuals living with Locked-in Syndrome (LIS), Amyotrophic Lateral Sclerosis (ALS), Cerebral Palsy, Severe Motor Paralysis, and Speech Impairments.

---

## 🌟 Overview

**Neuro-Gaze** is an integrated, non-invasive assistive technology suite developed in Python and PySide6 (Qt6). It empowers individuals with severe physical and verbal limitations to independently navigate digital environments, control physical appliances, steer motorized mobility systems, communicate fluently, and engage in cognitive leisure activities — **using only subtle head orientation and eye movements**.

Unlike costly commercial eye-tracking rigs that demand proprietary hardware or uncomfortable head-mounted apparatus, **Neuro-Gaze operates on any standard consumer webcam** using accelerated on-device computer vision.

---

## ✨ Comprehensive Feature Ecosystem

### 🎯 1. Gaze Cursor Steering & Multi-Modal Clicks
- **Head Vector Cursor Control**: Nose bridge spatial tracking via MediaPipe Face Landmarker (468/478 landmarks) translates orientation into fluid desktop cursor coordinates.
- **Dynamic Exponential Smoothing**: Dual-stage jitter filtering (`alpha_min` to `alpha_max`) dampens micro-tremors while maintaining snappy, responsive cursor velocity.
- **Blink Activation**: Precision Eye Aspect Ratio (EAR) blink detection with debounce timing and cooldown guards to prevent involuntary double-clicks.
- **Hands-Free Dwell Clicking (`DwellButton`)**: Gaze upon any button or UI element for a customizable dwell duration (e.g. 600 ms) with a dynamic circular progress ring animation to execute clicks without blinking.

---

### ♿ 2. Adaptive Wheelchair Navigation System
- **Gaze-Directed Steering**: Directional controls for **Forward**, **Backward/Reverse**, **Turn Left**, **Turn Right**, and **Immediate Stop**.
- **Hardware IoT Bridge**: Direct wireless integration with microcontroller motor drivers (ESP32 / ESP8266) over SoftAP or local Wi-Fi.
- **Ultrasonic Obstacle Avoidance**: Dual front and rear distance telemetry integration with automatic emergency safety cutoff at calibrated distances (45 cm threshold).
- **Live Telemetry HUD**: Real-time status indicators showing driving states, motor commands, and collision alerts.

---

### 🏠 3. Smart Home & Environmental IoT Automation
- **Appliance Relay Switching**: Gaze-operated controls for room lights (**Light ON / OFF**), ventilation (**Fan ON / OFF**), and home appliances.
- **Local Network API**: Transmits lightweight HTTP GET requests to local relay modules without third-party cloud intermediaries.
- **Acoustic Voice Confirmation**: Instant text-to-speech confirmation vocalizing the action taken (e.g., *"Light ON"*).

---

### 🎮 4. Entertainment, Wellness & Cognitive Rehabilitation Hub
An integrated leisure suite tailored specifically for eye-tracking interaction:
- **Accessible Games Suite**:
  - **Memory Match**: Card-flipping cognitive challenge with eye dwell / click selection.
  - **Tic-Tac-Toe**: Classic strategy game with an interactive AI opponent.
  - **Zen Bubble Pop**: Stress-relieving, casual physics bubble arena.
  - **Simon Sequence**: Audio-visual memory game with multi-colored ring feedback.
  - **Precision Gaze Target**: Reaction and gaze accuracy training game.
- **Health & Mindfulness Suite**:
  - **Paced Breathing Guide**: Visual expanding and contracting animated orb guiding restorative pulmonary exercises.
  - **Facial Muscle Relaxation**: Guided visual routines to mitigate ocular fatigue and facial muscle tension.
- **Integrated Media Player**:
  - Offline multi-track audio player with album art covers, progress seeking, volume adjustments, and continuous playback.
- **Creative Studio**:
  - Gaze-driven digital art canvas for expressive drawing and creative therapy.

---

### 💬 5. Augmentative & Alternative Communication (AAC)
- **Virtual Eye Keyboard**: Full on-screen keyboard featuring large target keys, backspace, clear, and instant voice output on ENTER.
- **Predictive Word Completion**: Built-in word suggestion engine proposing frequent completions as characters are typed to minimize keystrokes.
- **Quick Phrases**: Instant speech buttons for urgent daily needs (*"I need help"*, *"Yes"*, *"No"*, *"Water please"*, *"Food please"*, *"Toilet"*, *"Thank you"*).
- **Text-to-Speech (TTS) Engine**: Offline voice synthesizer with configurable speech rate, volume, and voice selection.

---

### 🎯 6. Multi-Point Interactive Calibration Wizard
- **5-Point Spatial Calibration**: Guided visual wizard (Top-Left, Top-Right, Center, Bottom-Left, Bottom-Right) mapping the user's comfortable range of motion.
- **Adaptive Threshold Tuning**: Automatically calculates normalized bounding limits and personalized EAR baseline for varying lighting and camera distances.

---

### 🚨 7. Caregiver Alerting & Remote Distress System
- **Caregiver Summon Ping**: One-click non-emergency alert to summon assistance.
- **Emergency Distress Alarm**: Triggers high-priority local acoustic sirens and visual warnings.
- **Asynchronous Webhook Notifications**: Non-blocking background dispatch to endpoints (Discord, Slack, Home Assistant, or custom HTTP webhooks) to notify remote caregivers immediately.

---

### 🔊 8. Polyphonic Offline Audio Synthesizer
- **100% Offline Procedural Audio**: Built using `sounddevice` and `numpy` for zero-latency auditory feedback.
- **Acoustic Tones**: Auditory cues for dwell progress, clicks, error states, and emergency sirens.
- **Ambient Soundscapes**: Procedural background audio generators (Rain, Ocean Waves, Wind, Fireplace) promoting calm during prolonged sessions.

---

### 🎨 9. Personalized Profiles & Modern Theming
- **Cyber-Medical UI**: High-contrast glassmorphism aesthetic built with custom Qt painting and responsive scaling.
- **Themes**: **Obsidian Dark**, **Clean Light**, and **High-Contrast Mode** (engineered for visual impairments).
- **Scalable UI**: Four interface scaling modes (**Small**, **Medium**, **Large**, **Extra Large**) supporting diverse monitor resolutions and viewing distances.
- **Multi-User Profiles**: Save and toggle between custom calibration and preferences for multiple users.

---

### 🛡️ 10. Safety & Emergency Failsafes
- **Persistent Emergency Stop**: Always-accessible emergency stop bar pinned across every screen.
- **Global ESC Hotkey**: Pressing the ESC key instantly disengages tracking and freezes cursor control.
- **Explicit Activation**: Mouse emulation requires explicit user initiation (`START TRACKING`).

---

## 🖥️ Application Navigation Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  NEURO-GAZE  │  Multi-Modal Assistive Ecosystem                             │
│  [Camera: ●]  [Face: ●]  [Tracking: ●]  [Voice: ●]  [🔔 Ping]  [🚨 EMERGENCY] │
├───────────────────┬─────────────────────────────────────────────────────────┤
│ 📹 Dashboard       │                                                         │
│ ♿ Wheelchair      │                                                         │
│ 🏠 Smart Home     │                   ACTIVE WORKSPACE                      │
│ ⌨️ Keyboard        │      (Camera Feed / Assistive Controls / Games /        │
│ 💬 Quick Phrases  │           Wheelchair HUD / Home Automation /            │
│ 🎮 Entertainment  │                   Settings / Wizard)                    │
│ 🎯 Calibration    │                                                         │
│ ⚙️ Settings        │                                                         │
│ ℹ️ About          │                                                         │
├───────────────────┴─────────────────────────────────────────────────────────┤
│  ESC — Emergency Stop                       [🛑 EMERGENCY STOP (F12 / ESC)] │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Directory Structure

```
Neuro-Gaze/
│
├── main.py                    # Application bootstrap, splash loader & runtime lifecycle
├── requirements.txt           # Python dependency manifest
├── Neuro-Gaze.spec            # PyInstaller multi-asset bundle specification
├── README.md                  # Comprehensive project documentation
├── create_icon.py             # App icon generator script
│
├── assets/                    # Static visual and audio assets
│   ├── app_icon.ico           # Application window & binary icon
│   ├── app_icon_custom.ico    # Alternate high-res icon
│   ├── logo.jpg               # Branding & showcase splash logo
│   └── music/                 # Built-in audio tracks & album art
│       ├── covers/            # Album artwork thumbnails
│       └── songs/             # Audio files for Entertainment Hub
│
├── models/
│   └── face_landmarker.task   # MediaPipe Face Landmarker model (auto-downloaded)
│
├── ui/                        # User interface modules (PySide6 / Qt6)
│   ├── main_window.py         # Shell window, sidebar navigation, headers & status pills
│   ├── dashboard.py           # Live camera feed, face mesh visualizer & tracking stats
│   ├── wheelchair.py          # Directional wheelchair steering HUD & ultrasonic telemetry
│   ├── home_automation.py     # Environmental IoT appliance relay toggles (lights, fan)
│   ├── keyboard.py            # Eye-controlled AAC keyboard with word autocomplete
│   ├── phrases.py             # Quick-phrase audio vocalization grid
│   ├── entertainment.py       # Games (Memory, Simon, TicTacToe, Bubbles), Breathing & Music
│   ├── calibration.py         # 5-point head movement & EAR calibration wizard
│   ├── settings.py            # Comprehensive preference manager & webhook config
│   ├── about.py               # System specifications, project links & developer showcase
│   ├── components.py          # Reusable accessible widgets (DwellButton, FadingStack)
│   ├── theme.py               # Dynamic design tokens, color palettes & scale multipliers
│   ├── tutorial.py            # Guided 5-step interactive onboarding spotlight overlay
│   └── splash.py              # Animated startup splash screen with status progress
│
├── core/                      # System engines & processing threads
│   ├── face_tracker.py        # QThread worker: MediaPipe landmark pipeline & mouse loops
│   ├── eye_tracker.py         # Pure Eye Aspect Ratio (EAR) mathematical calculations
│   ├── mouse_controller.py    # Exponential cursor smoothing & PyAutoGUI bridge
│   ├── camera.py              # VideoCapture manager & automatic model acquisition
│   ├── speech_engine.py       # Asynchronous pyttsx3 Text-To-Speech worker
│   ├── audio_synth.py         # 100% offline polyphonic procedural audio & tone mixer
│   ├── webhook.py             # Non-blocking caregiver alerting engine (Discord/Slack/HTTP)
│   ├── session.py             # Local session duration & emergency event logging
│   └── lifecycle.py           # Activity lifecycle manager for background tasks
│
└── utils/                     # Shared utilities & helpers
    ├── config.py              # JSON configuration manager & profile system
    ├── words.py               # English vocabulary dataset for predictive keyboard text
    ├── logger.py              # Multi-handler rotating logger (~/.Neuro-Gaze/app.log)
    └── resource.py            # Runtime asset & directory resolver (dev + PyInstaller)
```

---

## ⚙️ System Requirements

| Component | Minimum Requirement | Recommended |
|---|---|---|
| **Operating System** | Windows 10 (64-bit) | Windows 11 (64-bit) |
| **Python** | Python 3.10 | Python 3.11 or 3.12 |
| **Camera** | Built-in laptop webcam (720p @ 30 FPS) | External 1080p USB Webcam (good low-light SNR) |
| **Processor** | Intel Core i3 / AMD Ryzen 3 | Intel Core i5 / AMD Ryzen 5 or higher |
| **Memory (RAM)** | 4 GB | 8 GB or higher |
| **Audio** | Integrated speaker / 3.5mm jack | External speakers for clear TTS & alert sirens |
| **Microcontroller (Optional)** | ESP32 / ESP8266 (for wheelchair / IoT) | ESP32 DevKit v1 with SoftAP enabled |

---

## 🚀 Installation & Setup

### 1. Clone Repository & Create Virtual Environment

```bash
# Clone the repository
git clone https://github.com/Mahiiim/Neuro-Gaze.git
cd Neuro-Gaze

# Create a virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
venv\Scripts\Activate.ps1
# Windows (Command Prompt):
venv\Scripts\activate.bat
```

### 2. Install Required Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Optional**: To enable offline procedural audio synthesis, ensure `sounddevice` is installed:
> ```bash
> pip install sounddevice
> ```

### 3. Launch the Application

```bash
python main.py
```

*Note: On the first launch, the required MediaPipe Face Landmarker model (`~3.5 MB`) is downloaded automatically if not already present.*

---

## 🎮 User Guide: Getting Started

1. **Camera Alignment**: Sit comfortably in front of your webcam, ensuring adequate front-facing lighting with your face centered in frame.
2. **Onboarding Walkthrough**: On your initial launch, follow the built-in **5-Step Interactive Tutorial** for a guided introduction to cursor movement, blinking, and safety stops.
3. **Calibration**: Navigate to **🎯 Calibration** in the sidebar. Follow the 5-point calibration wizard (looking at the corner dots) to map your unique head movement range.
4. **Initiate Tracking**: From the **📹 Dashboard**, click **▶ START TRACKING** to engage head-movement cursor control.
5. **Clicking**:
   - **Blink**: Perform a distinct natural blink to click buttons.
   - **Dwell**: Alternatively, rest your gaze steadily over any interactive button until the circular progress indicator completes.
6. **Emergency Halt**:
   - Press the physical **ESC** key, or click **🛑 EMERGENCY STOP** at any time to immediately disengage all mouse control.

---

## 🔌 Hardware Integration (Mobility & Smart Home)

Neuro-Gaze is engineered to interface directly with low-cost microcontrollers for real-world autonomy:

```
┌─────────────┐   Wi-Fi / SoftAP    ┌──────────────────────────┐
│ Neuro-Gaze  │ ──────────────────> │ ESP32 Microcontroller    │
│ Computer    │  HTTP REST Commands │ (Default IP: 192.168.4.1)│
└─────────────┘                     └─────────────┬────────────┘
                                                  │
                  ┌───────────────────────────────┴───────────────────────────────┐
                  ▼                                                               ▼
        ┌───────────────────┐                                           ┌───────────────────┐
        │ Dual Motor Driver │                                           │ Relay Board       │
        │ (L298N / Smart    │                                           │ (5V Active Low)   │
        │ Wheelchair Base)  │                                           │                   │
        │                   │                                           │ • Relay 1: Light  │
        │ • Left Motor      │                                           │ • Relay 2: Fan    │
        │ • Right Motor     │                                           │ • Relay 3/4: Aux  │
        │ • Ultrasonic F/R  │                                           └───────────────────┘
        └───────────────────┘
```

- **Wheelchair Endpoints**: `http://192.168.4.1/{F|B|L|R|S}` for directional driving and stop.
- **Ultrasonic Telemetry**: `http://192.168.4.1/status` returns real-time obstacle proximity in JSON format.
- **Home Automation Endpoints**: `http://192.168.4.1/home/{light_on|light_off|fan_on|fan_off}` for appliance switching.

---

## ⚙️ Configuration & Customization

All user preferences and profile parameters are managed through the **⚙️ Settings** tab and persisted locally at `~/.Neuro-Gaze/config.json`:

| Parameter | Default | Description |
|---|---|---|
| `blink_threshold` | `0.20` | Eye Aspect Ratio (EAR) cutoff value below which a blink is registered |
| `click_cooldown` | `1.0s` | Minimum debounce interval between consecutive blink clicks |
| `sensitivity_x` / `sensitivity_y` | `1.0` | Cursor displacement multiplier along horizontal and vertical axes |
| `smoothing_alpha_min` | `0.05` | Jitter smoothing factor applied during subtle head resting |
| `smoothing_alpha_max` | `0.25` | Responsive tracking factor applied during rapid head turns |
| `speech_rate` | `150` | Words per minute for speech synthesis vocalization |
| `speech_volume` | `1.0` | Audio volume multiplier for text-to-speech output |
| `theme` | `dark` | Visual theme: `dark`, `light`, or `high_contrast` |
| `ui_scale` | `medium` | Display scaling: `small`, `medium`, `large`, `extra_large` |
| `webhook_url` | `""` | Optional Discord, Slack, or generic HTTP webhook URL for caregiver alerting |

---

## 🏗️ Building Standalone Windows Executable

To package Neuro-Gaze into a standalone distributable binary:

```bash
# Install PyInstaller
pip install pyinstaller

# Build using the custom spec file
pyinstaller Neuro-Gaze.spec
```

The compiled application bundle will be created at:
```
dist/Neuro-Gaze/Neuro-Gaze.exe
```

---

## 🔒 Privacy & Security

- **100% On-Device Computer Vision**: Video frames from your webcam are processed directly in local RAM using MediaPipe and OpenCV. **No video, pictures, or facial landmark coordinates are ever transmitted over the network.**
- **Zero Cloud Dependence**: Communication, speech synthesis, games, and tracking run completely offline without requiring internet connectivity.
- **Configurable Webhook Alerts**: Webhook alerts only send textual assistance requests and emergency pings to endpoints explicitly designated by the user in Settings.
- **No Telemetry Tracking**: User session history and error logs remain strictly local to your machine under `~/.Neuro-Gaze/`.

---

## 🤝 Contributing & Community

Contributions from developers, occupational therapists, accessibility advocates, and assistive researchers are warmly welcomed:

1. **Fork** the repository: [https://github.com/Mahiiim/Neuro-Gaze](https://github.com/Mahiiim/Neuro-Gaze)
2. **Create** your feature branch: `git checkout -b feature/NewAccessibleModule`
3. **Commit** your enhancements: `git commit -m "Add New Accessible Module"`
4. **Push** to your branch: `git push origin feature/NewAccessibleModule`
5. **Open** a Pull Request for review.

---

## 📜 License & Acknowledgements

- Distributed under the **MIT License**.
- Developed with gratitude to the open-source community: **PySide6 (The Qt Company)**, **Google MediaPipe**, **OpenCV**, and accessibility researchers worldwide.
- Dedicated to empowering individuals with Locked-in Syndrome, ALS, and motor paralysis to regain autonomy, voice, and independence.
