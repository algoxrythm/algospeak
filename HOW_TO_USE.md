# Algospeak: The Comprehensive User Manual

This guide documents every aspect of **Algospeak** that you can use, modify, and customize. It is designed for both end-users and developers who want to tweak the "Cyberdeck" experience.

---

## 1. Quick Start

### **Launching the App**
You have two ways to start the system:

1.  **Via Terminal (Recommended)**:
    ```bash
    ./run.sh
    ```
2.  **Via Global Launcher**:
    If you installed the `.desktop` file, press `Super` (Windows Key) and search for "Algospeak".

---

## 2. Controls & Interaction

### **Keyboard Hotkeys**
These hotkeys work **globally**, meaning the app doesn't need to be in focus.

| Key | Action | Code Location |
| :--- | :--- | :--- |
| **`Pause / Break`** | **Toggle Listening**. Mutes/Unmutes the mic. | `src/input.py` (Line 17) |
| **`Ctrl` + `Alt` + `Esc`** | **Kill Switch**. Instantly terminates the app. | `src/input.py` (Line 43) |

> **Modifying Hotkeys**:
> Open `src/input.py` and change `self.HOTKEY_TOGGLE` or the check in `on_press` to use different `keyboard.Key` values (e.g., `keyboard.Key.f12`).

### **Voice Commands**
The system listens for specific keywords to trigger actions instead of typing text.

| Command Phrase | Action |
| :--- | :--- |
| **"Delete"** / **"Backspace"** | Presses the `Backspace` key once. |
| **"Enter"** / **"Return"** | Presses the `Enter` key. |
| **"Clear Line"** | Deletes the entire current line (`Ctrl+Backspace`). |

> **Adding Commands**:
> Open `src/input.py`, look for the `inject_text` method. Add new `if` conditions:
> ```python
> if lower_text == "save file":
>     pyautogui.hotkey('ctrl', 's')
>     return
> ```

---

## 3. Configuration & Tuning (The "Engine")

All core logic resides in `src/engine.py`. You can adjust these variables to change how the AI behaves.

### **A. Changing the AI Model**
**Variable**: `self.model_size` (Line 12)
- **Default**: `"large-v3-turbo"`
- **Options**:
    - `"tiny.en"`, `"base.en"`, `"small.en"`: Extremely fast, lower accuracy.
    - `"medium.en"`: Balanced.
    - `"large-v3"`: Maximum accuracy, slower, requires ~10GB VRAM.
    - `"distil-large-v3"`: Faster version of large.

### **B. Adjusting Sensitivity (VAD)**
**Variable**: `self.vad_threshold` (Line 31)
- **Default**: `0.008`
- **How to tune**:
    - **Increase (e.g., 0.02)**: If it picks up breathing or keyboard clicks.
    - **Decrease (e.g., 0.002)**: If it fails to catch whispers.

### **C. Anti-Hallucination Settings**
The model sometimes "invents" text during silence. We filter this out.
- **`self.min_logprob`** (Line 37): Default `-0.8`. Segments with lower confidence are dropped.
- **`self.banned_phrases`** (Line 41): A set of words to **never** type.
    - *Common culprits*: "Thank you", "Subs by", "Copyright".
    - **Action**: Add new phrases here if you see them repeatedly appearing when you aren't speaking.

### **D. Initial Prompt (Context)**
**Line 174**: `initial_prompt="Cyberdeck stream log."`
- **Purpose**: Primes the model with context.
- **Modification**: Change this to match your current task for better accuracy.
    - *Coding*: `"Python class function def import numpy pandas."`
    - *Writing*: `"Fantasy novel writing chapter one dialogue."`

---

## 4. Customizing the Visuals (The "GUI")

The overlay look and feel is defined in `src/gui.py`.

### **A. Window Position & Size**
**Method**: `init_ui` (Line 78)
```python
self.setGeometry(100, 800, 600, 150)
# Format: (x_pos, y_pos, width, height)
```
- **x_pos/y_pos**: Coordinates on your screen.
- **width/height**: Size of the overlay.

### **B. Colors & Theme**
The visualizer colors are in `AudioVisualizer.paintEvent` (Line 48-49).
```python
gradient.setColorAt(0, QColor(0, 255, 255, 200))   # Start Color (Cyan)
gradient.setColorAt(1, QColor(255, 0, 255, 200))   # End Color (Magenta)
```
- **Modification**: Change RGB values to simpler colors (e.g., Green/Black) for a "Matrix" terminal look.

### **C. Fonts**
**Method**: `init_ui` (Line 88, 94)
- Current: `"Consolas"`.
- Change to `"Arial"`, `"Roboto"`, or any installed system font.

---

## 5. Audio Settings

Located in `src/engine.py` / `src/audio.py`.

- **Input Device**: Currently uses the system default.
- **Sample Rate**: Hardcoded to `16000` (required by Whisper). Do not change this unless you are adding a resampling layer.

---

## 6. Advanced: Running on CPU vs GPU

The system tries to auto-detect CUDA.

- **Force CPU**:
    In `src/engine.py`, change `device="auto"` to `device="cpu"` in `__init__`.
- **Force Low Precision (Faster)**:
    Change `compute_type="default"` to `compute_type="int8"`.

---

## 7. Troubleshooting "Click-Through"

If you cannot click windows behind the overlay:
- **Linux**: Ensure your Window Manager (KDE/Gnome/Hyprland) supports `NET_WM_WINDOW_TYPE_DOCK` or `Qt.WindowTransparentForInput`.
    - *Fix*: In `src/gui.py` -> `_set_click_through_linux`, try toggling `Qt.WindowType.WindowTransparentForInput`.

---

## Summary of Files to Edit

| Goal | File |
| :--- | :--- |
| **Accuracy / Model / VAD** | `src/engine.py` |
| **Hotkeys / Magic Words** | `src/input.py` |
| **Colors / Size / Position** | `src/gui.py` |
| **Microphone Logic** | `src/audio.py` |
