from distr.gui.utils.get_ollama_models import get_ollama_models
from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import pyqtSignal, Qt, QDir, QModelIndex
from PyQt6.QtWidgets import QMainWindow, QTreeView, QLineEdit, QScrollArea, QWidget, QVBoxLayout
from PyQt6.QtGui import QStandardItemModel, QStandardItem
import json
import os
import logging
from distr.core.constants import MODELS_DIR

SETTINGS_DIR = os.path.join(MODELS_DIR, "settings")
INDEX_FOLDERS_FILE = os.path.join(SETTINGS_DIR, "index_folders.json")

class CheckableDirModel(QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHorizontalHeaderLabels(['Directories'])
        self.itemChanged.connect(self.on_item_changed)
        self.checked_paths = self.load_checked_folders()
        self.populate_root(QDir.homePath())

    def load_checked_folders(self):
        if os.path.exists(INDEX_FOLDERS_FILE):
            try:
                with open(INDEX_FOLDERS_FILE, 'r') as f:
                    return set(json.load(f))
            except json.JSONDecodeError:
                logging.error(f"Error decoding JSON from {INDEX_FOLDERS_FILE}")
            except Exception as e:
                logging.error(f"Error loading checked folders: {str(e)}")
        return set()

    def populate_root(self, path):
        self.clear()
        print(f"Checked paths: {self.checked_paths}")
        root_dir = QDir(path)
        for info in root_dir.entryInfoList(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot):
            if info.isDir():
                item = self.create_item(info)
                self.set_check_state_for_item(item)
                self.appendRow(item)

    def set_check_state_for_item(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path in self.checked_paths:
            item.setCheckState(Qt.CheckState.Checked)
        elif any(checked_path.startswith(path) for checked_path in self.checked_paths):
            item.setCheckState(Qt.CheckState.PartiallyChecked)
        else:
            item.setCheckState(Qt.CheckState.Unchecked)

    def create_item(self, file_info):
        item = QStandardItem(file_info.fileName())
        item.setCheckable(True)
        item.setData(file_info.filePath(), Qt.ItemDataRole.UserRole)
        if QDir(file_info.filePath()).count() > 2:  # If directory is not empty
            placeholder = QStandardItem("Loading...")
            item.appendRow(placeholder)
        return item

    def populate_directory(self, parent_item):
        path = parent_item.data(Qt.ItemDataRole.UserRole)
        parent_item.removeRows(0, parent_item.rowCount())
        directory = QDir(path)
        for info in directory.entryInfoList(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot):
            if info.isDir():
                child_item = self.create_item(info)
                self.set_check_state_for_item(child_item)
                parent_item.appendRow(child_item)
                if parent_item.checkState() == Qt.CheckState.Checked:
                    child_item.setCheckState(Qt.CheckState.Checked)

    def set_checked_paths(self, paths):
        for path in paths:
            item = self.find_item(self.invisibleRootItem(), path)
            if item:
                item.setCheckState(Qt.CheckState.Checked)
                self.check_parents(item.parent())

    def find_item(self, parent_item, path):
        for row in range(parent_item.rowCount()):
            child = parent_item.child(row)
            item_path = child.data(Qt.ItemDataRole.UserRole)
            if item_path == path:
                return child
            elif path.startswith(item_path + os.path.sep):
                if child.hasChildren():
                    result = self.find_item(child, path)
                    if result:
                        return result
                else:
                    self.populate_directory(child)
                    return self.find_item(child, path)
        return None

    def hasChildren(self, parent=QModelIndex()):
        if not parent.isValid():
            return True
        return self.itemFromIndex(parent).rowCount() > 0

    def on_item_changed(self, item):
        # Disconnect to prevent recursive calls
        self.itemChanged.disconnect(self.on_item_changed)
        
        if item.isCheckable():
            check_state = item.checkState()
            self.check_children(item, check_state)
            self.check_parents(item.parent())
            self.update_checked_paths()
        
        # Reconnect after processing
        self.itemChanged.connect(self.on_item_changed)

    def check_children(self, parent, check_state):
        if parent.hasChildren():
            for row in range(parent.rowCount()):
                child = parent.child(row)
                child.setCheckState(check_state)
                self.check_children(child, check_state)

    def check_parents(self, parent):
        if parent is not None:
            checked_count = 0
            partial_count = 0
            total_count = parent.rowCount()
            for row in range(total_count):
                child = parent.child(row)
                if child.checkState() == Qt.CheckState.Checked:
                    checked_count += 1
                elif child.checkState() == Qt.CheckState.PartiallyChecked:
                    partial_count += 1
            
            if checked_count == 0 and partial_count == 0:
                parent.setCheckState(Qt.CheckState.Unchecked)
            elif checked_count == total_count:
                parent.setCheckState(Qt.CheckState.Checked)
            else:
                parent.setCheckState(Qt.CheckState.PartiallyChecked)
            
            self.check_parents(parent.parent())

    def get_checked_paths(self):
        checked_paths = []
        self._get_checked_paths_recursive(self.invisibleRootItem(), checked_paths)
        return checked_paths

    def _get_checked_paths_recursive(self, parent_item, checked_paths):
        for row in range(parent_item.rowCount()):
            child = parent_item.child(row)
            path = child.data(Qt.ItemDataRole.UserRole)
            if path and child.checkState() == Qt.CheckState.Checked:
                checked_paths.append(path)
            elif child.hasChildren():
                self._get_checked_paths_recursive(child, checked_paths)

    def update_checked_paths(self):
        self.checked_paths = set(self.get_checked_paths())

    def flags(self, index):
        default_flags = super().flags(index)
        return default_flags & ~Qt.ItemFlag.ItemIsEditable

class SettingsWindow(QMainWindow):
    settings_changed = pyqtSignal(dict)

    def __init__(self, soundplayer, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setWindowTitle("Settings")
        self.setMinimumSize(800, 775)
        self.resize(800, 775)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QtWidgets.QVBoxLayout(central_widget)

        # Create tabs
        tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(tabs)

        # General Settings Tab
        general_tab = QtWidgets.QWidget()
        general_layout = QtWidgets.QVBoxLayout(general_tab)

        # Startup options
        startup_group = QtWidgets.QGroupBox("Startup Options")
        startup_layout = QtWidgets.QVBoxLayout()
        self.load_splash_sound = QtWidgets.QCheckBox("Load Splash Sound on Startup")
        self.show_about = QtWidgets.QCheckBox("Show About on Startup")
        self.save_listening_state = QtWidgets.QCheckBox("Save Listening State on Startup")
        self.stop_listening = QtWidgets.QCheckBox("Stop Listening on Startup")
        startup_layout.addWidget(self.load_splash_sound)
        startup_layout.addWidget(self.show_about)
        startup_layout.addWidget(self.save_listening_state)
        startup_layout.addWidget(self.stop_listening)
        startup_group.setLayout(startup_layout)
        general_layout.addWidget(startup_group)

        # My Oracle options
        oracle_group = QtWidgets.QGroupBox("My Oracle")
        oracle_layout = QtWidgets.QVBoxLayout()
        self.restore_position = QtWidgets.QCheckBox("Restore Position for Different Screens")
        self.position_combo = QtWidgets.QComboBox()
        self.position_combo.addItems(["Top Left", "Top Right", "Middle Left", "Middle Right", "Bottom Left", "Bottom Right"])
        self.position_combo.setCurrentText("Middle Right")
        self.switch_oracle = QtWidgets.QComboBox()
        self.switch_oracle.addItems(["Oracle 1", "Oracle 2", "Oracle 3"])  # Add actual oracle options
        oracle_layout.addWidget(self.restore_position)
        oracle_layout.addWidget(QtWidgets.QLabel("Position:"))
        oracle_layout.addWidget(self.position_combo)
        oracle_layout.addWidget(QtWidgets.QLabel("Switch Oracle:"))
        oracle_layout.addWidget(self.switch_oracle)

        # Add Sphere Size slider
        sphere_size_layout = QtWidgets.QHBoxLayout()
        sphere_size_layout.addWidget(QtWidgets.QLabel("Sphere Size:"))
        self.sphere_size_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.sphere_size_slider.setRange(3, 20)  # 60 to 400 in steps of 20
        self.sphere_size_slider.setValue(9)  # Default value (180)
        self.sphere_size_slider.setTickInterval(1)
        self.sphere_size_slider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBelow)
        self.sphere_size_slider.setSingleStep(1)  # Ensure single step is 1
        sphere_size_layout.addWidget(self.sphere_size_slider)
        self.sphere_size_label = QtWidgets.QLabel("180px")
        sphere_size_layout.addWidget(self.sphere_size_label)
        oracle_layout.addLayout(sphere_size_layout)

        # Connect slider to update function
        self.sphere_size_slider.valueChanged.connect(self.update_sphere_size_label)

        oracle_group.setLayout(oracle_layout)
        general_layout.addWidget(oracle_group)

        # Language settings
        language_group = QtWidgets.QGroupBox("Language Settings")
        language_layout = QtWidgets.QVBoxLayout()
        self.language_combo = QtWidgets.QComboBox()
        self.language_combo.addItems(["English", "Spanish", "French", "German"])  # Add more languages as needed
        language_layout.addWidget(QtWidgets.QLabel("Set Language:"))
        language_layout.addWidget(self.language_combo)
        language_group.setLayout(language_layout)
        general_layout.addWidget(language_group)

        tabs.addTab(general_tab, "General")

        # Audio Settings Tab
        audio_tab = QtWidgets.QWidget()
        audio_layout = QtWidgets.QVBoxLayout(audio_tab)

        # Output settings
        output_group = QtWidgets.QGroupBox("Output")
        output_layout = QtWidgets.QVBoxLayout()

        play_output_layout = QtWidgets.QHBoxLayout()
        play_output_layout.addWidget(QtWidgets.QLabel("Play speech  through:"))
        self.play_output_combo = QtWidgets.QComboBox()
        self.play_output_combo.addItems(["System Default", "JBL TUNE500BT", "MacBook Pro Speakers"])  # Add actual output devices
        play_output_layout.addWidget(self.play_output_combo)
        output_layout.addLayout(play_output_layout)
        play_translation_layout = QtWidgets.QHBoxLayout()
        play_translation_layout.addWidget(QtWidgets.QLabel("Play translation through:"))
        self.play_translation_combo = QtWidgets.QComboBox()
        self.play_translation_combo.addItems(["System Default", "JBL TUNE500BT", "MacBook Pro Speakers"])  # Add actual output devices
        play_translation_layout.addWidget(self.play_translation_combo)
        output_layout.addLayout(play_translation_layout)

        self.lock_sound_checkbox = QtWidgets.QCheckBox("Lock sound to setting")
        output_layout.addWidget(self.lock_sound_checkbox)

        explanation_label = QtWidgets.QLabel(
            "When your audio devices reconnect (e.g., Bluetooth, USB), we'll automatically restore your previously saved input and output settings."
        )
        explanation_label.setWordWrap(True)
        explanation_label.setStyleSheet("font-style: italic; color: #666;")
        output_layout.addWidget(explanation_label)

        output_group.setLayout(output_layout)
        audio_layout.addWidget(output_group)

        # Output & Input Group
        output_input_group = QtWidgets.QGroupBox("Output & Input")
        output_input_layout = QtWidgets.QVBoxLayout()

        # Tabs for Output and Input
        output_input_tabs = QtWidgets.QTabWidget()
        output_tab = QtWidgets.QWidget()
        input_tab = QtWidgets.QWidget()
        output_input_tabs.addTab(output_tab, "Output")
        output_input_tabs.addTab(input_tab, "Input")

        # Output Tab
        output_layout = QtWidgets.QVBoxLayout(output_tab)
        self.output_device_list = QtWidgets.QTableWidget()
        self.output_device_list.setColumnCount(2)
        self.output_device_list.setHorizontalHeaderLabels(["Name", "Type"])
        self.output_device_list.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.output_device_list.verticalHeader().setVisible(False)
        self.output_device_list.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.populate_output_devices()
        output_layout.addWidget(self.output_device_list)

        # Input Tab
        input_layout = QtWidgets.QVBoxLayout(input_tab)
        self.input_device_list = QtWidgets.QTableWidget()
        self.input_device_list.setColumnCount(2)
        self.input_device_list.setHorizontalHeaderLabels(["Name", "Type"])
        self.input_device_list.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.input_device_list.verticalHeader().setVisible(False)
        self.input_device_list.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.populate_input_devices()
        input_layout.addWidget(self.input_device_list)

        output_input_layout.addWidget(output_input_tabs)
        output_input_group.setLayout(output_input_layout)
        audio_layout.addWidget(output_input_group)

        # Speech Volume
        speech_volume_layout = QtWidgets.QHBoxLayout()
        speech_volume_layout.addWidget(QtWidgets.QLabel("Speech Volume:"))
        self.speech_volume_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.speech_volume_slider.setRange(0, 100)
        self.speech_volume_slider.setValue(50)
        speech_volume_layout.addWidget(self.speech_volume_slider)
        audio_layout.addLayout(speech_volume_layout)

        # Input Level
        input_level_layout = QtWidgets.QHBoxLayout()
        input_level_layout.addWidget(QtWidgets.QLabel("Input Level:"))
        self.input_level_indicator = QtWidgets.QProgressBar()
        self.input_level_indicator.setRange(0, 100)
        self.input_level_indicator.setValue(0)
        input_level_layout.addWidget(self.input_level_indicator)
        audio_layout.addLayout(input_level_layout)

        # Add this method to update the input level (you'll need to call this periodically)
        def update_input_level(self, level):
            self.input_level_indicator.setValue(level)

        tabs.addTab(audio_tab, "Audio Setup")

        # AI Agents Tab
        ai_tab = QtWidgets.QWidget()
        ai_layout = QtWidgets.QVBoxLayout(ai_tab)

        # Providers section
        providers_group = QtWidgets.QGroupBox("Providers")
        providers_layout = QtWidgets.QGridLayout()
        providers_layout.setColumnStretch(1, 1)  # Make the input field column expandable
        providers_layout.setColumnMinimumWidth(0, 120)  # Set minimum width for checkbox column
        providers_layout.setHorizontalSpacing(20)  # Add horizontal spacing between columns
        providers_layout.setVerticalSpacing(10)  # Add vertical spacing between rows

        provider_row_style = """
            QCheckBox {
                font-size: 14px;
            }
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
                min-height: 30px;
            }
            QLineEdit:disabled {
                background-color: #f0f0f0;
                color: #888;
            }
        """

        for row, provider in enumerate(["OpenAI", "Anthropic", "AWS Polly", "Ollama"]):
            checkbox = QtWidgets.QCheckBox(provider)
            checkbox.setStyleSheet(provider_row_style)
            providers_layout.addWidget(checkbox, row, 0)

            attr_name = provider.lower().replace(" ", "_")

            input_field = QtWidgets.QLineEdit()
            input_field.setStyleSheet(provider_row_style)
            if provider == "Ollama":
                input_field.setText("http://localhost:11434/")
                input_field.setPlaceholderText("Ollama URL")
            else:
                input_field.setPlaceholderText("Please Enter API Key")
            input_field.setEnabled(False)  # Disable by default
            providers_layout.addWidget(input_field, row, 1)

            setattr(self, f"{attr_name}_checkbox", checkbox)
            setattr(self, f"{attr_name}_input", input_field)

            checkbox.stateChanged.connect(self.update_provider_inputs)

        providers_group.setLayout(providers_layout)
        ai_layout.addWidget(providers_group)

        # Text to Speech section
        tts_group = QtWidgets.QGroupBox("Text to Speech (TTS) Module")
        tts_layout = QtWidgets.QVBoxLayout()

        tts_provider_layout = QtWidgets.QHBoxLayout()
        self.tts_provider = QtWidgets.QComboBox()
        self.tts_provider.addItem("Coqui-AI")
        self.tts_provider.currentTextChanged.connect(self.update_tts_voices)

        self.tts_voice = QtWidgets.QComboBox()

        # Create a horizontal layout for the voice selection and play button
        voice_layout = QtWidgets.QHBoxLayout()
        voice_layout.addWidget(self.tts_voice)

        # Create the play button
        self.play_voice_button = QtWidgets.QPushButton()
        self.play_voice_button.setFixedSize(30, 30)
        self.play_voice_button.setStyleSheet("""
            QPushButton {
                background-color: black;
                border-radius: 15px;
                border: none;
            }
            QPushButton:hover {
                background-color: #333;
            }
        """)
        play_icon = QtGui.QIcon("path/to/play_icon.png")  # Replace with actual path to a play icon
        self.play_voice_button.setIcon(play_icon)
        self.play_voice_button.setIconSize(QtCore.QSize(20, 20))
        self.play_voice_button.clicked.connect(self.play_selected_voice)
        voice_layout.addWidget(self.play_voice_button)

        tts_provider_layout.addWidget(QtWidgets.QLabel("Provider:"))
        tts_provider_layout.addWidget(self.tts_provider)
        tts_provider_layout.addWidget(QtWidgets.QLabel("Voice:"))
        tts_provider_layout.addLayout(voice_layout)
        tts_layout.addLayout(tts_provider_layout)

        # Playback speed slider
        speed_layout = QtWidgets.QHBoxLayout()
        speed_layout.addWidget(QtWidgets.QLabel("Playback Speed:"))
        
        self.speed_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.speed_slider.setRange(10, 90)  # 0.5 to 4.5 in steps of 0.05
        self.speed_slider.setValue(20)  # Default to 1.0
        self.speed_slider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBelow)
        self.speed_slider.setTickInterval(10)
        self.speed_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                            stop:0 #B1B1B1, stop:1 #c4c4c4);
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, 
                                            stop:0 #FF9E9E, stop:1 #FF4040);
                width: 18px;
                height: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """)
        speed_layout.addWidget(self.speed_slider)
        
        self.speed_label = QtWidgets.QLabel("1.00x")
        self.speed_label.setStyleSheet("font-weight: bold; color: #FF4040;")
        speed_layout.addWidget(self.speed_label)
        
        tts_layout.addLayout(speed_layout)

        self.speed_slider.valueChanged.connect(self.update_speed_label)

        tts_group.setLayout(tts_layout)
        ai_layout.addWidget(tts_group)

        # Agent Model section
        agent_model_group = QtWidgets.QGroupBox("Agent Model")
        agent_model_layout = QtWidgets.QHBoxLayout()

        self.agent_provider = QtWidgets.QComboBox()
        self.agent_provider.addItems(["Ollama", "OpenAI", "Anthropic"])
        self.agent_provider.currentTextChanged.connect(self.update_agent_models)

        self.agent_model = QtWidgets.QComboBox()

        agent_model_layout.addWidget(QtWidgets.QLabel("Provider:"))
        agent_model_layout.addWidget(self.agent_provider)
        agent_model_layout.addWidget(QtWidgets.QLabel("Model:"))
        agent_model_layout.addWidget(self.agent_model)

        agent_model_group.setLayout(agent_model_layout)
        ai_layout.addWidget(agent_model_group)

        # Code/Logic Model section
        code_model_group = QtWidgets.QGroupBox("Code/Logic Model")
        code_model_layout = QtWidgets.QHBoxLayout()

        self.code_provider = QtWidgets.QComboBox()
        self.code_provider.addItems(["Ollama", "OpenAI", "Anthropic"])
        self.code_provider.currentTextChanged.connect(self.update_code_models)

        self.code_model = QtWidgets.QComboBox()

        code_model_layout.addWidget(QtWidgets.QLabel("Provider:"))
        code_model_layout.addWidget(self.code_provider)
        code_model_layout.addWidget(QtWidgets.QLabel("Model:"))
        code_model_layout.addWidget(self.code_model)

        code_model_group.setLayout(code_model_layout)
        ai_layout.addWidget(code_model_group)

        tabs.addTab(ai_tab, "AI Agents")

        # Advanced Tab
        advanced_tab = QScrollArea()
        advanced_tab.setWidgetResizable(True)
        advanced_tab.setFrameShape(QScrollArea.Shape.NoFrame)
        
        advanced_content = QWidget()
        advanced_layout = QVBoxLayout(advanced_content)
        advanced_layout.setSpacing(10)

        tab_header = QtWidgets.QLabel("Advanced Settings")
        tab_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tab_header.setStyleSheet("font-size: 18pt; font-weight: bold; margin-bottom: 10px;")
        advanced_layout.addWidget(tab_header)

        safety_message = QtWidgets.QLabel("AI Safety, Data Handling, and Intention")
        safety_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        safety_message.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        advanced_layout.addWidget(safety_message)

        safety_content = QtWidgets.QLabel(
            "This software is provided as-is, without warranties or guarantees. "
            "You use this application at your own risk. We do not collect, store, "
            "or process any personal data. All data is stored locally on your device. "
            "The AI models and features are for personal use and experimentation. "
            "We make no claims about the ownership, accuracy, reliability, or safety of the AI's outputs, "
            "as the AI models belong to 3rd party vendors. You are responsible for reviewing and "
            "verifying any information or suggestions provided. "
            "You can modify or delete any local data through the application settings at any time."
        )
        safety_content.setWordWrap(True)
        safety_content.setStyleSheet("font-size: 12pt; margin-bottom: 20px;")
        safety_content.setAlignment(Qt.AlignmentFlag.AlignJustify)
        advanced_layout.addWidget(safety_content)

        connect_header = QtWidgets.QLabel("Connect Your Accounts")
        connect_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        connect_header.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 5px;")
        advanced_layout.addWidget(connect_header)

        connect_explanation = QtWidgets.QLabel(
            "By connecting your social media accounts, you allow the AI to analyze your data "
            "and build a more accurate profile. This helps in providing personalized responses "
            "and recommendations. The AI will scrape publicly available data from your connected "
            "accounts to enhance its understanding of your preferences and behavior. "
            "Please note that this data will be stored locally on your device."
        )
        connect_explanation.setWordWrap(True)
        connect_explanation.setStyleSheet("font-size: 12pt; margin-bottom: 15px;")
        connect_explanation.setAlignment(Qt.AlignmentFlag.AlignJustify)
        advanced_layout.addWidget(connect_explanation)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(10)

        self.facebook_button = self.create_styled_button("Facebook", "#1877F2")
        self.instagram_button = self.create_styled_button("Instagram", "#E1306C")
        self.google_button = self.create_styled_button("Google", "#4285F4")
        self.linkedin_button = self.create_styled_button("LinkedIn", "#0A66C2")

        button_layout.addWidget(self.facebook_button)
        button_layout.addWidget(self.instagram_button)
        button_layout.addWidget(self.google_button)
        button_layout.addWidget(self.linkedin_button)

        advanced_layout.addLayout(button_layout)

        # Directory tree view
        dir_tree_label = QtWidgets.QLabel("Contextualize Data in Directories")
        dir_tree_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dir_tree_label.setStyleSheet("font-size: 14pt; font-weight: bold; margin-top: 20px; margin-bottom: 10px;")
        advanced_layout.addWidget(dir_tree_label)

        self.dir_tree = QTreeView()
        self.dir_model = CheckableDirModel()
        self.dir_tree.setModel(self.dir_model)
        self.dir_tree.setHeaderHidden(True)
        self.dir_tree.setStyleSheet("""
            QTreeView {
                background-color: white;
                border: 1px solid #d0d0d0;
            }
            QTreeView::item {
                padding: 5px;
            }
        """)
        self.dir_tree.expanded.connect(self.on_item_expanded)
        self.dir_tree.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        advanced_layout.addWidget(self.dir_tree, 1)  # Add stretch factor

        # Exclude file types and Reindex Models button
        exclude_layout = QtWidgets.QHBoxLayout()
        exclude_layout.setContentsMargins(0, 20, 0, 0)  # Add top margin for spacing
        
        exclude_label = QtWidgets.QLabel("Exclude file types:")
        exclude_label.setStyleSheet("font-size: 12pt;")
        exclude_layout.addWidget(exclude_label)

        self.exclude_types = QLineEdit()
        self.exclude_types.setPlaceholderText("e.g., .jpg, .pdf, .doc")
        self.exclude_types.setFixedWidth(350)
        exclude_layout.addWidget(self.exclude_types)
        
        exclude_layout.addStretch()
        
        self.reindex_button = QtWidgets.QPushButton("Reindex Models")
        self.reindex_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 12pt;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        exclude_layout.addWidget(self.reindex_button)
        
        advanced_layout.addLayout(exclude_layout)

        advanced_layout.addStretch(0)  # Add stretchable space at the bottom
        advanced_tab.setWidget(advanced_content)
        tabs.addTab(advanced_tab, "Advanced")

        # Add Save and Cancel buttons
        button_layout = QtWidgets.QHBoxLayout()
        save_button = QtWidgets.QPushButton("Save")
        cancel_button = QtWidgets.QPushButton("Cancel")
        save_button.setFixedWidth(150)  # Set fixed width for both buttons
        cancel_button.setFixedWidth(150)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)

        # Connect buttons
        save_button.clicked.connect(self.save_settings)
        cancel_button.clicked.connect(self.cancel_settings)

        self.load_checked_folders()

        # Call this method at the end of __init__ to set up initial state
        self.update_provider_inputs()
        self.update_tts_voices()
        self.update_agent_models()
        self.update_code_models()

        self.populate_output_devices()
        self.populate_input_devices()

    def load_checked_folders(self):
        if os.path.exists(INDEX_FOLDERS_FILE):
            try:
                with open(INDEX_FOLDERS_FILE, 'r') as f:
                    checked_folders = json.load(f)
                logging.info(f"Loaded checked folders: {checked_folders}")
                self.dir_model.set_checked_paths(checked_folders)
            except json.JSONDecodeError:
                logging.error(f"Error decoding JSON from {INDEX_FOLDERS_FILE}")
            except Exception as e:
                logging.error(f"Error loading checked folders: {str(e)}")

    def save_settings(self):
        settings = {
            'load_splash_sound': self.load_splash_sound.isChecked(),
            'show_about': self.show_about.isChecked(),
            'save_listening_state': self.save_listening_state.isChecked(),
            'stop_listening': self.stop_listening.isChecked(),
            'restore_position': self.restore_position.isChecked(),
            'oracle_position': self.position_combo.currentText(),
            'switch_oracle': self.switch_oracle.currentText(),
            'language': self.language_combo.currentText(),
            'vosk_sensitivity': self.vosk_sensitivity.value(),
            'playback_speed': self.playback_speed.value(),
            'input_device': self.input_device.currentText(),
            'output_device': self.output_device.currentText(),
            'diff_lock_audio': self.diff_lock_audio.isChecked(),
            'tts_voice': self.tts_voice.currentText(),
            'openai_key': self.openai_key.text(),
            'anthropic_key': self.anthropic_key.text(),
            'agent_provider': self.agent_provider.currentText(),
            'agent_model': self.agent_model.currentText(),
            'code_provider': self.code_provider.currentText(),
            'code_model': self.code_model.currentText(),
            'sphere_size': self.sphere_size_slider.value() * 20,
        }
        
        # Add Ollama model selection if available
        if self.ollama_model_selector:
            settings['ollama_model'] = self.ollama_model_selector.currentText()
        
        checked_folders = self.dir_model.get_checked_paths()
        os.makedirs(SETTINGS_DIR, exist_ok=True)
        try:
            with open(INDEX_FOLDERS_FILE, 'w') as f:
                json.dump(checked_folders, f, indent=2)
            logging.info(f"Saved checked folders to {INDEX_FOLDERS_FILE}")
            logging.info(f"Contents: {json.dumps(checked_folders, indent=2)}")
        except Exception as e:
            logging.error(f"Error saving checked folders: {str(e)}")

        self.settings_changed.emit(settings)
        self.hide()

    def cancel_settings(self):
        print("Settings cancelled")
        self.hide()  # Hide the window instead of closing it

    def closeEvent(self, event):
        # Override the close event to hide the window instead of destroying it
        event.ignore()
        self.hide()

    def showEvent(self, event):
        # Center the window on the screen
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        super().showEvent(event)

    def apply_settings(self):
        # Gather the new settings
        new_settings = {}
        # ... populate new_settings ...
        self.settings_changed.emit(new_settings)
        self.close()

    def create_styled_button(self, text, color):
        button = QtWidgets.QPushButton(text)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 12pt;
                font-weight: bold;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {self.darken_color(color)};
            }}
        """)
        return button

    def darken_color(self, color):
        # Define the darkening factor
        factor = 0.8
        
        # Convert hex to RGB
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        
        # Darken by 20%
        r = max(0, int(r * factor))
        g = max(0, int(g * factor))
        b = max(0, int(b * factor))
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"

    def on_item_expanded(self, index):
        item = self.dir_model.itemFromIndex(index)
        if item.rowCount() == 1 and item.child(0).text() == "Loading...":
            self.dir_model.populate_directory(item)

    def log_tree_contents(self):
        def log_item(item, depth=0):
            logging.debug(f"{'  ' * depth}{item.text()}")
            for row in range(item.rowCount()):
                log_item(item.child(row), depth + 1)

        root_item = self.dir_model.invisibleRootItem()
        logging.debug("Tree contents:")
        for row in range(root_item.rowCount()):
            log_item(root_item.child(row))

    def update_provider_inputs(self):
        for provider in ["openai", "anthropic", "aws_polly", "ollama"]:
            checkbox = getattr(self, f"{provider}_checkbox")
            input_field = getattr(self, f"{provider}_input")
            input_field.setEnabled(checkbox.isChecked())

        # Update TTS provider options
        current_text = self.tts_provider.currentText()
        self.tts_provider.clear()
        self.tts_provider.addItem("Coqui-AI")
        if self.openai_checkbox.isChecked():
            self.tts_provider.addItem("OpenAI")
        if self.aws_polly_checkbox.isChecked():
            self.tts_provider.addItem("AWS Polly")
        
        # Try to set the previous selection, or default to Coqui-AI
        index = self.tts_provider.findText(current_text)
        if index >= 0:
            self.tts_provider.setCurrentIndex(index)
        else:
            self.tts_provider.setCurrentIndex(0)

    def update_tts_voices(self):
        provider = self.tts_provider.currentText()
        self.tts_voice.clear()
        
        if provider == "Coqui-AI":
            voices = [{"id":"123", "name":"max"}, {"id":"345", "name":"jax"}, {"id":"678", "name":"sam"}]
        elif provider == "OpenAI":
            voices = [{"id":"o1", "name":"Alice"}, {"id":"o2", "name":"Bob"}, 
                      {"id":"o3", "name":"Charlie"}, {"id":"o4", "name":"Diana"}]
        elif provider == "AWS Polly":
            voices = [{"id":"p1", "name":"Joanna"}, {"id":"p2", "name":"Matthew"}, 
                      {"id":"p3", "name":"Ivy"}, {"id":"p4", "name":"Justin"}]
        else:
            voices = []
        
        for voice in voices:
            self.tts_voice.addItem(voice["name"], voice["id"])

    def update_agent_models(self):
        provider = self.agent_provider.currentText()
        self.agent_model.clear()
        
        if provider == "Ollama":
            models = [{"id":"ollama1", "name":"Llama 2"}, {"id":"ollama2", "name":"Mistral"}]
        elif provider == "OpenAI":
            models = [{"id":"gpt3", "name":"GPT-3.5"}, {"id":"gpt4", "name":"GPT-4"}]
        elif provider == "Anthropic":
            models = [{"id":"claude1", "name":"Claude 1"}, {"id":"claude2", "name":"Claude 2"}]
        else:
            models = []
        
        for model in models:
            self.agent_model.addItem(model["name"], model["id"])

    def update_code_models(self):
        provider = self.code_provider.currentText()
        self.code_model.clear()
        
        if provider == "Ollama":
            models = [{"id":"ollama_code1", "name":"CodeLlama"}, {"id":"ollama_code2", "name":"Starcoder"}]
        elif provider == "OpenAI":
            models = [{"id":"codex", "name":"Codex"}, {"id":"gpt4_code", "name":"GPT-4 for Code"}]
        elif provider == "Anthropic":
            models = [{"id":"claude_code1", "name":"Claude for Code"}, {"id":"claude_code2", "name":"Claude 2 for Code"}]
        else:
            models = []
        
        for model in models:
            self.code_model.addItem(model["name"], model["id"])

    def populate_output_devices(self):
        devices = [
            ("System Default", "Default"),
            ("MacBook Pro Speakers", "Built-in"),
            ("JBL TUNE500BT", "Bluetooth")
        ]  # Replace with actual device detection
        self.output_device_list.setRowCount(len(devices))
        for row, (name, type) in enumerate(devices):
            self.output_device_list.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
            self.output_device_list.setItem(row, 1, QtWidgets.QTableWidgetItem(type))

    def populate_input_devices(self):
        devices = [
            ("System Default", "Default"),
            ("MacBook Pro Microphone", "Built-in"),
            ("JBL TUNE500BT", "Bluetooth")
        ]  # Replace with actual device detection
        self.input_device_list.setRowCount(len(devices))
        for row, (name, type) in enumerate(devices):
            self.input_device_list.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
            self.input_device_list.setItem(row, 1, QtWidgets.QTableWidgetItem(type))

    # Add this method to the SettingsWindow class
    def update_speed_label(self, value):
        speed = 0.5 + (value - 10) * 0.05
        self.speed_label.setText(f"{speed:.2f}x")

    def play_selected_voice(self):
        selected_voice = self.tts_voice.currentText()
        # Implement the logic to play a sample of the selected voice
        print(f"Playing sample of voice: {selected_voice}")
        # You would typically call a TTS function here to generate and play a sample

    # Add this method to the SettingsWindow class
    def update_sphere_size_label(self, value):
        pixel_size = value * 20
        self.sphere_size_label.setText(f"{pixel_size}px")

# At the start of your main script
logging.basicConfig(level=logging.DEBUG)