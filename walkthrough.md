# Real-Time STT Overlay - Project Walkthrough

## 1. Project Overview
This application provides a real-time, local Speech-to-Text (STT) overlay. It captures system audio (microphone), transcribes it using the `faster-whisper` engine (powered by CTranslate2), and displays it on a semi-transparent, click-through window. It also supports auto-typing the text into other applications.

## 2. Architecture
The project is modularized into the following components:

### **A. Core Engine (`src/engine.py`)**
- **Library**: `faster-whisper` (CTranslate2 backend).
- **Model**: `large-v3-turbo`.
- **Logic**: Runs in a separate thread. It accumulates audio chunks and processes them.
- **Hardware Acceleration**: Automatically detects CUDA. If CUDA fails (e.g., missing libraries), it falls back to CPU (`int8` quantization).
- **Custom Fixes**: Includes logic to manually register `nvidia-cudnn` and `nvidia-cublas` libraries to `LD_LIBRARY_PATH` to resolve `ctranslate2` loading errors.

### **B. Audio Pipeline (`src/audio.py`)**
- **Library**: `sounddevice` (PortAudio wrapper).
- **Logic**: Captures audio in a non-blocking callback and pushes raw bytes to a thread-safe queue.
- **Format**: 16kHz, Mono, Float32 (standard for Whisper).

### **C. GUI & Overlay (`src/gui.py`)**
- **Library**: `PyQt6`.
- **Overlay**: A frameless, transparent window (`WA_TranslucentBackground`).
- **Click-Through**: Uses OS-specific API calls (`user32.dll` on Windows, `Qt.WindowTransparentForInput` on Linux) to ensure mouse clicks pass through the overlay to the window behind it.
- **System Tray**: Provides control without cluttering the taskbar.

### **D. Input & Control (`src/input.py`)**
- **Hotkeys**: `pynput` listens for global hotkeys.
    - **Toggle**: `Pause/Break` key.
    - **Kill**: `Ctrl + Alt + Esc`.
- **Text Injection**: `pyautogui` types short text; `pyperclip` handles long text via clipboard swapping.

## 3. Environment & Setup (Crucial)
The project relies on specific versions of Python libraries and system dependencies.

### **The "Environment Mismatch" Issue**
You may have encountered `OSError: PortAudio library not found` or `Could not import nvidia libraries`. This happens when dependencies are split between your system Python (`/usr/lib/...`) and a virtual environment (`.venv`).

**Correct Setup:**
1.  **System Dependencies**:
    ```bash
    sudo apt-get install libportaudio2
    ```
2.  **Python Environment**:
    Always run the application using the virtual environment where **ALL** dependencies (including `nvidia-*` packages) are installed.

### **Recommended Run Command**
Use the provided `run.sh` script or execute explicitly:
```bash
# Install everything in venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/pip install nvidia-cublas-cu12 nvidia-cudnn-cu12

# Run with venv python
./.venv/bin/python main.py
```

## 4. Troubleshooting

### **Error: `cudnnCreateTensorDescriptor` / `Unable to load ...`**
- **Cause**: `ctranslate2` cannot find the cuDNN libraries.
- **Solution**: Ensure `nvidia-cudnn-cu12` and `nvidia-cublas-cu12` are installed **in the same environment** as `faster-whisper`. The `src/engine.py` script attempts to automatically add them to `LD_LIBRARY_PATH`.

### **Error: `PortAudio library not found`**
- **Cause**: Missing system library.
- **Solution**: `sudo apt-get install libportaudio2`.

### **Dimension Mismatch Error**
- **Cause**: Audio buffer shape mismatch (1D vs 2D).
- **Solution**: Fixed in `src/engine.py` by flattening the array.

## 5. Future Improvements
- **VAD Tuning**: Adjust `min_silence_duration_ms` in `src/engine.py` for better segmentation.
- **Model Caching**: The model is currently downloaded to the default cache. You can specify a custom path.
## 6. System Integration (Global Launch)

### **Desktop Entry**
A `.desktop` file has been created at `algospeak.desktop`. To install it so it appears in your app launcher:
```bash
cp algospeak.desktop ~/.local/share/applications/
chmod +x ~/.local/share/applications/algospeak.desktop
```

### **Global Hotkey (Auto-Start)**
To launch the app with a keyboard shortcut (e.g., `Super+Alt+S`) regardless of focus:
1.  Open **Settings** > **Keyboard** > **View and Customize Shortcuts**.
2.  Select **Custom Shortcuts**.
3.  Click **Add Shortcut**.
    - **Name**: AlgoSpeak
    - **Command**: `/home/panu/workspaces/algospeak/run.sh`
    - **Shortcut**: Press your desired key combo.

