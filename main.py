
import sys
import os

# pyrefly: ignore [missing-import]
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog, QSplashScreen
# pyrefly: ignore [missing-import]
from PySide6.QtCore import Qt, QThread, Signal

# pyrefly: ignore [missing-import]
from PySide6.QtGui import QFont, QPixmap

from utils.logger import get_logger
from utils.config import Config
from core.camera import is_model_available, download_model
from core.face_tracker import FaceTrackerWorker
from core.speech_engine import SpeechEngine
from ui.main_window import MainWindow
from ui.theme import set_theme, set_scale

log = get_logger("main")

def main() -> int:
    try:
        import ctypes
        myappid = 'neurogaze.assistive.system.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("Neuro-Gaze")
    app.setApplicationDisplayName("Neuro-Gaze")
    app.setApplicationVersion("2.0")
    
    from PySide6.QtGui import QIcon
    app.setWindowIcon(QIcon("assets/app_icon.ico"))

    # Global font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    from ui.splash import AnimatedSplashScreen
    splash = AnimatedSplashScreen()
    splash.show()

    window_holder = []
    
    class InitWorker(QThread):
        progress_updated = Signal(str, int)
        init_finished = Signal(object, object, object) # config, speech, tracker
        init_failed = Signal(str)

        def run(self):
            import time
            self.progress_updated.emit("Initializing MediaPipe Ocular Pipeline...", 10)
            time.sleep(0.5)
            
            # Load config
            config = Config()
            
            # Download model
            if not is_model_available():
                self.progress_updated.emit("Downloading MediaPipe Face Landmarker model...", 15)
                def on_progress(downloaded: int, total: int) -> None:
                    if total > 0:
                        pct = int(min(downloaded / total * 30, 30))
                    else:
                        pct = 15
                    self.progress_updated.emit("Downloading MediaPipe Face Landmarker model...", 15 + pct)
                
                success = download_model(progress_callback=on_progress)
                if not success:
                    self.init_failed.emit("Failed to download the face tracking model.")
                    return

            self.progress_updated.emit("Establishing Hotspot Link (192.168.4.1)...", 50)
            time.sleep(0.5)
            
            self.progress_updated.emit("Calibrating Real-Time Ear & Landmark Engine...", 70)
            
            # Speech engine
            try:
                speech = SpeechEngine()
                speech.set_rate(config.get("speech_rate", 150))
                speech.set_volume(config.get("speech_volume", 1.0))
                speech.set_voice_by_index(config.get("speech_voice_index", 0))
            except Exception as exc:
                log.error("Speech engine failed: %s", exc)
                speech = SpeechEngine()
                
            self.progress_updated.emit("Calibrating Real-Time Ear & Landmark Engine...", 85)
            
            # Face tracker
            tracker = FaceTrackerWorker(config)
            
            time.sleep(0.5)
            self.progress_updated.emit("System Ready", 100)
            time.sleep(0.2)
            
            self.init_finished.emit(config, speech, tracker)

    worker = InitWorker()
    worker.progress_updated.connect(splash.update_progress)
    
    def on_init_finished(config, speech, tracker):
        set_theme(config.get("theme", "dark"))
        set_scale(config.get("ui_scale", "medium"))
        
        window = MainWindow(config, tracker, speech)
        window_holder.append(window)
        
        def show_main():
            window.show()
            tracker.start()
            splash.close()
            
        splash.fade_out(show_main)

    def on_init_failed(error_msg):
        QMessageBox.critical(None, "Startup Failed", error_msg)
        app.quit()
        
    worker.init_finished.connect(on_init_finished)
    worker.init_failed.connect(on_init_failed)
    
    # Need to keep reference to worker
    window_holder.append(worker)
    worker.start()

    exit_code = app.exec()
    log.info("Application exited with code %d", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())