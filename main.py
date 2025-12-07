import sys
import signal
import threading
import time
from PyQt6.QtWidgets import QApplication
from src.audio import AudioPipeline
from src.engine import TranscriptionEngine
from src.gui import SystemTrayApp, SignalHandler
from src.input import InputController

def main():
    # Handle SIGINT for Ctrl+C in terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Initialize Components
    audio_pipeline = AudioPipeline() 
    
    # Signal Handler for GUI updates
    signal_handler = SignalHandler()
    
    # --- Integration Logic ---
    
    def on_transcription_update(text: str, is_final: bool):
        """
        Callback from Engine.
        """
        # 1. Update GUI (Always, for partials and finals)
        signal_handler.update_text.emit(text, is_final)
        
        # 2. Inject Text (Only if Final and Valid)
        if is_final and text:
            print(f"Injecting: {text}")
            input_controller.inject_text(text)

    def on_feedback_update(feedback_type: str):
        signal_handler.trigger_feedback.emit(feedback_type)

    engine = TranscriptionEngine(
        on_segment_callback=on_transcription_update,
        on_feedback_callback=on_feedback_update
    )
    
    def toggle_recording():
        if audio_pipeline.is_recording:
            audio_pipeline.stop()
            signal_handler.update_text.emit("[PAUSED]", True)
        else:
            audio_pipeline.start()
            # We don't want to emit "True" here as it's not a committed text, just a status update.
            # But our GUI expects text, is_final. 
            # Let's send a special status update or just use the text.
            signal_handler.update_text.emit("[LISTENING...]", False)

    def kill_app():
        print("Kill switch activated.")
        cleanup()
        sys.exit(0)

    input_controller = InputController(
        on_toggle_record=toggle_recording,
        on_kill_app=kill_app
    )

    # Cleanup Routine
    def cleanup():
        print("Shutting down...")
        input_controller.stop()
        audio_pipeline.stop()
        engine.stop()
        
    tray_app = SystemTrayApp(app, on_quit=cleanup)
    
    # Connect signals
    # map signal_handler.update_text -> tray_app.overlay.update_text
    signal_handler.update_text.connect(tray_app.overlay.update_text)
    signal_handler.trigger_feedback.connect(tray_app.overlay.handle_feedback)

    # Start Services
    print("Starting Engine...")
    engine.start() # Model loading happens here
    
    print("Starting Input Controller...")
    input_controller.start()
    
    # Audio Bridge Thread
    # Reads from AudioPipeline -> Pushes to Engine
    def audio_bridge():
        while True:
            chunk = audio_pipeline.get_audio_chunk()
            if chunk is not None:
                # Push to engine
                engine.push_audio(chunk)
            else:
                time.sleep(0.005) # fast poll
            
            if not engine.running:
                break
    
    bridge_thread = threading.Thread(target=audio_bridge, daemon=True)
    bridge_thread.start()

    print("System Ready. Press Pause/Break to start/stop dictation.")
    tray_app.overlay.update_text("SYSTEM READY", True)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
