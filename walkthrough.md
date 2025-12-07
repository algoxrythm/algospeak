# Algospeak: Real-Time Cyberdeck STT Overlay

**Algospeak** is a high-performance, local Speech-to-Text (STT) application designed for "Cyberdeck" usage. It captures your voice, transcribes it locally using the `faster-whisper` engine (accelerated by CUDA), and overlays the text on your screen in a transparent, click-through window. It can also "type" what you say into any active application.

---

## 1. Project Architecture

The project follows a modular architecture to separate concerns:

### **A. Entry Point (`main.py`)**
- **Role**: The "Conductor".
- **Function**: Initializes the Audio Pipeline, Transcription Engine, GUI, and Input Controller. It wires them together using signals and callbacks.
- **Key Logic**: It creates a bridge thread that pulls audio chunks from the pipeline and pushes them to the engine.

### **B. Core Engine (`src/engine.py`)**
- **Role**: The "Brain".
- **Function**: Runs the `faster-whisper` model (`large-v3-turbo`) in a background thread.
- **Key Logic**:
    - **VAD (Voice Activity Detection)**: Energy-based detection (`vad_threshold`) to ignore silence.
    - **Transcription**: Uses `model.transcribe()` with `language="en"` and a technical `initial_prompt`.
    - **Filtering**: Filters out hallucinations (e.g., "Thank you", "Subtitle") and low-confidence segments.
    - **Hardware**: Auto-detects CUDA; falls back to CPU (int8) if needed.

### **C. Audio Pipeline (`src/audio.py`)**
- **Role**: The "Ears".
- **Function**: Captures raw audio from the default microphone.
- **Key Logic**: Uses `sounddevice` (PortAudio wrapper) in a non-blocking callback mode to fill a thread-safe `queue`. Format is 16kHz Mono Float32.

### **D. GUI & Overlay (`src/gui.py`)**
- **Role**: The "Face".
- **Function**: Displays status and text in a "Cyberpunk/Glassmorphic" overlay.
- **Key Logic**:
    - **Transparency**: Uses `WA_TranslucentBackground`.
    - **Click-Through**: Uses OS-specific API calls (`user32.dll` on Windows, `Qt.WindowTransparentForInput` on Linux) so you can interact with windows *behind* the overlay.
    - **System Tray**: Provides a menu to Hide/Show/Quit the app.

### **E. Input Controller (`src/input.py`)**
- **Role**: The "Hands".
- **Function**: Listens for global hotkeys and handles text injection.
- **Key Logic**:
    - **Hotkeys**: Uses `pynput` to listen for global keys.
    - **Injection**: Uses `pyautogui` for short text and `pyperclip` (clipboard paste) for long text to ensure speed.
    - **Commands**: Handles voice commands like "delete", "enter", "clear line".

---

## 2. Installation & Setup

### **Prerequisites (System)**
You must install these system-level dependencies before running the Python code.

**On Ubuntu/Debian:**
```bash
sudo apt-get update
# Required for audio capture
sudo apt-get install -y libportaudio2
# Required for clipboard injection (fixes 'Pyperclip could not find a copy/paste mechanism' error)
sudo apt-get install -y xclip
```

### **Python Environment**
It is highly recommended to use the provided virtual environment (`.venv`).

1.  **Create/Activate venv** (if not already done):
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install Application Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install NVIDIA Libraries (For CUDA Acceleration)**:
    Required for `ctranslate2` to run on GPU.
    ```bash
    pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
    ```

---

## 3. Usage Guide

### **Running the Application**
You can use the provided helper script `run.sh` which handles the environment for you:

```bash
./run.sh
```

Or run manually using the venv python:
```bash
./.venv/bin/python main.py
```

### **Controls**
| Action | Hotkey / Command | Description |
| :--- | :--- | :--- |
| **Toggle Listening** | `Pause / Break` | Starts or Stops the microphone recording. |
| **Kill App** | `Ctrl + Alt + Esc` | Emergency kill switch to terminate the app immediately. |
| **Delete** | Voice: "Delete" / "Backspace" | Simulates a backspace key press. |
| **Enter** | Voice: "Enter" / "Return" | Simulates the Enter key. |

### **Overlay Feedback**
- **[LISTENING...]**: The mic is open. A "sound wave" visualizer will animate when you speak.
- **Text (Italic/White)**: Partial transcription (updating in real-time).
- **Text (Green)**: Final committed text (injected into your active window).
- **[PAUSED]**: Mic is muted.

---

## 4. Troubleshooting

### **Error: `Pyperclip could not find a copy/paste mechanism`**
- **Reason**: Linux does not have a clipboard utility installed by default for Python to access.
- **Fix**: Run `sudo apt-get install xclip`.

### **Error: `PortAudio library not found`**
- **Reason**: The `sounddevice` library needs the C header files for PortAudio.
- **Fix**: Run `sudo apt-get install libportaudio2`.

### **Error: `Could not load library ...libcudnn...`**
- **Reason**: `faster-whisper` (CTranslate2) needs exact versions of cuDNN and cuBLAS.
- **Fix**:
    1.  Ensure you installed the nvidia pip packages: `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`.
    2.  The application (`engine.py`) automatically tries to link these. If it fails, ensure you are running inside the `.venv`.

### **Dimension Mismatch / Shape Error**
- **Reason**: Sometimes audio chunks are 2D arrays `(N, 1)` instead of 1D `(N,)`.
- **Fix**: The code in `engine.py` has a patch: `if new_data.ndim > 1: new_data = new_data.flatten()`.

---

## 5. Directory Structure

```
algospeak/
├── main.py                     # Entry point
├── requirements.txt            # Python deps
├── run.sh                      # Launcher script
├── algospeak.desktop           # Linux desktop entry (for App Launcher)
├── walkthrough.md              # This file
├── accuracy_options.md         # Research on improving accuracy
├── english_optimization_research.md # Research on English-only constraints
└── src/
    ├── __init__.py
    ├── audio.py                # AudioPipeline class
    ├── engine.py               # TranscriptionEngine class
    ├── gui.py                  # OverlayWindow & SystemTrayApp
    └── input.py                # InputController (Keyboard/Injection)
```
