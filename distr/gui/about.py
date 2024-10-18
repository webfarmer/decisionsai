from distr.core.constants import IMAGES_DIR
from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import Qt, QUrl
import os


class ClickableLabel(QtWidgets.QLabel):
    def __init__(self, text, url, parent=None):
        super().__init__(text, parent)
        self.url = url
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("color: white; text-decoration: underline;")

    def mousePressEvent(self, event):
        QDesktopServices.openUrl(QUrl(self.url))

class ScrollingCredits(QtWidgets.QScrollArea):
    def __init__(self, credits, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setStyleSheet("background-color: #1a2a3c; border: none;")

        content = QtWidgets.QWidget()
        self.setWidget(content)
        layout = QtWidgets.QVBoxLayout(content)

        for title, url in credits.items():
            label = ClickableLabel(title, url)
            layout.addWidget(label)

        layout.addStretch()

class AboutWindow(QtWidgets.QMainWindow):

    def __init__(self, soundplayer, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setWindowTitle("About Decisions")
        self.setFixedSize(1000, 600)
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #0f1a2c;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
  
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Left side (text content)
        text_widget = QtWidgets.QWidget()
        text_layout = QtWidgets.QVBoxLayout(text_widget)
        text_layout.setContentsMargins(50, 50, 20, 20)
        text_layout.setSpacing(20)

        title_label = QtWidgets.QLabel("DecisionsAI")
        title_label.setStyleSheet("font-size: 48px; font-weight: 700; letter-spacing: -1px;")
        text_layout.addWidget(title_label)

        description = QtWidgets.QLabel(
            "Since the dawn of civilization, humanity has sought to harness the power of the subservient (aka; Slave). "
            "Speak to your computer as you would a South African car-gaurd and let DecisionsAI figure it out."
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 14px; line-height: 1.6; font-weight: 300;")
        text_layout.addWidget(description)

        credits = {
            "Ollama: AI Model Deployment": "https://ollama.ai/",
            "Vosk: Low Latency ASR Toolkit": "https://alphacephei.com/vosk/",
            "Open-AI Whisper": "https://github.com/openai/whisper",
            "coqui-ai/TTS: Text-to-Speech": "https://github.com/coqui-ai/TTS",
            "OpenAI: AI Research and Deployment": "https://openai.com/",
            "PyAutoGUI: GUI Automation": "https://pyautogui.readthedocs.io/",
            "NumPy: Scientific Computing": "https://numpy.org/",
            "Pydantic: Data Validation": "https://pydantic-docs.helpmanual.io/",
            "PyAudio: Audio I/O": "https://people.csail.mit.edu/hubert/pyaudio/",
            "SpeechRecognition: Speech to Text": "https://pypi.org/project/SpeechRecognition/",
            "PyQt6: GUI Framework": "https://www.riverbankcomputing.com/software/pyqt/",
            "Python: Programming Language": "https://www.python.org/"
        }
        credits_scroll = ScrollingCredits(credits)
        text_layout.addWidget(credits_scroll)

        description = QtWidgets.QLabel(
            "Built using a plethora of leading-edge libraries and open-source models, DecisionsAI serves as an intelligent "
            "digital assistant capable of understanding and executing various tasks on your computer. "
            "It's designed to be more than just an information retrieval tool, with capabilities that "
            "include automation, voice interaction, and adaptive learning. DecisionsAI aims to streamline "
            "your workflow and enhance productivity through true, local, intuitive AI-driven assistance."
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 14px; line-height: 1.6; font-weight: 300;")
        text_layout.addWidget(description)

        text_layout.addStretch()

        content_layout.addWidget(text_widget, 2)

        # Right side (image)
        self.image_label = QtWidgets.QLabel()
        avatar_path = os.path.join(IMAGES_DIR, "avatar.jpg")
        pixmap = QtGui.QPixmap(avatar_path)
        image_height = int(self.height() * 0.7)
        scaled_pixmap = pixmap.scaledToHeight(image_height, QtCore.Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        content_layout.addWidget(self.image_label, 1)

        main_layout.addWidget(content_widget)

        # Footer
        footer_widget = QtWidgets.QWidget()
        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(50, 10, 50, 10)

        right_footer = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_footer)
        version_label = QtWidgets.QLabel("Version 0.0.1 (2024)")
        right_layout.addWidget(version_label)
        company_label = ClickableLabel("Built by Crystal Logic (Pty) Ltd", "https://www.crystallogic.co.za")
        right_layout.addWidget(company_label)
        version_label = QtWidgets.QLabel("")
        right_layout.addWidget(version_label)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        footer_layout.addWidget(right_footer)

        footer_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 26, 44, 0.8);
            }
            QLabel, ClickableLabel {
                font-size: 12px;
                color: #cccccc;
                font-weight: 400;
            }
        """)
        main_layout.addWidget(footer_widget)

    # Add this new method
    def closeEvent(self, event):
        event.ignore()
        self.hide()
