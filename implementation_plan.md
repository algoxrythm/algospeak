# UX Improvement Plan

## Goal
Implement "Audio-Tactile" feedback and "Auto-Hide" to make the application feel responsive and clutter-free.

## Proposed Changes

### 1. Audio Feedback (Procedural)
Instead of managing external `.wav` files, we will synthesize sounds on the fly using `sounddevice` and `numpy`.
- **Method**: `generate_tone(frequency, duration)`
- **Sounds**:
    - **Success (Inject)**: High pitch chirp (e.g., 880Hz -> 1760Hz slide).
    - **Deletion (Cut/Clear)**: Low pitch decay (e.g., 400Hz -> 100Hz).
    - **Error**: Buzzer.

### 2. GUI Polishing (`src/gui.py`)
- **Reactive Visuals**:
    - Add `flash_border(color_hex)`: Temporarily changes the window border color.
- **Auto-Hide**:
    - Add `idle_timer`: If no text update for 5 seconds, fade `windowOpacity` to 0.1.
    - **Wake Up**: Instantly restore opacity to 1.0 on any signal.
- **Signal Handling**:
    - Add `signal_handler.play_sound.emit(str)` to trigger sounds from the GUI thread (or dedicated audio thread) to avoid blocking the engine.

### 3. Engine Wiring (`src/engine.py`)
- **Inject**: Emit `play_sound("success")`, trigger Green flash.
- **Cut/Clear**: Emit `play_sound("delete")`, trigger Red flash.
- **Wake**: Ensure any VAD activity resets the Auto-Hide timer.

## Verification
1.  **Test**: Speak "Test Inject".
    -   *Expect*: High chirp sound + Green border flash.
2.  **Test**: Speak "Word Cut".
    -   *Expect*: Low decay sound + Red border flash.
3.  **Test**: Wait 5 seconds.
    -   *Expect*: Overlay fades out.
4.  **Test**: Speak.
    -   *Expect*: Overlay snaps back to full visibility.
