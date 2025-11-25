import sys
import platform
import ctypes
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                             QWidget, QSystemTrayIcon, QMenu)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QAction, QIcon, QFont, QColor, QPalette

class SignalHandler(QObject):
    update_text = pyqtSignal(str)

class OverlayWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_window_flags()

    def init_ui(self):
        self.setWindowTitle("STT Overlay")
        # Smaller size, positioned towards bottom center or user preference
        # We'll start with a compact bar
        self.setGeometry(100, 100, 500, 80)
        
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Label for text
        self.text_label = QLabel("Ready...")
        self.text_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.text_label.setStyleSheet("color: rgba(255, 255, 255, 230);")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)
        
        layout.addWidget(self.text_label)
        
        # Styling
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Gracefully transparent background
        # Using a darker, more transparent black with rounded corners
        central_widget.setStyleSheet("""
            background-color: rgba(0, 0, 0, 100); 
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 30);
        """)

    def setup_window_flags(self):
        # Always on top, Frameless
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool  # Tool window doesn't show in taskbar usually
        )
        
        # Click-through logic
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
            
            # Get current window style
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
            print(f"Failed to set Windows click-through: {e}")

    def _set_click_through_linux(self, enable: bool):
        # Qt 5.11+ supports Qt.WindowTransparentForInput
        # But it needs to be set in setWindowFlags.
        # Since we already set flags, we need to update them.
        flags = self.windowFlags()
        if enable:
            flags |= Qt.WindowType.WindowTransparentForInput
        else:
            flags &= ~Qt.WindowType.WindowTransparentForInput
        
        self.setWindowFlags(flags)
        self.show() # Re-show is often needed after changing flags

    def update_text(self, text: str):
        self.text_label.setText(text)
        # Auto-clear after a few seconds? Or keep history?
        # For now, just show the latest segment.
        QTimer.singleShot(5000, lambda: self.text_label.setText("") if self.text_label.text() == text else None)

class SystemTrayApp:
    def __init__(self, app: QApplication, on_quit: callable):
        self.app = app
        self.on_quit = on_quit
        
        self.tray_icon = QSystemTrayIcon(QIcon.fromTheme("audio-input-microphone"), self.app)
        # Fallback icon if theme icon not found? 
        # We'll assume standard icons exist or user can provide one.
        
        self.menu = QMenu()
        
        self.action_show = QAction("Show Overlay", self.app)
        self.action_show.triggered.connect(self.show_overlay)
        self.menu.addAction(self.action_show)
        
        self.action_hide = QAction("Hide Overlay", self.app)
        self.action_hide.triggered.connect(self.hide_overlay)
        self.menu.addAction(self.action_hide)
        
        self.menu.addSeparator()
        
        self.action_quit = QAction("Quit", self.app)
        self.action_quit.triggered.connect(self.quit_app)
        self.menu.addAction(self.action_quit)
        
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()
        
        self.overlay = OverlayWindow()
        self.overlay.show()

    def show_overlay(self):
        self.overlay.show()

    def hide_overlay(self):
        self.overlay.hide()

    def quit_app(self):
        self.on_quit()
        self.app.quit()
