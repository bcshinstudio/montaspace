"""Frameless application window, shortcuts, menus, and metadata."""
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut, QUndoStack
from PySide6.QtWidgets import QMainWindow, QMessageBox
from .config import APP_VERSION, PUBLISHER, COPYRIGHT, WEBSITE, asset_path
from .canvas import Canvas
from .performance import memory_working_set_mb
from .project import ProjectPersistenceMixin


class MontaSpace(ProjectPersistenceMixin, QMainWindow):
    RESIZE_MARGIN = 8

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MontaSpace")
        self.setWindowIcon(QIcon(str(asset_path("assets/MontaSpace.ico"))))
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.resize(900, 600)
        self.setMinimumSize(400, 300)
        self.canvas = Canvas(self)
        self.setCentralWidget(self.canvas)

        self.project_path = None
        self.undo_stack = QUndoStack(self)
        self.undo_stack.setUndoLimit(50)
        self._embedded_sources = set()
        self._temp_extract = None
        self._saved_snapshot = self.project_snapshot()

        for shortcut, callback in (
            ("Ctrl+N", self.new_project),
            ("Ctrl+O", self.open_project),
            ("Ctrl+S", self.save_project),
            ("Ctrl+Shift+S", self.save_project_as),
            ("Ctrl+Z", self.perform_undo),
            ("Ctrl+Y", self.perform_redo),
            ("Ctrl+Shift+Z", self.perform_redo),
            ("Ctrl+D", self.canvas.duplicate_selected),
            ("Ctrl+A", self.select_all),
        ):
            key = QShortcut(QKeySequence(shortcut), self)
            key.activated.connect(callback)

    def show_about(self):
        """Display version and publisher attribution."""
        QMessageBox.about(
            self,
            "About MontaSpace",
            f"<h3>MontaSpace {APP_VERSION}</h3>"
            "<p>A lightweight, frameless visual workspace for arranging images.</p>"
            f"<p><b>Developed and published by {PUBLISHER}</b><br>"
            f"{COPYRIGHT}<br>"
            f'<a href="{WEBSITE}">{WEBSITE}</a></p>'
            "<p><b>Linked projects:</b> .mspace<br>"
            "<b>Portable projects:</b> .mspacepack</p>"
            "<p>Built with Python and PySide6 (Qt).<br>"
            "Video support is planned for a future release.</p>"
            "<p><small>Copyright in photos imported by users remains with "
            "their respective owners.</small></p>",
        )

    def show_performance_info(self):
        """On-demand diagnostics; no background monitoring or extra packages."""
        items = self.canvas.image_stack()
        # Ignore duplicate pixmaps that share the same Qt pixel storage.
        pixmaps = {i.pixmap.cacheKey(): i.pixmap for i in items}
        estimated_mb = sum(
            p.width() * p.height() * 4 for p in pixmaps.values()
        ) / (1024 * 1024)
        working_set = memory_working_set_mb()
        ram_text = (f"{working_set:.1f} MB" if working_set is not None
                    else "Not available")
        QMessageBox.information(
            self, "MontaSpace — Performance Info",
            f"Images on board: {len(items)}\n"
            f"Unique image previews: {len(pixmaps)}\n"
            f"Estimated decoded preview pixels: {estimated_mb:.1f} MB\n"
            f"Current process RAM (Windows working set): {ram_text}\n\n"
            "Preview pixel estimate excludes Qt, Undo history, and other "
            "application memory. Portable projects still embed original files."
        )

    def perform_undo(self):
        if self.canvas.active_crop:
            self.canvas.finish_crop(False)
        self.undo_stack.undo()
        self.update_modified_title()

    def perform_redo(self):
        if self.canvas.active_crop:
            self.canvas.finish_crop(False)
        self.undo_stack.redo()
        self.update_modified_title()

    def select_all(self):
        if not self.canvas.active_crop:
            for item in self.canvas.image_stack():
                item.setSelected(True)

    def update_modified_title(self):
        label = self.project_path.name if self.project_path else "Untitled"
        star = " *" if self.project_is_modified() else ""
        self.setWindowTitle(f"MontaSpace — {label}{star}")

    def closeEvent(self, event):
        if self.confirm_discard_changes():
            event.accept()
        else:
            event.ignore()

    def resize_edges(self, position):
        edges = Qt.Edge(0)
        if position.x() < self.RESIZE_MARGIN:
            edges |= Qt.Edge.LeftEdge
        elif position.x() >= self.width() - self.RESIZE_MARGIN:
            edges |= Qt.Edge.RightEdge
        if position.y() < self.RESIZE_MARGIN:
            edges |= Qt.Edge.TopEdge
        elif position.y() >= self.height() - self.RESIZE_MARGIN:
            edges |= Qt.Edge.BottomEdge
        return edges

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.windowHandle()
            edges = self.resize_edges(event.position().toPoint())
            if handle and edges and handle.startSystemResize(edges):
                event.accept()
                return
            if handle and event.modifiers() & Qt.KeyboardModifier.AltModifier:
                if handle.startSystemMove():
                    event.accept()
                    return
        super().mousePressEvent(event)
