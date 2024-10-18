from PyQt6.QtCore import QObject, pyqtSignal

class SignalManager(QObject):

    # VoiceBox-related signals
    update_voice_box_position = pyqtSignal()

    show_voice_box = pyqtSignal()
    hide_voice_box = pyqtSignal()

    reset_voice_box = pyqtSignal()

    # Sound-related signals
    sound_started = pyqtSignal()
    sound_stopped = pyqtSignal()
    sound_finished = pyqtSignal()

    stop_sound_player = pyqtSignal()

    hide_oracle = pyqtSignal() 
    show_oracle = pyqtSignal()  
    change_oracle = pyqtSignal() 

    #signals for transcription control
    is_transcribing = pyqtSignal(bool)
    is_listening = pyqtSignal(bool)
    is_speaking = pyqtSignal(bool)

    voice_update_last_speech_time = pyqtSignal()
    action_update_last_speech_time = pyqtSignal()

    enable_tray = pyqtSignal()
    disable_tray = pyqtSignal()

    #signals for transcription control
    voice_set_action = pyqtSignal(dict)
    voice_start_transcribing = pyqtSignal()
    voice_stop_transcribing = pyqtSignal()

    voice_set_is_transcribing = pyqtSignal(bool)
    voice_set_is_listening = pyqtSignal(bool)
    voice_set_is_speaking = pyqtSignal(bool)

    voice_stop_speaking = pyqtSignal()
    
    action_set_action = pyqtSignal(dict)

    action_set_is_transcribing = pyqtSignal(bool)
    action_set_is_listening = pyqtSignal(bool)
    action_set_is_speaking = pyqtSignal(bool)

    voice_set_transcription_buffer = pyqtSignal(list)
    action_set_transcription_buffer = pyqtSignal(list)
    

    # New signals for oracle color animations
    set_oracle_red = pyqtSignal()
    set_oracle_yellow = pyqtSignal()
    set_oracle_blue = pyqtSignal()
    set_oracle_green = pyqtSignal()
    set_oracle_white = pyqtSignal()
    reset_oracle_color = pyqtSignal()

    # New signals for chat operations
    chat_created = pyqtSignal(int)  # Emits new chat ID
    chat_updated = pyqtSignal(int)  # Emits updated chat ID
    chat_deleted = pyqtSignal(int)  # Emits deleted chat ID

    exit_app = pyqtSignal()  

    def __init__(self):
        super().__init__()
        self._is_transcribing = False

    def set_is_transcribing(self, value):
        if self._is_transcribing != value:
            self._is_transcribing = value
            self.is_transcribing.emit(value)

    def get_is_transcribing(self):
        return self._is_transcribing

    def disconnect_all(self):
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, pyqtSignal):
                try:
                    attr.disconnect()
                except TypeError:
                    pass  # Signal was not connected

   
signal_manager = SignalManager()