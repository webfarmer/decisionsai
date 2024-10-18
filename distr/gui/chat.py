from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QIcon, QAction, QMovie, QColor, QPainter, QFontMetrics, QBrush
from PyQt6.QtWidgets import QPushButton, QListWidgetItem, QMenu, QMessageBox, QInputDialog, QLineEdit, QListWidget, QStyledItemDelegate
from PyQt6 import QtWidgets
from distr.core.db import get_session, Chat
from distr.core.constants import ICONS_DIR
import os
from datetime import datetime, timedelta
import json
from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound

class RoundButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border-radius: 20px;
                font-size: 20px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setBrush(QColor("#007bff"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(self.rect())

        painter.setPen(QColor("white"))
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "+")

class ChatListWidget(QListWidget):
    chat_selected = pyqtSignal(int)
    rename_requested = pyqtSignal(QListWidgetItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.parent_window.handle_enter_key()
        elif event.key() == Qt.Key.Key_Delete:
            self.parent_window.handle_delete_key()
        elif event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            super().keyPressEvent(event)
            current_item = self.currentItem()
            if current_item and current_item.flags() & Qt.ItemFlag.ItemIsSelectable:
                self.parent_window.on_chat_item_clicked(current_item)
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if item and item.flags() & Qt.ItemFlag.ItemIsSelectable:
            self.rename_requested.emit(item)
        else:
            super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.parent_window.cancel_renaming()

class ChatItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.renaming_item = None

    def paint(self, painter, option, index):
        if index.row() == self.renaming_item:
            painter.fillRect(option.rect, QColor("#90EE90"))
        super().paint(painter, option, index)

class ChatWindow(QtWidgets.QMainWindow):
    def __init__(self, chat_manager):
        super().__init__()
        self.chat_manager = chat_manager
        self.setWindowTitle("DecisionsAI - Your Chat History")
        self.setGeometry(100, 100, 1000, 600)

        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)

        # Main layout
        self.main_layout = QtWidgets.QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Left side: Chat list
        self.left_widget = QtWidgets.QWidget()
        self.left_widget.setFixedWidth(300)  # Fixed width for the sidebar
        self.left_layout = QtWidgets.QVBoxLayout(self.left_widget)
        self.left_layout.setContentsMargins(10, 10, 10, 10)
        self.left_layout.setSpacing(10)

        # Search widget
        self.search_widget = QtWidgets.QWidget()
        self.search_widget.setFixedHeight(40)  # Fixed height for search box
        self.search_layout = QtWidgets.QHBoxLayout(self.search_widget)
        self.search_layout.setContentsMargins(0, 0, 0, 0)

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Search")
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 5px 35px 5px 15px;
                font-size: 14px;
            }
        """)
        self.search_input.textChanged.connect(self.filter_chats)

        search_icon_path = os.path.join(ICONS_DIR, "search.png")
        search_icon = QIcon(search_icon_path)
        search_action = QAction(search_icon, "", self.search_input)
        search_action.setIconText("")
        self.search_input.addAction(search_action, QtWidgets.QLineEdit.ActionPosition.TrailingPosition)

        self.search_layout.addWidget(self.search_input)
        self.left_layout.addWidget(self.search_widget)

        # Container for chat list and spinner
        self.list_container = QtWidgets.QWidget()
        self.list_container_layout = QtWidgets.QStackedLayout(self.list_container)
        self.list_container_layout.setStackingMode(QtWidgets.QStackedLayout.StackingMode.StackAll)

        # Chat list
        self.chat_list = ChatListWidget(self)
        self.chat_list.parent_window = self
        self.chat_item_delegate = ChatItemDelegate(self.chat_list)
        self.chat_list.setItemDelegate(self.chat_item_delegate)
        self.chat_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
            }
            QListWidget::item {
                height: 40px;
                padding-left: 20px;
                padding-right: 20px;
                border-radius: 5px;
                font-size: 16px;
            }
            QListWidget::item:selected {
                background-color: #e0e0e0;
                color: black;
            }
        """)
        self.chat_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chat_list.customContextMenuRequested.connect(self.show_context_menu)
        self.chat_list.itemClicked.connect(self.on_chat_item_clicked)
        self.chat_list.rename_requested.connect(self.start_renaming)
        self.list_container_layout.addWidget(self.chat_list)

        # Spinner container
        self.spinner_container = QtWidgets.QWidget()
        self.spinner_container_layout = QtWidgets.QVBoxLayout(self.spinner_container)
        self.spinner_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Spinner
        self.spinner = QtWidgets.QLabel()
        spinner_path = os.path.join(ICONS_DIR, "spinner.gif")
        self.spinner_movie = QMovie(spinner_path)
        self.spinner_movie.setScaledSize(QSize(60, 60))
        self.spinner.setMovie(self.spinner_movie)
        self.spinner.setFixedSize(60, 60)
        self.spinner_container_layout.addWidget(self.spinner)

        self.list_container_layout.addWidget(self.spinner_container)
        self.spinner_container.hide()  # Initially hide the spinner

        self.left_layout.addWidget(self.list_container)
        self.main_layout.addWidget(self.left_widget)

        # Right side: Chat thread view
        self.right_widget = QtWidgets.QWidget()
        self.right_layout = QtWidgets.QVBoxLayout(self.right_widget)
        self.chat_thread_view = QtWidgets.QTextEdit()
        self.chat_thread_view.setReadOnly(True)
        self.right_layout.addWidget(self.chat_thread_view)

        # Input area
        self.input_area = QtWidgets.QTextEdit()
        self.input_area.setFixedHeight(100)
        self.right_layout.addWidget(self.input_area)

        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.clicked.connect(self.add_to_chat_thread)
        self.right_layout.addWidget(self.send_button)

        self.main_layout.addWidget(self.right_widget, 2)

        # New Chat button
        self.new_chat_button = RoundButton(self)
        self.new_chat_button.setToolTip("New Chat")
        self.new_chat_button.clicked.connect(self.add_new_chat)
        self.new_chat_button.raise_()

        self.current_chat_id = None
        self.load_chat_list()

        self.position_new_chat_button()

        self.rename_editor = None
        self.is_renaming = False
        self.renaming_item = None

        # Connect signals
        self.chat_manager.chat_created.connect(self.on_chat_created)
        self.chat_manager.chat_updated.connect(self.on_chat_updated)
        self.chat_manager.chat_deleted.connect(self.on_chat_deleted)

    def show_spinner(self):
        self.chat_list.hide()
        self.spinner_container.show()
        self.spinner_movie.start()

    def hide_spinner(self):
        self.spinner_movie.stop()
        self.spinner_container.hide()
        self.chat_list.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_new_chat_button()

    def filter_chats(self):
        self.show_spinner()
        search_text = self.search_input.text().lower()
        QTimer.singleShot(100, lambda: self.load_chat_list(search_text))

    def load_chat_list(self, search_text=""):
        self.chat_list.clear()
        session = get_session()
        query = session.query(Chat).filter(Chat.parent_id.is_(None))
        
        if search_text:
            query = query.filter(or_(Chat.title.ilike(f"%{search_text}%"), 
                                     Chat.input.ilike(f"%{search_text}%")))
        
        chats = query.order_by(Chat.created_date.desc()).all()
        
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        current_date = None
        for chat in chats:
            chat_date = chat.created_date.date()
            
            if chat_date != current_date:
                if chat_date == today:
                    header_text = "Today"
                elif chat_date == yesterday:
                    header_text = "Yesterday"
                elif today - chat_date <= timedelta(days=6):
                    header_text = f"{(today - chat_date).days} days ago"
                else:
                    header_text = chat_date.strftime("%B %d, %Y")
                
                self.add_date_header(header_text)
                current_date = chat_date
            
            self.add_chat_item(chat)
        
        session.close()
        self.hide_spinner()

        # Select the first chat item (latest added) if available
        if self.chat_list.count() > 0:
            first_item = self.chat_list.item(0)
            if first_item and first_item.flags() & Qt.ItemFlag.ItemIsSelectable:
                self.chat_list.setCurrentItem(first_item)
                self.on_chat_item_clicked(first_item)

    def add_date_header(self, header_text):
        header_item = QListWidgetItem(header_text)
        header_item.setFlags(Qt.ItemFlag.NoItemFlags)
        header_item.setForeground(Qt.GlobalColor.gray)
        font = header_item.font()
        font.setBold(True)
        font.setPointSize(9)  # Smaller font size
        header_item.setFont(font)
        self.chat_list.addItem(header_item)

    def add_chat_item(self, chat):
        item = QListWidgetItem(chat.title)
        item.setData(Qt.ItemDataRole.UserRole, chat.id)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsSelectable)
        self.chat_list.addItem(item)  # Add to the bottom of the list

    def show_context_menu(self, position):
        item = self.chat_list.itemAt(position)
        if item is not None:
            chat_id = item.data(Qt.ItemDataRole.UserRole)
            if chat_id is not None:
                menu = QMenu(self)
                rename_action = menu.addAction("Rename Chat")
                archive_action = menu.addAction("Archive Chat")
                copy_action = menu.addAction("Copy Chat")
                remove_action = menu.addAction("Remove Chat")

                action = menu.exec(self.chat_list.mapToGlobal(position))
                if action == rename_action:
                    self.rename_chat(chat_id)
                elif action == archive_action:
                    self.archive_chat(chat_id)
                elif action == copy_action:
                    self.copy_chat(chat_id)
                elif action == remove_action:
                    self.remove_chat(chat_id)

    def rename_chat(self, chat_id):
        session = get_session()
        try:
            chat = session.query(Chat).filter(Chat.id == chat_id).one()
            new_title, ok = QInputDialog.getText(self, "Rename Chat", "Enter new chat title:", text=chat.title)
            if ok and new_title:
                chat.title = new_title
                session.commit()
                self.load_chat_list()
        except NoResultFound:
            QMessageBox.warning(self, "Error", f"Chat with id {chat_id} not found.")
        finally:
            session.close()

    def archive_chat(self, chat_id):
        # Implement archive functionality
        pass

    def copy_chat(self, chat_id):
        # Implement copy functionality
        pass

    def remove_chat(self, chat_id):
        confirm = QMessageBox.question(self, "Confirm Deletion", "Are you sure you want to delete this chat and all its replies?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.chat_manager.delete_chat(chat_id)
            self.load_chat_list(self.search_input.text())
            if self.current_chat_id == chat_id:
                self.chat_thread_view.clear()
                self.current_chat_id = None

    def on_chat_item_clicked(self, item):
        if item and item.flags() & Qt.ItemFlag.ItemIsSelectable:
            chat_id = item.data(Qt.ItemDataRole.UserRole)
            if chat_id:
                self.load_chat_thread(chat_id)

    def load_chat_thread(self, chat_id):
        self.current_chat_id = chat_id
        session = get_session()
        chat = session.query(Chat).get(chat_id)
        self.chat_thread_view.clear()
        if chat:
            self.display_chat(chat)
            if chat.children:
                for child in chat.children:
                    self.display_chat(child, is_child=True)
        else:
            self.chat_thread_view.append("Chat not found.")
        session.close()

    def display_chat(self, chat, is_child=False):
        prefix = "  " if is_child else ""
        self.chat_thread_view.append(f"{prefix}Title: {chat.title}")
        self.chat_thread_view.append(f"{prefix}Input: {chat.input}")
        self.chat_thread_view.append(f"{prefix}Response: {chat.response}")
        self.chat_thread_view.append(f"{prefix}Created: {chat.created_date}")
        self.chat_thread_view.append(f"{prefix}Modified: {chat.modified_date}")
        self.chat_thread_view.append("")

    def add_to_chat_thread(self):
        if not self.current_chat_id:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select a chat thread first.")
            return

        input_text = self.input_area.toPlainText()
        if not input_text:
            return

        session = get_session()
        new_chat = Chat(
            parent_id=self.current_chat_id,
            title=f"Reply to {self.current_chat_id}",
            
            input=input_text,
            response="",  # You might want to generate a response here
            params=json.dumps({}),
            created_date=datetime.utcnow(),
            modified_date=datetime.utcnow()
        )
        session.add(new_chat)
        session.commit()
        session.close()

        self.input_area.clear()
        self.load_chat_thread(self.current_chat_id)

    def add_new_chat(self):
        title, ok = QtWidgets.QInputDialog.getText(self, "New Chat", "Enter chat title:")
        if ok and title:
            new_chat_id = self.chat_manager.create_chat(title)
            self.load_chat_list(self.search_input.text())
            self.select_chat_by_id(new_chat_id)

    def select_chat_by_id(self, chat_id):
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == chat_id:
                self.chat_list.setCurrentItem(item)
                self.on_chat_item_clicked(item)
                break

    def closeEvent(self, event):
        event.accept()

    def handle_enter_key(self):
        if self.is_renaming:
            self.finish_renaming()
        else:
            current_item = self.chat_list.currentItem()
            if current_item and current_item.flags() & Qt.ItemFlag.ItemIsSelectable:
                self.start_renaming(current_item)

    def handle_delete_key(self):
        current_item = self.chat_list.currentItem()
        if current_item and current_item.flags() & Qt.ItemFlag.ItemIsSelectable:
            chat_id = current_item.data(Qt.ItemDataRole.UserRole)
            self.remove_chat(chat_id)

    def start_renaming(self, item=None):
        if not self.is_renaming:
            current_item = item or self.chat_list.currentItem()
            if current_item and current_item.flags() & Qt.ItemFlag.ItemIsSelectable:
                self.is_renaming = True
                self.renaming_item = current_item
                self.chat_item_delegate.renaming_item = self.chat_list.row(current_item)
                self.rename_editor = QLineEdit(self.chat_list)
                self.rename_editor.setText(current_item.text())
                self.rename_editor.selectAll()
                self.rename_editor.setFrame(False)
                self.rename_editor.editingFinished.connect(self.finish_renaming)
                
                rect = self.chat_list.visualItemRect(current_item)
                left_padding = 20
                
                self.rename_editor.setGeometry(
                    rect.x(), 
                    rect.y(),
                    rect.width(),
                    rect.height()
                )
                
                self.rename_editor.setStyleSheet(f"""
                    background-color: #426eb1;
                    color: white;
                    border: none;
                    padding-left: {left_padding}px;
                    padding-right: 5px;
                """)
                
                self.rename_editor.show()
                self.rename_editor.setFocus()

                # Connect the key press event
                self.rename_editor.keyPressEvent = self.rename_editor_key_press
                
                self.chat_list.update()

    def rename_editor_key_press(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.finish_renaming()
        else:
            QLineEdit.keyPressEvent(self.rename_editor, event)

    def cancel_renaming(self):
        if self.is_renaming:
            self.finish_renaming(cancel=True)

    def finish_renaming(self, cancel=False):
        if self.rename_editor and self.renaming_item:
            if not cancel:
                new_title = self.rename_editor.text().strip()
                if new_title:
                    chat_id = self.renaming_item.data(Qt.ItemDataRole.UserRole)
                    self.rename_chat(chat_id, new_title)
                    self.renaming_item.setText(new_title)
                else:
                    QMessageBox.warning(self, "Invalid Title", "Chat title cannot be empty.")
                    self.rename_editor.setFocus()
                    return  # Don't close the rename editor if the title is empty
            
            self.rename_editor.deleteLater()
            self.rename_editor = None
            self.is_renaming = False
            self.chat_item_delegate.renaming_item = None
            self.renaming_item = None
            self.chat_list.setFocus()
            self.chat_list.update()

    def rename_chat(self, chat_id, new_title):
        session = get_session()
        try:
            chat = session.query(Chat).filter(Chat.id == chat_id).one()
            chat.title = new_title
            chat.modified_date = datetime.utcnow()  # Update the modified date
            session.commit()
        except NoResultFound:
            QMessageBox.warning(self, "Error", f"Chat with id {chat_id} not found.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while renaming the chat: {str(e)}")
        finally:
            session.close()

    def position_new_chat_button(self):
        button_size = self.new_chat_button.width()
        self.new_chat_button.move(
            self.width() - button_size - 15,
            15
        )

    def on_chat_created(self, chat_id):
        print(f"New chat created with ID: {chat_id}")
        self.load_chat_list(self.search_input.text())

    def on_chat_updated(self, chat_id):
        print(f"Chat updated with ID: {chat_id}")
        self.load_chat_list(self.search_input.text())

    def on_chat_deleted(self, chat_id):
        print(f"Chat deleted with ID: {chat_id}")
        self.load_chat_list(self.search_input.text())

    def closeEvent(self, event):
        event.ignore()
        self.hide()
