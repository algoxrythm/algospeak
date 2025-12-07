import sys
import platform
import ctypes
import random
import numpy as np
import sounddevice as sd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                             QWidget, QSystemTrayIcon, QMenu, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QAction, QIcon, QFont, QColor, QPalette, QLinearGradient, QBrush, QPainter

class SignalHandler(QObject):
    update_text = pyqtSignal(str, bool) # text, is_final
    trigger_feedback = pyqtSignal(str)  # "SUCCESS", "ERROR", "DELETE"

class SoundSynthesizer:
    @staticmethod
    def generate_tone(freq_start, freq_end, duration, volume=0.5):
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Frequency slide
        freqs = np.linspace(freq_start, freq_end, len(t))
        
        # Generate sine wave
        audio = np.sin(2 * np.pi * freqs * t) * volume
        
        # Apply envelope (fade in/out) to avoid clicks
        envelope = np.ones_like(audio)
        fade_len = int(sample_rate * 0.01) # 10ms
        envelope[:fade_len] = np.linspace(0, 1, fade_len)
        envelope[-fade_len:] = np.linspace(1, 0, fade_len)
        
        return (audio * envelope).astype(np.float32)

    @staticmethod
    def play(sound_type):
        try:
            if sound_type == "SUCCESS":
                # High pitch chirp: 880Hz -> 1760Hz, 100ms
                wave = SoundSynthesizer.generate_tone(880, 1760, 0.1, 0.3)
                sd.play(wave, 44100, blocking=False)
            
            elif sound_type == "DELETE":
                # Low decay: 400Hz -> 100Hz, 150ms
                wave = SoundSynthesizer.generate_tone(400, 100, 0.15, 0.4)
                sd.play(wave, 44100, blocking=False)
                
            elif sound_type == "ERROR":
                # Buzzer: 150Hz tone
                wave = SoundSynthesizer.generate_tone(150, 140, 0.2, 0.4)
                sd.play(wave, 44100, blocking=False)
                
        except Exception as e:
            print(f"Sound Error: {e}")

