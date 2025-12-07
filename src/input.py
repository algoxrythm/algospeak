import threading
import time
import pyautogui
import pyperclip
from pynput import keyboard
from typing import Callable, Optional, Set
import platform

class InputController:
    def __init__(self, 
                 on_toggle_record: Optional[Callable[[], None]] = None,
                 on_kill_app: Optional[Callable[[], None]] = None):
        self.on_toggle_record = on_toggle_record
        self.on_kill_app = on_kill_app
        self.listener = None
        self.current_keys: Set[keyboard.Key] = set()
        
        self.HOTKEY_TOGGLE = {keyboard.Key.pause}
        # Ctrl+Alt+Esc using sets is tricky with pynput's canonicalization
        # We'll use a simplified check
        
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
        try:
            self.current_keys.add(key)
            
            # Toggle (Pause/Break)
            if keyboard.Key.pause in self.current_keys:
                if self.on_toggle_record:
                    self.on_toggle_record()
                self.current_keys.clear()

            # Kill Switch (Ctrl+Alt+Esc) -> Relaxed
            ctrl_pressed = any(k in self.current_keys for k in {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r})
            alt_pressed = any(k in self.current_keys for k in {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r})
            
            if ctrl_pressed and alt_pressed and (keyboard.Key.esc in self.current_keys):
                if self.on_kill_app:
                    self.on_kill_app()
                self.current_keys.clear()
        except AttributeError:
             pass

    def on_release(self, key):
        try:
            if key in self.current_keys:
                self.current_keys.remove(key)
        except KeyError:
            pass

    def inject_text(self, text: str):
        """
        Smart injection that respects what was just typed.
        """
        if not text:
            return

        text = text.strip()
        
        # Check for commands
        lower_text = text.lower()
        if lower_text in ["delete", "backspace"]:
            pyautogui.press("backspace")
            return
        if lower_text in ["enter", "return"]:
            pyautogui.press("enter")
            return
        if lower_text == "clear line":
            # Command to delete whole line?
            pyautogui.hotkey('ctrl', 'backspace') # Simplistic
            return
        
        # Normal Text
        # Add leading space if needed (simplified: always add space unless user handles it)
        # For a smooth experience, we almost always want a space before new dictation 
        # unless it starts with punctuation.
        
        if text and text[0].isalnum():
             text = " " + text
        
        if len(text) < 20:
            # Fast type for short phrases
            # pyautogui.typewrite is slow by default, let's use write
            pyautogui.write(text) 
        else:
            self._clipboard_paste(text)

    def _clipboard_paste(self, text: str):
        # Optimized paste
        # We don't save/restore clipboard to be faster. 
        # Using a "Cyberdeck" usually implies dedicated use, so overwriting clipboard is acceptable for speed.
        # But let's try to be nice.
        
        try:
            pyperclip.copy(text)
            if platform.system() == "Darwin":
                pyautogui.hotkey("command", "v")
            else:
                pyautogui.hotkey("ctrl", "v")
        except Exception as e:
            print(f"Paste failed: {e}")
