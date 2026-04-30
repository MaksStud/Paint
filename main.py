import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QToolBar, QStatusBar, QFileDialog, QMessageBox,
    QColorDialog, QSpinBox, QLabel, QDialog,
    QVBoxLayout, QDialogButtonBox, QTextBrowser
)
from PyQt6.QtGui import QAction, QPainter, QColor, QPen, QImage, QUndoStack, QUndoCommand
from PyQt6.QtCore import Qt, QRectF


class AddShapeCommand(QUndoCommand):
    def __init__(self, scene, item, description):
        super().__init__(description)
        self.scene = scene
        self.item = item
        self.first_run = True

    def undo(self):
        self.scene.removeItem(self.item)

    def redo(self):
        if not self.first_run:
            self.scene.addItem(self.item)
        self.first_run = False


class PencilCommand(QUndoCommand):
    def __init__(self, scene, items, description):
        super().__init__(description)
        self.scene = scene
        self.items = items
        self.first_run = True

    def undo(self):
        for item in self.items:
            self.scene.removeItem(item)

    def redo(self):
        if not self.first_run:
            for item in self.items:
                self.scene.addItem(item)
        self.first_run = False


class BackgroundColorCommand(QUndoCommand):
    def __init__(self, apply_color, old_color, new_color):
        super().__init__("Зміна фону")
        self.apply_color = apply_color
        self.old_color = QColor(old_color)
        self.new_color = QColor(new_color)

    def undo(self):
        self.apply_color(self.old_color)

    def redo(self):
        self.apply_color(self.new_color)


