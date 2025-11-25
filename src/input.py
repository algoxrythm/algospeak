import threading
import time
import pyautogui
import pyperclip
from pynput import keyboard
from typing import Callable, Optional

class InputController:
    def __init__(self, 
                 on_toggle_record: Optional[Callable[[], None]] = None,
                 on_kill_app: Optional[Callable[[], None]] = None):
        self.on_toggle_record = on_toggle_record
        self.on_kill_app = on_kill_app
        self.listener = None
        
        # Hotkey configuration
        # Using sets for multi-key detection
        self.current_keys = set()
        
        # Define hotkeys
        self.HOTKEY_TOGGLE = {keyboard.Key.pause}
        self.HOTKEY_KILL = {keyboard.Key.ctrl_l, keyboard.Key.alt_l, keyboard.Key.esc}

    def start(self):
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()

    def on_press(self, key):
        if key in self.HOTKEY_TOGGLE or key in self.HOTKEY_KILL:
            self.current_keys.add(key)
            
            # Check for Toggle
            if self.HOTKEY_TOGGLE.issubset(self.current_keys):
                if self.on_toggle_record:
                    self.on_toggle_record()
                # Reset keys to avoid repeated triggering
                self.current_keys.clear()
                
            # Check for Kill
            if self.HOTKEY_KILL.issubset(self.current_keys):
                if self.on_kill_app:
                    self.on_kill_app()
                self.current_keys.clear()
        else:
             # If other keys are pressed, we might want to clear or keep tracking.
             # For strict hotkeys, we usually just track modifiers + key.
             # But pynput can be tricky. Let's just add it.
             self.current_keys.add(key)

    def on_release(self, key):
        try:
            self.current_keys.remove(key)
        except KeyError:
            pass

    def inject_text(self, text: str):
        """
        Injects text into the active window.
        Uses pyautogui.write for short text, clipboard swap for long text.
        """
        if not text:
            return

        if len(text) < 50:
            pyautogui.write(text + " ")
        else:
            self._clipboard_paste(text + " ")

    def _clipboard_paste(self, text: str):
        # Backup clipboard
        old_clipboard = pyperclip.paste()
        
        # Copy new text
        pyperclip.copy(text)
        
        # Paste
        # Determine OS for command key
        # Assuming Windows/Linux use Ctrl+V
        pyautogui.hotkey('ctrl', 'v')
        
        # Restore clipboard (with a small delay to ensure paste finishes)
        # This is blocking, so maybe run in thread if responsiveness is key.
        # But for now, a tiny sleep is fine.
        time.sleep(0.1) 
        pyperclip.copy(old_clipboard)
