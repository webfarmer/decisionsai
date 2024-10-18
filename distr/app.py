from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtCore import QThreadPool, QTimer
from transformers import logging as transformers_logging
from distr.core.voice import ContinuousListener
from distr.core.signals import signal_manager
from distr.core.actions import ActionHandler

from distr.gui.voicebox import VoiceBoxWindow
from distr.gui.oracle import OracleWindow
from distr.gui.about import AboutWindow
from distr.gui.settings import SettingsWindow

from distr.core.constants import TMP_DIR
from distr.core.chat import ChatManager

from distr.core.sound import SoundPlayer
from distr.core.db import get_session

from PyQt6 import QtWidgets
import threading
import warnings
import logging
import AppKit
import hashlib
import torch
import sys
import os

# Suppress specific warnings
logging.getLogger('sentence_transformers').setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message="clean_up_tokenization_spaces")
warnings.filterwarnings("ignore", category=FutureWarning, module="TTS.utils.io")
transformers_logging.set_verbosity_error()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)
logging.getLogger("vosk").setLevel(logging.ERROR)

tts_model_ready = threading.Event()

class TTSManager(QObject):
    tts_completed = pyqtSignal(str)
    tts_error = pyqtSignal(str)

    def __init__(self, sound_player):
        super().__init__()
        self.tts_model = None
        self.sound_player = sound_player  # Use the provided SoundPlayer instance
        self.initialize_tts_model()

    def initialize_tts_model(self):
        from TTS.api import TTS
        print("Initializing TTS model...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tts_model = TTS("tts_models/en/vctk/vits").to(device)
        tts_model_ready.set()  # Signal that the TTS model is ready
        print("TTS model initialized.")

    def start_tts(self, text):
        try:
            output_file = f"{TMP_DIR}/output_{hashlib.md5(text.encode()).hexdigest()}.wav"
            # Specify a default speaker (e.g., "p225")
            self.tts_model.tts_to_file(text=text, file_path=output_file, speaker="p225")
            self.tts_completed.emit(output_file)
            signal_manager.voice_set_is_speaking.emit(True)
            signal_manager.action_set_is_speaking.emit(True)
            self.sound_player.play_sound(output_file)
        except Exception as e:
            print(f"TTS Error: {str(e)}")
            self.tts_error.emit(str(e))

def initialize_tts_manager(sound_player):
    return TTSManager(sound_player)



class Application(QtWidgets.QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.db_session = get_session()
        signal_manager.exit_app.connect(self.quit)        

        AppKit.NSApp.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
        self.sound_player = SoundPlayer()

        self.voice_box = VoiceBoxWindow(self.sound_player)
        self.voice_box.hide() 
        
        self.about_window = AboutWindow(self.sound_player)
        self.about_window.show()
        
        self.settings_window = SettingsWindow(self.sound_player) 

        self.listener = None
        self.ollama_models = None

        self.action_handler = ActionHandler()
        self.chat_manager = ChatManager()

        self.setup_oracle_window()

        # if the settings file's TTS is set to Conque-AI, then initialize the Conque-AI TTS
        self.tts_manager = initialize_tts_manager(self.sound_player)  # Initialize TTSManager with the shared SoundPlayer

        self.chat_manager.set_tts_manager(self.tts_manager)

        QTimer.singleShot(100, self.initialize_app)


    def initialize_app(self):
        thread_pool = QThreadPool.globalInstance()

        self.listener = ContinuousListener(self.action_handler, self.chat_manager)
                        
        thread_pool.waitForDone()

        signal_manager.sound_finished.connect(self.voice_box.on_sound_finished)
        self.listener.start()


    def setup_oracle_window(self):
        self.oracle_window = OracleWindow(self.settings_window, self.about_window, self.voice_box, self.chat_manager)
        self.voice_box.set_oracle_window(self.oracle_window) 
        self.oracle_window.show()
        self.sound_player.play_decisions_sound()

        if self.chat_manager:
            self.chat_manager.chat_created.connect(self.oracle_window.chat_window.on_chat_created)
            self.chat_manager.chat_updated.connect(self.oracle_window.chat_window.on_chat_updated)
            self.chat_manager.chat_deleted.connect(self.oracle_window.chat_window.on_chat_deleted)


    def quit(self):
        logger.info("Quitting application...")
        try:
            signal_manager.stop_sound_player.emit()
            if self.listener:
                self.listener.stop()
            if self.action_handler:
                self.action_handler.stop()

            QThreadPool.globalInstance().waitForDone(5000)
            for window in self.topLevelWindows():
                window.close()
            self.processEvents()
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")
        finally:
            super().quit()



def run():
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    app = Application(sys.argv)
    sys.exit(app.exec())

if __name__ == "__main__":
    run()