"""Frameless application window, shortcuts, menus, and metadata."""
from pathlib import Path
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QIcon, QKeySequence, QShortcut, QUndoStack
from PySide6.QtWidgets import QMainWindow, QMessageBox
from .config import APP_VERSION, PUBLISHER, COPYRIGHT, WEBSITE, asset_path
from .canvas import Canvas
from .performance import memory_working_set_mb, memory_peak_working_set_mb
from .project import ProjectPersistenceMixin
from .window_resize import (EDGE_MARGIN, ResizeHint, resize_cursor,
                            resize_edges_for_point)


class MontaSpace(ProjectPersistenceMixin, QMainWindow):
    RESIZE_MARGIN = EDGE_MARGIN

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MontaSpace")
        self.setWindowIcon(QIcon(str(asset_path("assets/MontaSpace.ico"))))
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.resize(900, 600)
        self.setMinimumSize(400, 300)
        self.canvas = Canvas(self)
        self.setCentralWidget(self.canvas)
        # The viewport covers almost the entire frameless window. Qt delivers
        # most pointer events to it rather than to QMainWindow.
        self._resize_hint = ResizeHint(self.canvas.viewport())
        self._resize_hover_edges = Qt.Edge(0)
        self.canvas.setMouseTracking(True)
        self.canvas.viewport().setMouseTracking(True)
        self.canvas.installEventFilter(self)
        self.canvas.viewport().installEventFilter(self)

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
        peak = memory_peak_working_set_mb()
        peak_text = f"{peak:.1f} MB" if peak is not None else "Not available"
        QMessageBox.information(
            self, "MontaSpace — Performance Info",
            f"Images on board: {len(items)}\n"
            f"Unique image previews: {len(pixmaps)}\n"
            f"Estimated decoded preview pixels: {estimated_mb:.1f} MB\n"
            f"Current process RAM (Windows working set): {ram_text}\n"
            f"Peak process RAM (since launch): {peak_text}\n"
            f"Undo history entries: {self.undo_stack.count()}\n\n"
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
        return resize_edges_for_point(position, self.width(), self.height())

    def update_resize_hover(self, position):
        """Expose a directional cursor and a small border hint near edges."""
        edges = self.resize_edges(position)
        changed = edges != self._resize_hover_edges
        self._resize_hover_edges = edges
        cursor = resize_cursor(edges)
        # Reapply the border cursor even if the zone has not changed: an image
        # item may update the viewport cursor during graphics-scene hover.
        if cursor is not None:
            self.canvas.viewport().setCursor(cursor)
        elif changed:
            self.canvas.viewport().unsetCursor()
        if changed:
            self._resize_hint.show_edges(edges)

    def clear_resize_hover(self):
        self._resize_hover_edges = Qt.Edge(0)
        self.canvas.viewport().unsetCursor()
        self._resize_hint.show_edges(Qt.Edge(0))

    def eventFilter(self, watched, event):
        # Keep the overlay sized to the actual image viewport and track its
        # pointer events, including when the pointer is over a photo.
        viewport = self.canvas.viewport()
        if watched is viewport:
            if event.type() == QEvent.Type.Resize:
                self._resize_hint.setGeometry(viewport.rect())
            elif event.type() == QEvent.Type.MouseMove:
                self.update_resize_hover(viewport.mapTo(self, event.position().toPoint()))
            elif event.type() == QEvent.Type.Enter:
                from PySide6.QtGui import QCursor
                self.update_resize_hover(viewport.mapTo(self, viewport.mapFromGlobal(QCursor.pos())))
            elif event.type() == QEvent.Type.Leave:
                self.clear_resize_hover()
        elif watched is self.canvas:
            if event.type() == QEvent.Type.MouseMove:
                self.update_resize_hover(self.canvas.mapTo(self, event.position().toPoint()))
        return super().eventFilter(watched, event)

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