class AudioVisualizer(QWidget):
    """
    A simple 'Sound Wave' visualizer simulation.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.is_active = False
        self.bars = 20
        self.values = [0.0] * self.bars

    def start_anim(self):
        self.is_active = True
        self.timer.start(50)

    def stop_anim(self):
        self.is_active = False
        self.timer.stop()
        self.values = [0.0] * self.bars
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        bar_width = width / self.bars
        
        # Cyberpunk gradient
        gradient = QLinearGradient(0, 0, width, 0)
        gradient.setColorAt(0, QColor(0, 255, 255, 200))   # Cyan
        gradient.setColorAt(1, QColor(255, 0, 255, 200))   # Magenta
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        
        for i in range(self.bars):
            if self.is_active:
                target = random.random() * height
                self.values[i] = self.values[i] * 0.5 + target * 0.5
            else:
                self.values[i] = max(0, self.values[i] - 2)

            h = self.values[i]
            y = (height - h) / 2
            x = i * bar_width
            painter.drawRoundedRect(int(x + 2), int(y), int(bar_width - 4), int(h), 2, 2)


class OverlayWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.default_border = "rgba(0, 255, 255, 50)"
        self.border_color = self.default_border
        
        self.init_ui()
        self.setup_window_flags()
        
        # Auto-Hide
        self.idle_timer = QTimer(self)
        self.idle_timer.setInterval(5000) # 5 seconds
        self.idle_timer.timeout.connect(self.fade_out)
        self.idle_timer.start()
        
        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(500)
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def init_ui(self):
        self.setWindowTitle("Algospeak Cyberdeck")
        self.setGeometry(100, 800, 600, 150) # Bottom left-ish
        
        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(20, 10, 20, 10)
        
        # 1. Status / Header
        self.status_label = QLabel("SYSTEM READY")
        self.status_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #00FFFF; letter-spacing: 2px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # 2. Transcription Text
        self.text_label = QLabel("")
        self.text_label.setFont(QFont("Consolas", 14)) # Monospaced font
        self.text_label.setStyleSheet("color: rgba(255, 255, 255, 240);")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.text_label.setWordWrap(True)
        
        # 3. Visualizer
        self.visualizer = AudioVisualizer()
        
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.text_label)
        self.layout.addWidget(self.visualizer)
        
        # Styling
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.update_style()
        
        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 255, 255, 80))
        shadow.setOffset(0, 0)
        self.central_widget.setGraphicsEffect(shadow)

    def update_style(self):
        self.central_widget.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(10, 10, 15, 200); 
                border-radius: 10px;
                border: 2px solid {self.border_color};
            }}
        """)

    def flash_border(self, color_code):
        self.border_color = color_code
        self.update_style()
        QTimer.singleShot(300, self.reset_border)
        
    def reset_border(self):
        self.border_color = self.default_border
        self.update_style()

    def wake_up(self):
        self.idle_timer.stop()
        self.idle_timer.start() # Reset timer
        if self.windowOpacity() < 1.0:
            self.opacity_anim.stop()
            self.opacity_anim.setEndValue(1.0)
            self.opacity_anim.start()

    def fade_out(self):
        self.opacity_anim.stop()
        self.opacity_anim.setEndValue(0.1) # Ghost mode
        self.opacity_anim.start()

    def setup_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.set_click_through(True)

    def set_click_through(self, enable: bool):
        if platform.system() == "Windows":
            self._set_click_through_windows(enable)
        elif platform.system() == "Linux":
            self._set_click_through_linux(enable)

    def _set_click_through_windows(self, enable: bool):
        try:
            hwnd = self.winId().__int__()
            user32 = ctypes.windll.user32
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x80000
            WS_EX_TRANSPARENT = 0x20
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if enable:
                style = style | WS_EX_LAYERED | WS_EX_TRANSPARENT
            else:
                style = style & ~WS_EX_TRANSPARENT
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception as e:
            print(f"Windows click-through error: {e}")

    def _set_click_through_linux(self, enable: bool):
        flags = self.windowFlags()
        if enable:
            flags |= Qt.WindowType.WindowTransparentForInput
        else:
            flags &= ~Qt.WindowType.WindowTransparentForInput
        self.setWindowFlags(flags)
        self.show()

    def handle_feedback(self, feedback_type):
        self.wake_up()
        SoundSynthesizer.play(feedback_type)
        
        if feedback_type == "SUCCESS":
            self.flash_border("#00FF00") # Green
        elif feedback_type in ["DELETE", "ERROR"]:
            self.flash_border("#FF0000") # Red

    def update_text(self, text: str, is_final: bool):
        self.wake_up()
        
        if not text:
            # If empty update (clear), ensure we show ready state
            if is_final:
                 self.status_label.setText("READY")
                 self.text_label.setText("")
                 self.visualizer.stop_anim()
            return
            
        self.text_label.setText(text)
        
        if is_final:
            self.text_label.setStyleSheet("color: #00FF00;") 
            self.status_label.setText("COMMITTED")
            self.status_label.setStyleSheet("color: #00FF00;")
            self.visualizer.stop_anim()
        else:
            self.text_label.setStyleSheet("color: rgba(255, 255, 255, 200); font-style: italic;")
            self.status_label.setText("LISTENING...")
            self.status_label.setStyleSheet("color: #00FFFF;")
            self.visualizer.start_anim()

class SystemTrayApp:
    def __init__(self, app: QApplication, on_quit: callable):
        self.app = app
        self.on_quit = on_quit
        
        self.tray_icon = QSystemTrayIcon(QIcon.fromTheme("audio-input-microphone"), self.app)
        self.menu = QMenu()
        
        action_show = QAction("Show Cyberdeck", self.app)
        action_show.triggered.connect(self.show_overlay)
        self.menu.addAction(action_show)
        
        action_hide = QAction("Hide Cyberdeck", self.app)
        action_hide.triggered.connect(self.hide_overlay)
        self.menu.addAction(action_hide)
        
        self.menu.addSeparator()
        
        action_quit = QAction("Terminate", self.app)
        action_quit.triggered.connect(self.quit_app)
        self.menu.addAction(action_quit)
        
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()
        
        self.overlay = OverlayWindow()
        self.overlay.show()

    def show_overlay(self):
        self.overlay.show()
        self.overlay.wake_up()

    def hide_overlay(self):
        self.overlay.hide()

    def quit_app(self):
        self.on_quit()
        self.app.quit()
