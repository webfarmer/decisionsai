from PyQt6 import QtWidgets, QtGui, QtCore
from distr.core.signals import signal_manager  
from distr.core.constants import ICONS_DIR, IMAGES_DIR
from PyQt6.QtCore import QTimer, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup, QParallelAnimationGroup
from distr.gui.chat import ChatWindow 
import os
from PyQt6.QtWidgets import QApplication

class RoundContainer(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(self.rect())

    def resizeEvent(self, event):
        path = QtGui.QPainterPath()
        path.addEllipse(0, 0, self.width(), self.height())
        mask = QtGui.QRegion(path.toFillPolygon().toPolygon())
        self.setMask(mask)

class OracleWindow(QtWidgets.QMainWindow):

    def __init__(self, settings_window, about_window, voice_box, chat_manager, parent=None):
        super().__init__(parent)
        self.voice_box = voice_box
        self.chat_manager = chat_manager
        self.settings_window = settings_window
        self.about_window = about_window
        # Connect the OracleWindow's move event to trigger VoiceBox position update
        self.moveEvent = self.on_move_event


        signal_manager.change_oracle.connect(self.next_image)
        signal_manager.show_oracle.connect(self.show_globe)
        signal_manager.hide_oracle.connect(self.hide_globe)

        signal_manager.enable_tray.connect(self.enable_tray)
        signal_manager.disable_tray.connect(self.disable_tray)
        
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self._shadow_color = QtGui.QColor(0, 0, 0, 100)  # Initial shadow color
        self._border_color = QtGui.QColor(0, 0, 0)  # Initial black color
        self._inner_shadow_color = QtGui.QColor(0, 0, 0, 100)  # Initial inner shadow color
        self.fill_color = QtGui.QColor(255, 255, 255, 200)  # White with some transparency

        self.animation_group = QParallelAnimationGroup(self)
        self.border_animation_group = QSequentialAnimationGroup(self)
        self.inner_shadow_animation_group = QSequentialAnimationGroup(self)

        self.border_forward_animation = QPropertyAnimation(self, b"border_color")
        self.border_backward_animation = QPropertyAnimation(self, b"border_color")
        self.inner_shadow_forward_animation = QPropertyAnimation(self, b"inner_shadow_color")
        self.inner_shadow_backward_animation = QPropertyAnimation(self, b"inner_shadow_color")
        self.shadow_forward_animation = QPropertyAnimation(self, b"shadow_color")
        self.shadow_backward_animation = QPropertyAnimation(self, b"shadow_color")

        for anim in [self.border_forward_animation, self.border_backward_animation,
                     self.inner_shadow_forward_animation, self.inner_shadow_backward_animation,
                     self.shadow_forward_animation, self.shadow_backward_animation]:
            anim.setDuration(1000)  # 1 second duration
            anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.border_animation_group.addAnimation(self.border_forward_animation)
        self.border_animation_group.addAnimation(self.border_backward_animation)
        self.inner_shadow_animation_group.addAnimation(self.inner_shadow_forward_animation)
        self.inner_shadow_animation_group.addAnimation(self.inner_shadow_backward_animation)

        self.shadow_animation_group = QSequentialAnimationGroup(self)
        self.shadow_animation_group.addAnimation(self.shadow_forward_animation)
        self.shadow_animation_group.addAnimation(self.shadow_backward_animation)

        self.animation_group.addAnimation(self.border_animation_group)
        self.animation_group.addAnimation(self.inner_shadow_animation_group)
        self.animation_group.addAnimation(self.shadow_animation_group)
        self.animation_group.setLoopCount(-1)  # Infinite loop


        self.content_size = 180
        self.shadow_size = 4
        self.stroke_width = 6

        self.total_size = self.content_size + 2 * (self.shadow_size + self.stroke_width)

        screen = QtWidgets.QApplication.primaryScreen().geometry()
        x_position = screen.width() - self.total_size - 40
        y_position = (screen.height() - self.total_size) // 2

        self.setGeometry(x_position, y_position, self.total_size, self.total_size)

        self.dragging = False
        self.offset = QtCore.QPoint()

        self.round_container = RoundContainer(self)
        self.round_container.setGeometry(self.shadow_size + self.stroke_width, 
                                         self.shadow_size + self.stroke_width, 
                                         self.content_size, 
                                         self.content_size)

        self.gif_label = QtWidgets.QLabel(self.round_container)
        self.gif_label.setGeometry(0, 0, self.content_size, self.content_size)
        self.gif_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.gif_label.setScaledContents(True)

        self.current_image_index = 0
        self.forward = True
        self.load_globe_image()

        self.context_menu = self.create_menu()
        
        # Create system tray icon
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        self.create_tray_icon()

        # Connect new signals
        signal_manager.set_oracle_red.connect(self.set_red_animation)
        signal_manager.set_oracle_yellow.connect(self.set_yellow_animation)
        signal_manager.set_oracle_blue.connect(self.set_blue_animation)
        signal_manager.set_oracle_green.connect(self.set_green_animation)
        signal_manager.set_oracle_white.connect(self.set_white_animation)
        signal_manager.reset_oracle_color.connect(self.reset_color_animation)

        # Enable drag and drop
        self.setAcceptDrops(True)

        self.globe_visible = True
        self.chat_window = ChatWindow(self.chat_manager)  # Make sure this is initialized


    def set_voice_box(self, voice_box):
        self.voice_box = voice_box
        

    def enable_tray(self):
        icon_path = os.path.join(ICONS_DIR, "tray.png")
        icon = QtGui.QIcon(icon_path)
        self.tray_icon.setIcon(icon)
        self.listen_action.setChecked(True)
        self.listen_action.setText("Listening")
        signal_manager.voice_set_is_listening.emit(True)
        signal_manager.action_set_is_listening.emit(True)

    def disable_tray(self):
        icon_path = os.path.join(ICONS_DIR, "tray-disabled.png")
        icon = QtGui.QIcon(icon_path)
        self.tray_icon.setIcon(icon)
        self.listen_action.setChecked(False)
        self.listen_action.setText("Not Listening")
        signal_manager.voice_set_is_listening.emit(False)
        signal_manager.action_set_is_listening.emit(False)



    def create_menu(self):
        self.menu = QtWidgets.QMenu()
        
        self.listen_action = self.menu.addAction("Listening")
        self.listen_action.setCheckable(True)
        self.listen_action.setChecked(True)
        self.listen_action.triggered.connect(self.toggle_listening)

        self.menu.addSeparator()
        listen_action = self.menu.addAction("Record an Action")
        listen_action.triggered.connect(lambda: None)  # Do nothing when clicked

        listen_action = self.menu.addAction("New Chat")
        listen_action.triggered.connect(lambda: None)  # Do nothing when clicked

        self.menu.addSeparator()
        chat_id_action = self.menu.addAction("ChatID: 1234567890")
        chat_id_action.setEnabled(False)
        self.menu.addSeparator()

        self.menu.addAction("Chats", self.show_chat_window)  # Change "History" to "Chat"

        self.menu.addAction("Actions", self.show_actions)

        listen_action = self.menu.addAction("Snippets")
        listen_action.triggered.connect(lambda: None)  # Do nothing when clicked
        
        self.menu.addSeparator()
        
        self.toggle_visibility_action = self.menu.addAction("Hide Oracle")
        self.toggle_visibility_action.triggered.connect(self.toggle_visibility)
        
        self.change_globe_action = self.menu.addAction("Change Oracle")
        self.change_globe_action.triggered.connect(self.next_image)
        
        self.menu.addSeparator()
        self.menu.addAction("About DecisionsAI", self.show_about_window)
        self.menu.addSeparator()
        self.menu.addAction("Preferences", self.show_settings_window)
        self.menu.addSeparator()
        self.menu.addAction("Exit", self.exit_app)
        
        # Connect the aboutToShow signal to update the menu
        self.menu.aboutToShow.connect(self.update_menu)
        
        return self.menu

    def toggle_listening(self):
        if self.listen_action.isChecked():
            self.enable_tray()
            self.listen_action.setText("Listening")
        else:
            self.disable_tray()
            self.listen_action.setText("Not Listening")

    def update_menu(self):
        self.change_globe_action.setVisible(self.globe_visible)       

    def is_globe_window_open(self):
        return self.globe_visible

    def create_tray_icon(self):
        icon_path = os.path.join(ICONS_DIR, "tray.png")
        icon = QtGui.QIcon(icon_path)
        self.tray_icon.setIcon(icon)

        # Use the same menu for both the tray icon and the Oracle window
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide_globe()
            new_text = "Show Oracle"
        else:
            self.show_globe()
            new_text = "Hide Oracle"
        
        self.toggle_visibility_action.setText(new_text)
        self.toggle_visibility_tray_action.setText(new_text)


    def load_globe_image(self):
        gif_path = os.path.join(IMAGES_DIR, "oracle", f"{self.current_image_index}.gif")
        if not os.path.exists(gif_path):
            print(f"Error: GIF file not found at {gif_path}")
            return
        self.movie = QtGui.QMovie(gif_path)
        if not self.movie.isValid():
            print(f"Error: Invalid GIF file at {gif_path}")
            return
        self.movie.frameChanged.connect(self.update_frame)
        self.gif_label.setMovie(self.movie)
        self.movie.start()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Draw shadow
        shadow_rect = self.rect().adjusted(self.shadow_size, self.shadow_size, -self.shadow_size, -self.shadow_size)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self.shadow_color)
        painter.drawEllipse(shadow_rect)

        # Draw filled content
        content_rect = QtCore.QRect(self.shadow_size + self.stroke_width, 
                                    self.shadow_size + self.stroke_width, 
                                    self.content_size, 
                                    self.content_size)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self.fill_color)
        painter.drawEllipse(content_rect)

        # Draw inner shadow
        inner_shadow_rect = content_rect.adjusted(2, 2, -2, -2)
        center = inner_shadow_rect.center()
        gradient = QtGui.QRadialGradient(
            center.x(), center.y(),
            inner_shadow_rect.width() / 2
        )
        gradient.setColorAt(0.95, QtGui.QColor(0, 0, 0, 0))
        gradient.setColorAt(1, self.inner_shadow_color)
        painter.setBrush(gradient)
        painter.drawEllipse(inner_shadow_rect)

        # Draw animated border
        painter.setPen(QtGui.QPen(self.border_color, self.stroke_width, 
                                  QtCore.Qt.PenStyle.SolidLine, 
                                  QtCore.Qt.PenCapStyle.RoundCap, 
                                  QtCore.Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawEllipse(content_rect)

    def update_frame(self):
        current_frame = self.movie.currentPixmap()
        scaled_frame = current_frame.scaled(
            self.content_size + 75, self.content_size + 75,
            QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        center = scaled_frame.rect().center()
        target_rect = QtCore.QRect(0, 0, self.content_size, self.content_size)
        target_rect.moveCenter(center)
        cropped_frame = scaled_frame.copy(target_rect)
        self.gif_label.setPixmap(cropped_frame)

    def resizeEvent(self, event):
        path = QtGui.QPainterPath()
        path.addEllipse(0, 0, self.total_size, self.total_size)
        self.setMask(QtGui.QRegion(path.toFillPolygon().toPolygon()))


    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = event.position().toPoint()
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            self.menu.exec(event.globalPosition().toPoint())

    def next_image(self):
        self.current_image_index = (self.current_image_index + 1) % 7
        # testing colours
        # if self.current_image_index == 1:
        #     self.set_red_animation()
        # elif self.current_image_index == 2:
        #     self.set_yellow_animation()
        # elif self.current_image_index == 3:
        #     self.set_blue_animation()
        # elif self.current_image_index == 4:
        #     self.set_green_animation()
        # elif self.current_image_index == 5:
        #     self.set_white_animation()
        # elif self.current_image_index == 6:
        #     self.reset_color_animation()
        self.load_globe_image()

    def exit_app(self):
        print("Exiting app")
        QApplication.instance().quit()
        signal_manager.exit_app.emit()

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_position = self.mapToParent(event.position().toPoint() - self.offset)
            self.move(new_position)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.dragging = False

    def on_move_event(self, event):
        super().moveEvent(event)
        signal_manager.update_voice_box_position.emit()

    def play_voice_box(self):
        print("Playing voice box animation")
        signal_manager.update_voice_box_position.emit()
        self.voice_box.show()
        self.voice_box.play_gif()

    def stop_voice_box(self):
        print("Stopping voice box")
        self.voice_box.stop_gif()
        self.voice_box.hide()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                print(f"File dropped: {file_path}")
            elif os.path.isdir(file_path):
                print(f"Directory dropped: {file_path}")
                self.print_directory_tree(file_path)

    def print_directory_tree(self, start_path):
        for root, dirs, files in os.walk(start_path):
            level = root.replace(start_path, '').count(os.sep)
            indent = ' ' * 4 * level
            print(f"{indent}{os.path.basename(root)}/")
            sub_indent = ' ' * 4 * (level + 1)
            for file in files:
                print(f"{sub_indent}{file}")

    def show_about_window(self):
        self.about_window.show()
        self.about_window.raise_()
        self.about_window.activateWindow()

    def show_settings_window(self):
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def show_globe(self):
        self.globe_visible = True
        print(f"Oracle shown. self.isVisible(): {self.isVisible()}, globe_visible: {self.globe_visible}")
        QTimer.singleShot(0, self.show)
        QTimer.singleShot(0, self.gif_label.show)
        QTimer.singleShot(10, self.update)
        QTimer.singleShot(20, self.update_menu)

    def hide_globe(self):
        self.globe_visible = False
        print(f"Oracle hidden. self.isVisible(): {self.isVisible()}, globe_visible: {self.globe_visible}")
        QTimer.singleShot(0, self.hide)
        QTimer.singleShot(10, self.update_menu)

    def show_chat_window(self):
        if not self.chat_window:
            self.chat_window = ChatWindow(self.chat_manager)
        self.chat_window.show()
        self.chat_window.raise_()
        self.chat_window.activateWindow()

    def show_actions(self):
        print("Show Actions")
        # Implement the functionality to show the actions

    # Add this new method
    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def set_color_animation(self, color, animation_speed=1000):
        start_color = QtGui.QColor(0, 0, 0)  # Always start from black
        end_color = QtGui.QColor(*color)
        
        self.border_forward_animation.setStartValue(start_color)
        self.border_forward_animation.setEndValue(end_color)
        self.border_backward_animation.setStartValue(end_color)
        self.border_backward_animation.setEndValue(start_color)

        inner_shadow_start = QtGui.QColor(0, 0, 0, 100)
        inner_shadow_end = QtGui.QColor(color[0], color[1], color[2], 100)
        
        self.inner_shadow_forward_animation.setStartValue(inner_shadow_start)
        self.inner_shadow_forward_animation.setEndValue(inner_shadow_end)
        self.inner_shadow_backward_animation.setStartValue(inner_shadow_end)
        self.inner_shadow_backward_animation.setEndValue(inner_shadow_start)

        # Update shadow animation
        shadow_start = QtGui.QColor(0, 0, 0, 100)
        shadow_end = QtGui.QColor(color[0], color[1], color[2], 100)
        
        self.shadow_forward_animation.setStartValue(shadow_start)
        self.shadow_forward_animation.setEndValue(shadow_end)
        self.shadow_backward_animation.setStartValue(shadow_end)
        self.shadow_backward_animation.setEndValue(shadow_start)

        for anim in [self.border_forward_animation, self.border_backward_animation,
                     self.inner_shadow_forward_animation, self.inner_shadow_backward_animation,
                     self.shadow_forward_animation, self.shadow_backward_animation]:
            anim.setDuration(animation_speed)

        self.animation_group.stop()
        self.animation_group.start()

    @QtCore.pyqtProperty(QtGui.QColor)
    def border_color(self):
        return self._border_color

    @border_color.setter
    def border_color(self, color):
        self._border_color = color
        self.update()

    @QtCore.pyqtProperty(QtGui.QColor)
    def inner_shadow_color(self):
        return self._inner_shadow_color

    @inner_shadow_color.setter
    def inner_shadow_color(self, color):
        self._inner_shadow_color = color
        self.update()

    @QtCore.pyqtProperty(QtGui.QColor)
    def shadow_color(self):
        return self._shadow_color

    @shadow_color.setter
    def shadow_color(self, color):
        self._shadow_color = color
        self.update()

    def set_red_animation(self, animation_speed=1000):
        self.set_color_animation((230, 0, 0), animation_speed)  # Red (#e60000)

    def set_yellow_animation(self, animation_speed=1000):
        self.set_color_animation((227, 215, 18), animation_speed)  # Yellow (#e3d712)

    def set_blue_animation(self, animation_speed=1000):
        self.set_color_animation((8, 201, 236), animation_speed)  # Blue (#08c9ec)

    def set_green_animation(self, animation_speed=1000):
        self.set_color_animation((68, 186, 45), animation_speed)  # Green (#44ba2d)

    def set_white_animation(self, animation_speed=1000):
        self.set_color_animation((255, 255, 255), animation_speed)  # White

    def reset_color_animation(self):
        self.set_color_animation((0, 0, 0), 1000)  # Reset to black
        # Reset shadow color animations
        shadow_color = QtGui.QColor(0, 0, 0, 100)
        self.shadow_forward_animation.setStartValue(shadow_color)
        self.shadow_forward_animation.setEndValue(shadow_color)
        self.shadow_backward_animation.setStartValue(shadow_color)
        self.shadow_backward_animation.setEndValue(shadow_color)


