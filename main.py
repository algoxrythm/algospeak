import sys
import signal
import threading
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
    
    # Signal Handler to communicate from Thread to GUI
    signal_handler = SignalHandler()
    
    def on_transcription_segment(text: str):
        print(f"Transcribed: {text}")
        signal_handler.update_text.emit(text)
        input_controller.inject_text(text)

    engine = TranscriptionEngine(on_segment_callback=on_transcription_segment)
    
    def toggle_recording():
        if audio_pipeline.is_recording:
            audio_pipeline.stop()
            signal_handler.update_text.emit("[Paused]")
        else:
            audio_pipeline.start()
            signal_handler.update_text.emit("[Listening...]")

    def kill_app():
        print("Kill switch activated.")
        cleanup()
        sys.exit(0)

    input_controller = InputController(
        on_toggle_record=toggle_recording,
        on_kill_app=kill_app
    )

    # Setup GUI
    def cleanup():
        print("Cleaning up...")
        input_controller.stop()
        audio_pipeline.stop()
        engine.stop()
        
    tray_app = SystemTrayApp(app, on_quit=cleanup)
    
    # Connect signals
    signal_handler.update_text.connect(tray_app.overlay.update_text)

    # Start Threads
    engine.start()
    input_controller.start()
    
    # Start Audio (default to listening? Or wait for toggle?)
    # Let's wait for toggle to avoid immediate recording
    # audio_pipeline.start() 
    tray_app.overlay.update_text("Press Pause|Break to Start")

    # Main Loop
    # We need to periodically pull audio from pipeline and push to engine
    # Since engine pulls from its own queue, we need to bridge them.
    # Or better, let's make a bridge thread.
    
    def audio_bridge():
        while True:
            chunk = audio_pipeline.get_audio_chunk()
            if chunk is not None:
                engine.push_audio(chunk)
            else:
                time.sleep(0.01)
            
            if not engine.running:
                break
    
    import time
    bridge_thread = threading.Thread(target=audio_bridge, daemon=True)
    bridge_thread.start()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
