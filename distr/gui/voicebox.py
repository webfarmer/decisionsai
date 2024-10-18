from distr.core.constants import IMAGES_DIR, ICONS_DIR
from distr.core.signals import signal_manager
from PyQt6.QtGui import QMovie, QImageReader
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt, QSize, QTimer
import os

class VoiceBoxWindow(QtWidgets.QWidget):

    def __init__(self, sound_player, parent=None):
        super().__init__(parent)
        print("VoiceBoxWindow initialized")  # Debug print
        self.oracle_window = None
        # Update the window flags
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                            Qt.WindowType.WindowStaysOnTopHint | 
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.movie = None
        self.animation_timer = QtCore.QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)

        self.sound_player = sound_player

        self.setup_ui()

        # Connect signals
        signal_manager.update_voice_box_position.connect(self.update_position)

        signal_manager.show_voice_box.connect(self.show_window)
        signal_manager.hide_voice_box.connect(self.hide_window)

        signal_manager.sound_started.connect(self.on_sound_started)
        signal_manager.sound_finished.connect(self.on_sound_finished)
        signal_manager.sound_stopped.connect(self.on_sound_stopped)

        signal_manager.reset_voice_box.connect(self.reset)

    def set_oracle_window(self, oracle_window):
        self.oracle_window = oracle_window

    def setup_ui(self):
        # Set size
        self.setFixedSize(300, 60)

        # Create layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create and set up the voice container
        self.voice_container = QtWidgets.QWidget(self)
        self.voice_container.setObjectName("voiceContainer")
        self.voice_container.setStyleSheet("""
            #voiceContainer {
                background-color: black;
                border: 1px solid black;
                border-radius: 30px;
            }
        """)
        layout.addWidget(self.voice_container)

        # Set up the voice GIF
        self.setup_voice_graphic()
        self.reset()
        self.setup_stop_button()


    def ensure_visibility(self):
        self.show()
        self.windowHandle().setFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)

    def reinforce_always_on_top(self):
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.show()


    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Draw rounded rectangle
        path = QtGui.QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 30, 30)
        painter.setClipPath(path)
        painter.fillPath(path, QtGui.QColor(0, 0, 0))


    def update_position(self):
        oracle_window = self.oracle_window
        if oracle_window and oracle_window.isVisible():
            # Get the screen containing the Oracle window
            screen = QtWidgets.QApplication.screenAt(oracle_window.geometry().center())
            if not screen:
                screen = QtWidgets.QApplication.primaryScreen()
            
            screen_geometry = screen.geometry()
            oracle_rect = oracle_window.geometry()
            oracle_center = oracle_rect.center()

            # Determine if the Oracle window is on the left or right half of its screen
            if oracle_center.x() < screen_geometry.center().x():
                # Oracle is on the left side, place VoiceBox on the right
                voice_box_x = oracle_rect.right() + 20  # 20 pixels gap
            else:
                # Oracle is on the right side, place VoiceBox on the left
                voice_box_x = oracle_rect.left() - self.width() - 20  # 20 pixels gap

            # Vertically center the VoiceBox relative to the Oracle window
            voice_box_y = oracle_rect.top() + (oracle_rect.height() - self.height()) // 2

            # Ensure the VoiceBox stays within the screen bounds
            voice_box_x = max(screen_geometry.left(), min(voice_box_x, screen_geometry.right() - self.width()))
            voice_box_y = max(screen_geometry.top(), min(voice_box_y, screen_geometry.bottom() - self.height()))

            # Calculate the global position
            global_pos = screen_geometry.topLeft() + QtCore.QPoint(voice_box_x - screen_geometry.left(), voice_box_y - screen_geometry.top())
            
            # Move the VoiceBox to the new position
            self.move(global_pos)
            
            # Ensure the VoiceBox is visible and on top
            self.raise_()
            self.activateWindow()

            # If the VoiceBox is still not visible, try to force it onto the screen
            if not self.isVisible():
                self.setGeometry(screen_geometry)


    # def update_with_speech(self, speech):
    #     QTimer.singleShot(0, lambda: self._update_with_speech(speech))

    # def _update_with_speech(self, speech):
    #     # Update the VoiceBox window with the recognized speech
    #     if hasattr(self, 'speech_label'):
    #         self.speech_label.setText(f"Last recognized: {speech}")

    def setup_voice_graphic(self):
        self.voice_label = QtWidgets.QLabel(self.voice_container)
        self.voice_label.setGeometry(0, 0, 300, 60)
        self.voice_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        gif_path = os.path.join(IMAGES_DIR, "voice.gif")        
        reader = QImageReader(gif_path)
        if reader.canRead():
            original_size = reader.size()
            if original_size.isValid() and original_size.height() > 0:
                # Set the height to 150% of the voice box height
                new_height = int(self.voice_label.height() * 2)
                # Calculate the width while maintaining aspect ratio
                new_width = int(new_height * original_size.width() / original_size.height())
                
                self.movie = QMovie(gif_path)
                self.movie.setScaledSize(QSize(new_width, new_height))
                self.voice_label.setMovie(self.movie)
                
                # Center the GIF horizontally and vertically
                x_offset = (self.voice_label.width() - new_width) // 2
                y_offset = ((self.voice_label.height() - new_height) // 2) - 3
                self.voice_label.setGeometry(x_offset, y_offset, new_width, new_height)
                
                self.total_frames = self.movie.frameCount()
            else:
                print(f"Error: Invalid image dimensions: {original_size.width()}x{original_size.height()}")
                self.voice_label.setText("Invalid Image")
        else:
            print(f"Error: Unable to read image from {gif_path}")
            print(f"Error string: {reader.errorString()}")
            self.voice_label.setText("Image Load Error")
        
        self.voice_label.setStyleSheet("color: white; font-size: 14px;")


    def setup_stop_button(self):
        self.stop_button = QtWidgets.QPushButton(self.voice_container)
        self.stop_button.setFixedSize(32, 32)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border-radius: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        icon_path = os.path.join(ICONS_DIR, "stop.png")
        self.stop_button.setIcon(QtGui.QIcon(icon_path))
        self.stop_button.setIconSize(QSize(24, 24))
        
        self.stop_button.clicked.connect(self.on_stop_clicked)
        self.stop_button.move(260, 14)

    def update_animation(self):
        if self.movie.state() == QtGui.QMovie.MovieState.Running:
            self.movie.jumpToNextFrame()
            self.update()
        else:
            self.animation_timer.stop()

    def reset(self):
        self.movie.stop()
        self.animation_timer.stop()
        if self.movie.state() == QMovie.MovieState.Paused:
            self.movie.jumpToFrame(0)
            for _ in range(144):
                self.movie.jumpToNextFrame()
            self.movie.setPaused(True)

    def on_stop_clicked(self):
        print("Stop button clicked")
        self.sound_player.stop_sound()
        signal_manager.sound_stopped.emit()
        self.reset()
        self.hide_window()

    def on_sound_started(self):
        self.movie.start()

    def on_sound_finished(self):
        self.reset()
        self.hide()

    def on_sound_stopped(self):
        print("Sound stopped manually")
        self.hide_window()

    def show_window(self):
        self.update_position()
        self.show()
        self.raise_()
        self.activateWindow()
        print(f"VoiceBoxWindow position: {self.pos()}")  # Debug print
        QtCore.QTimer.singleShot(0, self.update)  # Force an immediate update

    def hide_window(self):
        self.reset()
        self.hide()

    def closeEvent(self, event):
        self.reset()
        event.ignore()
        self.hide()



