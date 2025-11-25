# Real-Time STT Overlay

A modular, high-performance, local real-time Speech-to-Text (STT) overlay application using `faster-whisper`, `PyQt6`, and `sounddevice`.

## Prerequisites

- Python 3.10+
- CUDA-capable GPU (Recommended for performance)

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. (Optional) Install CUDA libraries for `faster-whisper` if using GPU.

## Usage

Run the application:
```bash
python main.py
```

## Controls

- **Toggle Recording**: `Pause|Break Key`
- **Kill Switch**: `Pause|Break Key`
- **System Tray**: Right-click the microphone icon in the system tray to Show/Hide overlay or Quit.

## Features

- **Always-on-Top Overlay**: Semi-transparent, click-through overlay displaying live transcription.
- **Local Inference**: Uses `faster-whisper` (large-v3-turbo) for high-accuracy, offline transcription.
- **Auto-Type**: Automatically types transcribed text into the active window.
- **Clipboard Swap**: Efficiently pastes long text to avoid typing delay.