class DrawingScene(QGraphicsScene):
    def __init__(self, undo_stack, parent=None):
        super().__init__(parent)
        self.undo_stack = undo_stack
        self.setSceneRect(0, 0, 800, 600)
        self.bg_color = QColor(Qt.GlobalColor.white)
        self.setBackgroundBrush(self.bg_color)

        self.current_tool = "pencil"
        self.current_color = QColor(Qt.GlobalColor.black)
        self.line_width = 2

        self.last_point = None
        self.current_item = None
        self.pencil_items = []

    def set_tool(self, tool):
        self.current_tool = tool

    def set_color(self, color):
        self.current_color = color

    def set_bg_color(self, color):
        self.bg_color = QColor(color)
        self.setBackgroundBrush(self.bg_color)
        self.update(self.sceneRect())

    def set_line_width(self, width):
        self.line_width = width

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_point = event.scenePos()
            self.pencil_items = []
            if self.current_tool == "line":
                pen = QPen(self.current_color, self.line_width)
                self.current_item = self.addLine(
                    self.last_point.x(), self.last_point.y(),
                    self.last_point.x(), self.last_point.y(),
                    pen
                )
            elif self.current_tool == "rect":
                pen = QPen(self.current_color, self.line_width)
                self.current_item = self.addRect(
                    QRectF(self.last_point, self.last_point),
                    pen
                )
            elif self.current_tool == "ellipse":
                pen = QPen(self.current_color, self.line_width)
                self.current_item = self.addEllipse(
                    QRectF(self.last_point, self.last_point),
                    pen
                )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            current_pos = event.scenePos()
            if self.current_tool == "pencil" or self.current_tool == "eraser":
                color = self.current_color if self.current_tool == "pencil" else self.bg_color
                pen = QPen(color, self.line_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                line = self.addLine(
                    self.last_point.x(), self.last_point.y(),
                    current_pos.x(), current_pos.y(),
                    pen
                )
                self.pencil_items.append(line)
                self.last_point = current_pos
            elif self.current_tool == "line" and self.current_item:
                self.current_item.setLine(
                    self.last_point.x(), self.last_point.y(),
                    current_pos.x(), current_pos.y()
                )
            elif self.current_tool == "rect" and self.current_item:
                rect = QRectF(self.last_point, current_pos).normalized()
                self.current_item.setRect(rect)
            elif self.current_tool == "ellipse" and self.current_item:
                rect = QRectF(self.last_point, current_pos).normalized()
                self.current_item.setRect(rect)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.current_tool == "pencil" and self.pencil_items:
                command = PencilCommand(self, self.pencil_items, "Малювання олівцем")
                self.undo_stack.push(command)
            elif self.current_item:
                name = {"line": "Лінія", "rect": "Прямокутник", "ellipse": "Еліпс"}.get(self.current_tool, "Фігура")
                command = AddShapeCommand(self, self.current_item, f"Додавання: {name}")
                self.undo_stack.push(command)
            self.current_item = None
            self.pencil_items = []
        super().mouseReleaseEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyPaint - Системний Графічний Редактор")
        self.resize(1000, 700)

        # Undo Stack
        self.undo_stack = QUndoStack(self)
        self.undo_stack.cleanChanged.connect(self.update_modified)
        self.modified = False

        # Scene and View
        self.scene = DrawingScene(self.undo_stack)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setBackgroundBrush(QColor(Qt.GlobalColor.white))
        self.view.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setCentralWidget(self.view)

        # UI Components
        self.init_menus()
        self.init_toolbars()
        self.init_statusbar()
        self.undo_stack.setClean()

    def update_modified(self, clean):
        self.modified = not clean
        if self.modified:
            self.statusBar().showMessage("Документ змінено")

    def apply_background_color(self, color):
        self.scene.set_bg_color(color)
        self.view.setBackgroundBrush(self.scene.bg_color)
        self.view.viewport().update()

    def reset_canvas(self):
        self.scene.clear()
        self.apply_background_color(QColor(Qt.GlobalColor.white))
        self.undo_stack.clear()
        self.undo_stack.setClean()
        self.modified = False

    def init_menus(self):
        menubar = self.menuBar()

        # Actions that will be used in both menu and toolbars
        self.new_act = QAction("📄 Новий", self)
        self.new_act.triggered.connect(self.new_file)

        self.save_act = QAction("💾 Зберегти", self)
        self.save_act.triggered.connect(self.save_file)

        self.exit_act = QAction("Вихід", self)
        self.exit_act.triggered.connect(self.close)

        self.undo_act = self.undo_stack.createUndoAction(self, "↩️ Скасувати")
        self.undo_act.setShortcut("Ctrl+Z")

        self.redo_act = self.undo_stack.createRedoAction(self, "↪️ Повторити")
        self.redo_act.setShortcut("Ctrl+Y")

        self.clear_act = QAction("🗑️ Очистити", self)
        self.clear_act.triggered.connect(self.clear_scene)

        # File Menu
        file_menu = menubar.addMenu("Файл")
        file_menu.addAction(self.new_act)
        file_menu.addAction(self.save_act)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_act)

        # Edit Menu
        edit_menu = menubar.addMenu("Правка")
        edit_menu.addAction(self.undo_act)
        edit_menu.addAction(self.redo_act)
        edit_menu.addSeparator()
        edit_menu.addAction(self.clear_act)

        # View Menu
        self.view_menu = menubar.addMenu("Вигляд")

        # Help Menu
        help_menu = menubar.addMenu("Довідка")
        help_action = QAction("Переглянути довідку", self)
        help_action.triggered.connect(self.open_help)
        help_menu.addAction(help_action)

        about_action = QAction("Про програму", self)
        about_action.triggered.connect(self.about)
        help_menu.addAction(about_action)

    def init_toolbars(self):
        # 1. File Toolbar
        self.file_toolbar = QToolBar("Файлові операції")
        self.file_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(self.file_toolbar)
        self.view_menu.addAction(self.file_toolbar.toggleViewAction())
        self.file_toolbar.addAction(self.new_act)
        self.file_toolbar.addAction(self.save_act)

        # 2. Drawing Tools Toolbar
        self.tools_toolbar = QToolBar("Інструменти малювання")
        self.tools_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(self.tools_toolbar)
        self.view_menu.addAction(self.tools_toolbar.toggleViewAction())

        pencil_act = QAction("✏️ Олівець", self)
        pencil_act.setToolTip("Вільне малювання олівцем")
        pencil_act.triggered.connect(lambda: self.scene.set_tool("pencil"))
        self.tools_toolbar.addAction(pencil_act)

        line_act = QAction("📏 Лінія", self)
        line_act.setToolTip("Малювання прямої лінії")
        line_act.triggered.connect(lambda: self.scene.set_tool("line"))
        self.tools_toolbar.addAction(line_act)

        rect_act = QAction("⬜ Прямокутник", self)
        rect_act.setToolTip("Малювання прямокутника")
        rect_act.triggered.connect(lambda: self.scene.set_tool("rect"))
        self.tools_toolbar.addAction(rect_act)

        ellipse_act = QAction("⭕ Еліпс", self)
        ellipse_act.setToolTip("Малювання еліпса або кола")
        ellipse_act.triggered.connect(lambda: self.scene.set_tool("ellipse"))
        self.tools_toolbar.addAction(ellipse_act)

        eraser_act = QAction("🧼 Стирачка", self)
        eraser_act.setToolTip("Стирання частин малюнку (білий колір)")
        eraser_act.triggered.connect(lambda: self.scene.set_tool("eraser"))
        self.tools_toolbar.addAction(eraser_act)

        # 3. Style Toolbar
        self.style_toolbar = QToolBar("Властивості")
        self.style_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(self.style_toolbar)
        self.view_menu.addAction(self.style_toolbar.toggleViewAction())

        color_act = QAction("🎨 Колір", self)
        color_act.setToolTip("Вибрати колір малювання")
        color_act.triggered.connect(self.choose_color)
        self.style_toolbar.addAction(color_act)

        bg_color_act = QAction("🖼️ Фон", self)
        bg_color_act.setToolTip("Вибрати колір фону")
        bg_color_act.triggered.connect(self.choose_bg_color)
        self.style_toolbar.addAction(bg_color_act)

        self.style_toolbar.addWidget(QLabel(" Товщина: "))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 20)
        self.width_spin.setValue(2)
        self.width_spin.setToolTip("Товщина лінії")
        self.width_spin.valueChanged.connect(self.scene.set_line_width)
        self.style_toolbar.addWidget(self.width_spin)

        # 4. History Toolbar (Undo/Redo)
        self.history_toolbar = QToolBar("Історія дій")
        self.history_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(self.history_toolbar)
        self.view_menu.addAction(self.history_toolbar.toggleViewAction())
        self.history_toolbar.addAction(self.undo_act)
        self.history_toolbar.addAction(self.redo_act)

        # 5. Edit Toolbar
        self.edit_toolbar = QToolBar("Редагування")
        self.edit_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(self.edit_toolbar)
        self.view_menu.addAction(self.edit_toolbar.toggleViewAction())
        self.edit_toolbar.addAction(self.clear_act)

    def init_statusbar(self):
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Готово")

    def resizeEvent(self, event):
        # Expand the scene to match the view size when window is resized
        # This prevents cropping and "dead zones" when maximized
        view_rect = self.view.viewport().rect()
        scene_rect = self.scene.sceneRect()

        # United current scene rect with the new visible area
        new_rect = scene_rect.united(QRectF(0, 0, view_rect.width(), view_rect.height()))
        self.scene.setSceneRect(new_rect)

        super().resizeEvent(event)

    def choose_color(self):
        color = QColorDialog.getColor(self.scene.current_color, self, "Виберіть колір")
        if color.isValid():
            self.scene.set_color(color)

    def clear_scene(self):
        reply = QMessageBox.question(self, 
                                     'Підтвердження', 
                                     "Ви впевнені, що хочете очистити все полотно?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.reset_canvas()
            self.statusBar().showMessage("Полотно очищено")

    def new_file(self):
        if self.maybe_save():
            self.reset_canvas()
            self.statusBar().showMessage("Створено нове полотно")

    def maybe_save(self):
        if not self.modified:
            return True

        reply = QMessageBox.question(self, 'Збереження',
                                     "Документ було змінено. Бажаєте зберегти зміни перед продовженням?",
                                     QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                     QMessageBox.StandardButton.Save)

        if reply == QMessageBox.StandardButton.Save:
            return self.save_file()
        elif reply == QMessageBox.StandardButton.Cancel:
            return False
        return True

    def choose_bg_color(self):
        old_color = QColor(self.scene.bg_color)
        color = QColorDialog.getColor(old_color, self, "Виберіть колір фону")
        if color.isValid() and color != old_color:
            self.undo_stack.push(BackgroundColorCommand(self.apply_background_color, old_color, color))
            self.statusBar().showMessage("Колір фону змінено")

    def save_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Зберегти малюнок", "", "PNG Files (*.png);;JPG Files (*.jpg);;All Files (*)")
        if file_path:
            # Calculate the area that contains all drawn items
            items_rect = self.scene.itemsBoundingRect()
            # Also consider the current sceneRect to include background if items are small
            save_rect = items_rect.united(self.scene.sceneRect())

            # Create image with appropriate size
            image = QImage(save_rect.size().toSize(), QImage.Format.Format_ARGB32)
            image.fill(self.scene.bg_color)

            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            # Render the specific area to the image
            self.scene.render(painter, QRectF(image.rect()), save_rect)
            painter.end()

            if image.save(file_path):
                self.undo_stack.setClean()
                self.modified = False
                self.statusBar().showMessage(f"Збережено: {file_path}")
                return True
            else:
                QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти файл: {file_path}")
                return False
        return False

    def open_help(self):
        help_path = os.path.join(os.getcwd(), "help", "index.html")
        if os.path.exists(help_path):
            try:
                with open(help_path, "r", encoding="utf-8") as help_file:
                    help_html = help_file.read()
            except OSError as error:
                QMessageBox.critical(self, "Помилка", f"Не вдалося відкрити довідку: {error}")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle("Довідка PyPaint")
            dialog.resize(820, 640)

            layout = QVBoxLayout(dialog)

            help_view = QTextBrowser(dialog)
            help_view.setOpenExternalLinks(True)
            help_view.setHtml(help_html)
            layout.addWidget(help_view)

            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=dialog)
            buttons.rejected.connect(dialog.reject)
            buttons.accepted.connect(dialog.accept)
            layout.addWidget(buttons)

            dialog.exec()
        else:
            QMessageBox.information(self, "Довідка", "Файл довідки ще не створено.")

    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

    def about(self):
        QMessageBox.about(self, "Про PyPaint", 
                          "PyPaint v1.0\n\nГрафічний редактор як системна програма.\nРеалізовано на PyQt6 з підтримкою Undo/Redo та групуванням інструментів.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
