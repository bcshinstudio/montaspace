"""MontaSpace — lightweight frameless image workspace, including crop mode."""

import sys
import json
import os
import tempfile
import math
import zipfile
import hashlib
import shutil
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QLineF, QTemporaryDir
from PySide6.QtGui import QColor, QBrush, QPainter, QPen, QPixmap, QImageReader, QPainterPath, QKeySequence, QShortcut, QUndoStack, QUndoCommand, QIcon
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QGraphicsItem, QGraphicsScene,
    QGraphicsView, QMainWindow, QMenu, QMessageBox,
)

PROJECT_FILTER = "MontaSpace Linked (*.mspace);;MontaSpace Portable (*.mspacepack)"
IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
PREVIEW_MAX_EDGE = 1600
APP_VERSION = "0.7.3"
PUBLISHER = "BC Shin Studio"
COPYRIGHT = "© 2026 BC Shin Studio. All rights reserved."
WEBSITE = "https://www.bcshinstudio.com"


def asset_path(relative_path):
    """Locate bundled assets in source and PyInstaller applications."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative_path


def load_preview(filename):
    """Decode images at display resolution rather than full camera resolution.

    This reduces peak RAM when opening large photos. Image transforms and crops
    remain non-destructive; original files are kept for portable project saving.
    """
    reader = QImageReader(str(filename))
    reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid() and max(size.width(), size.height()) > PREVIEW_MAX_EDGE:
        reader.setScaledSize(size.scaled(
            PREVIEW_MAX_EDGE,
            PREVIEW_MAX_EDGE,
            Qt.AspectRatioMode.KeepAspectRatio,
        ))
    image = reader.read()
    return QPixmap.fromImage(image) if not image.isNull() else QPixmap()


def memory_working_set_mb():
    """Report Windows process working set in MB; unavailable elsewhere."""
    if sys.platform != "win32":
        return None

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    info = ProcessMemoryCounters()
    info.cb = ctypes.sizeof(info)
    # Explicit 64-bit handle signatures prevent pointer truncation on Windows x64.
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.argtypes = []
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD,
    ]
    handle = kernel32.GetCurrentProcess()
    ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(info), info.cb)
    return info.WorkingSetSize / (1024 * 1024) if ok else None



class StateCommand(QUndoCommand):
    """Undo one edit by storing small metadata snapshots, not image bytes."""

    def __init__(self, canvas, before, after, name):
        super().__init__(name)
        self.canvas = canvas
        self.before = before
        self.after = after
        self.first_redo = True

    def redo(self):
        if self.first_redo:
            self.first_redo = False
            return  # The user already performed the action.
        self.canvas.restore_state(self.after)

    def undo(self):
        self.canvas.restore_state(self.before)



class ImageItem(QGraphicsItem):
    """One movable image. Cropping changes the view, not the image file."""

    HANDLE_SIZE = 12.0
    CROP_HANDLE_SIZE = 20.0
    CROP_GRAB_MARGIN = 14.0
    ROTATE_OFFSET = 34.0
    MIN_SCALE = 0.05
    MAX_SCALE = 20.0
    MIN_CROP = 12.0

    def __init__(self, pixmap, filename=""):
        super().__init__()
        self.filename = str(filename)
        self.pixmap = pixmap
        self.full_rect = QRectF(0, 0, pixmap.width(), pixmap.height())
        self.crop_rect = QRectF(self.full_rect)
        self.crop_mode = False
        self.crop_before_edit = None
        self._mode = None
        self._handle = None
        self._start_scale = 1.0
        self._start_rotation = 0.0
        self._start_angle = 0.0
        self._start_distance = 1.0
        self._crop_start_rect = None
        self._press_pos = None
        self._undo_start = None

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setTransformOriginPoint(self.full_rect.center())

    def handles(self):
        r = self.crop_rect
        # During crop mode, keep handles large even when the image is scaled down.
        size = (self.CROP_HANDLE_SIZE / max(self.scale(), 0.05)
                if self.crop_mode else self.HANDLE_SIZE)
        half = size / 2
        points = {
            "tl": r.topLeft(), "tr": r.topRight(),
            "bl": r.bottomLeft(), "br": r.bottomRight(),
        }
        if self.crop_mode:
            points.update({
                "top": (r.topLeft() + r.topRight()) / 2,
                "bottom": (r.bottomLeft() + r.bottomRight()) / 2,
                "left": (r.topLeft() + r.bottomLeft()) / 2,
                "right": (r.topRight() + r.bottomRight()) / 2,
            })
        result = {
            name: QRectF(p.x() - half, p.y() - half, size, size)
            for name, p in points.items()
        }
        if not self.crop_mode:
            result["rotate"] = QRectF(
                r.center().x() - half, r.top() - self.ROTATE_OFFSET - half,
                self.HANDLE_SIZE, self.HANDLE_SIZE,
            )
        return result

    def boundingRect(self):
        margin = self.ROTATE_OFFSET + self.HANDLE_SIZE + 6
        if self.crop_mode:
            margin = max(margin, self.CROP_HANDLE_SIZE / max(self.scale(), 0.05))
        return self.full_rect.adjusted(-margin, -margin, margin, margin)

    def shape(self):
        path = QPainterPath()
        path.addRect(self.full_rect if self.crop_mode else self.crop_rect)
        if self.isSelected():
            padding = (self.CROP_GRAB_MARGIN / max(self.scale(), 0.05)
                       if self.crop_mode else 5)
            for rect in self.handles().values():
                path.addRect(rect.adjusted(-padding, -padding, padding, padding))
        return path

    def handle_at(self, pos):
        if not self.isSelected():
            return None
        padding = (self.CROP_GRAB_MARGIN / max(self.scale(), 0.05)
                   if self.crop_mode else 5)
        for name, rect in self.handles().items():
            if rect.adjusted(-padding, -padding, padding, padding).contains(pos):
                return name

        # In crop mode, dragging close to any boundary works too,
        # even when the pointer isn't exactly over a square handle.
        if self.crop_mode:
            r = self.crop_rect
            margin = self.CROP_GRAB_MARGIN / max(self.scale(), 0.05)
            near_left = abs(pos.x() - r.left()) <= margin
            near_right = abs(pos.x() - r.right()) <= margin
            near_top = abs(pos.y() - r.top()) <= margin
            near_bottom = abs(pos.y() - r.bottom()) <= margin
            within_x = r.left() - margin <= pos.x() <= r.right() + margin
            within_y = r.top() - margin <= pos.y() <= r.bottom() + margin
            if within_x and within_y:
                if near_left and near_top:
                    return "tl"
                if near_right and near_top:
                    return "tr"
                if near_left and near_bottom:
                    return "bl"
                if near_right and near_bottom:
                    return "br"
                if near_left:
                    return "left"
                if near_right:
                    return "right"
                if near_top:
                    return "top"
                if near_bottom:
                    return "bottom"
        return None

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        if self.crop_mode:
            painter.setOpacity(0.30)
            painter.drawPixmap(self.full_rect, self.pixmap, self.full_rect)
            painter.setOpacity(1.0)

        painter.save()
        painter.setClipRect(self.crop_rect)
        painter.drawPixmap(self.full_rect, self.pixmap, self.full_rect)
        painter.restore()

        if not self.isSelected():
            return
        pen = QPen(QColor("#1676d2"), 2.5 if self.crop_mode else 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.crop_rect)
        handle_rects = self.handles()
        if "rotate" in handle_rects:
            painter.drawLine(
                self.crop_rect.center().x(), self.crop_rect.top(),
                handle_rects["rotate"].center().x(), handle_rects["rotate"].center().y(),
            )
        painter.setBrush(QBrush(QColor("#ffffff")))
        for name, rect in handle_rects.items():
            if name == "rotate":
                painter.drawEllipse(rect)
            else:
                painter.drawRect(rect)

    def start_crop(self):
        if self.crop_mode:
            return
        self.crop_before_edit = QRectF(self.crop_rect)
        self.crop_mode = True
        self.setSelected(True)
        self.update()

    def end_crop(self, apply):
        if not self.crop_mode:
            return
        if not apply:
            self.crop_rect = QRectF(self.crop_before_edit)
        self.crop_before_edit = None
        self.crop_mode = False
        self._mode = None
        self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Route through Canvas so editing gets priority over overlapping images.
            views = self.scene().views() if self.scene() else []
            if views and hasattr(views[0], "begin_crop"):
                views[0].begin_crop(self)
            else:
                self.start_crop()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.scene():
            self._undo_start = self.scene().views()[0].capture_state()
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.handle_at(event.pos())
            if handle:
                self._handle = handle
                self._press_pos = event.pos()
                if self.crop_mode:
                    self._mode = "crop"
                    self._crop_start_rect = QRectF(self.crop_rect)
                else:
                    center = self.mapToScene(self.transformOriginPoint())
                    line = QLineF(center, event.scenePos())
                    if handle == "rotate":
                        self._mode = "rotate"
                        self._start_rotation = self.rotation()
                        self._start_angle = line.angle()
                    else:
                        self._mode = "resize"
                        self._start_scale = self.scale()
                        self._start_distance = max(line.length(), 1.0)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._mode == "crop":
            dx = event.pos().x() - self._press_pos.x()
            dy = event.pos().y() - self._press_pos.y()
            r = self._crop_start_rect
            left, right, top, bottom = r.left(), r.right(), r.top(), r.bottom()
            if self._handle in ("tl", "bl", "left"):
                left = min(max(left + dx, self.full_rect.left()), right - self.MIN_CROP)
            if self._handle in ("tr", "br", "right"):
                right = max(min(right + dx, self.full_rect.right()), left + self.MIN_CROP)
            if self._handle in ("tl", "tr", "top"):
                top = min(max(top + dy, self.full_rect.top()), bottom - self.MIN_CROP)
            if self._handle in ("bl", "br", "bottom"):
                bottom = max(min(bottom + dy, self.full_rect.bottom()), top + self.MIN_CROP)
            self.crop_rect = QRectF(left, top, right - left, bottom - top)
            self.update()
            event.accept()
            return

        if self._mode in ("resize", "rotate"):
            center = self.mapToScene(self.transformOriginPoint())
            line = QLineF(center, event.scenePos())
            if self._mode == "rotate":
                self.setRotation(self._start_rotation + self._start_angle - line.angle())
            else:
                scale = self._start_scale * max(line.length(), 1.0) / self._start_distance
                self.setScale(max(self.MIN_SCALE, min(self.MAX_SCALE, scale)))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        was_editing = bool(self._mode)
        self._mode = None
        self._handle = None
        if not was_editing:
            super().mouseReleaseEvent(event)
        else:
            event.accept()
        if self._undo_start is not None and self.scene():
            canvas = self.scene().views()[0]
            if not self.crop_mode:
                canvas.record_edit(self._undo_start, "Move / transform image")
            self._undo_start = None

    def hoverMoveEvent(self, event):
        name = self.handle_at(event.pos())
        if self.crop_mode and name in ("tl", "br"):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif self.crop_mode and name in ("tr", "bl"):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif self.crop_mode and name in ("left", "right"):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif self.crop_mode and name in ("top", "bottom"):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif name == "rotate":
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif name in ("tl", "br"):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif name in ("tr", "bl"):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        super().hoverLeaveEvent(event)


class Canvas(QGraphicsView):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.scene_area = QGraphicsScene(self)
        self.scene_area.setSceneRect(-10000, -10000, 20000, 20000)
        self.setScene(self.scene_area)
        self.setBackgroundBrush(QBrush(QColor("white")))
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.image_count = 0
        self.active_crop = None
        self._crop_previous_z = None
        self._crop_disabled_items = []
        self._restoring = False

    def capture_state(self):
        """Immutable metadata for active items (pixmaps remain shared in memory)."""
        return tuple(
            (item, item.pos().x(), item.pos().y(), item.scale(), item.rotation(),
             tuple((item.crop_rect.x(), item.crop_rect.y(),
                    item.crop_rect.width(), item.crop_rect.height())), item.zValue())
            for item in self.image_stack()
        )

    def restore_state(self, state):
        self._restoring = True
        try:
            self.finish_crop(False)
            desired = {entry[0] for entry in state}
            for item in list(self.image_stack()):
                if item not in desired:
                    self.scene_area.removeItem(item)
            for item, x, y, scale, angle, crop, z in state:
                if item.scene() is None:
                    self.scene_area.addItem(item)
                item.setPos(x, y)
                item.setScale(scale)
                item.setRotation(angle)
                item.crop_rect = QRectF(*crop)
                item.setZValue(z)
                item.update()
            self.scene_area.clearSelection()
        finally:
            self._restoring = False
        self.window.update_modified_title()

    def record_edit(self, before, description):
        if self._restoring:
            return
        after = self.capture_state()
        if before != after:
            self.window.undo_stack.push(StateCommand(self, before, after, description))
            self.window.update_modified_title()

    def duplicate_selected(self):
        if self.active_crop:
            return
        selected = self.selected_images()
        if not selected:
            return
        before = self.capture_state()
        highest = max((i.zValue() for i in self.image_stack()), default=-1)
        self.scene_area.clearSelection()
        for original in selected:
            copy = ImageItem(original.pixmap, original.filename)
            copy.crop_rect = QRectF(original.crop_rect)
            copy.setPos(original.pos().x() + 30, original.pos().y() + 30)
            copy.setScale(original.scale())
            copy.setRotation(original.rotation())
            highest += 1
            copy.setZValue(highest)
            self.scene_area.addItem(copy)
            copy.setSelected(True)
            self.image_count += 1
        self.record_edit(before, "Duplicate image")

    def add_image(self, filename, scene_pos=None, record_undo=True):
        before = self.capture_state() if record_undo else None
        pixmap = load_preview(filename)
        if pixmap.isNull():
            return False
        item = ImageItem(pixmap, filename)
        if scene_pos is None:
            scene_pos = self.mapToScene(self.viewport().rect().center())
            offset = (self.image_count % 6) * 24
            scene_pos.setX(scene_pos.x() + offset)
            scene_pos.setY(scene_pos.y() + offset)
        item.setPos(scene_pos)
        item.setZValue(self.image_count)
        self.scene_area.addItem(item)
        self.scene_area.clearSelection()
        item.setSelected(True)
        self.image_count += 1
        if record_undo:
            self.record_edit(before, "Insert image")
        return True

    def insert_image(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Insert Image", "", IMAGE_FILTER)
        if filename:
            self.add_image(filename)

    def selected_images(self):
        return [i for i in self.scene_area.selectedItems() if isinstance(i, ImageItem)]

    def begin_crop(self, item):
        """Keep the edited image above others and route input to it."""
        if self.active_crop is item:
            return
        if self.active_crop is not None:
            self.finish_crop(True)

        self._before_crop_state = self.capture_state()
        self.scene_area.clearSelection()
        item.setSelected(True)
        self.active_crop = item
        self._crop_previous_z = item.zValue()

        # The crop handles must always be above overlapping photos.
        max_z = max((i.zValue() for i in self.scene_area.items()), default=0)
        item.setZValue(max_z + 1)

        # Prevent any other photo from intercepting crop-handle clicks.
        self._crop_disabled_items = []
        for other in self.scene_area.items():
            if isinstance(other, ImageItem) and other is not item:
                self._crop_disabled_items.append(
                    (other, other.acceptedMouseButtons(), other.acceptHoverEvents())
                )
                other.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                other.setAcceptHoverEvents(False)

        item.start_crop()
        self.setFocus()

    def finish_crop(self, apply):
        """Restore the regular stacking order and mouse interactions."""
        if self.active_crop is None:
            return

        item = self.active_crop
        before_crop = getattr(self, "_before_crop_state", None)
        item.end_crop(apply)
        if self._crop_previous_z is not None:
            item.setZValue(self._crop_previous_z)

        for other, buttons, hover in self._crop_disabled_items:
            if other.scene() is self.scene_area:
                other.setAcceptedMouseButtons(buttons)
                other.setAcceptHoverEvents(hover)

        self._crop_disabled_items = []
        self._crop_previous_z = None
        self.active_crop = None
        self.scene_area.clearSelection()
        item.setSelected(True)
        if apply and before_crop is not None:
            self.record_edit(before_crop, "Crop image")
        self._before_crop_state = None

    def delete_selected_items(self):
        self.finish_crop(False)
        before = self.capture_state()
        for item in self.scene_area.selectedItems():
            self.scene_area.removeItem(item)
        self.record_edit(before, "Delete image")

    def mouseDoubleClickEvent(self, event):
        """Enter crop mode on a double-clicked photo."""
        item = self.itemAt(event.position().toPoint())
        if isinstance(item, ImageItem):
            self.begin_crop(item)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def image_stack(self):
        """Return all photos from back to front, using scene order for ties."""
        return [
            item for item in reversed(self.scene_area.items())
            if isinstance(item, ImageItem)
        ]

    def arrange_image(self, item, operation):
        """Move one image within the persistent stacking order."""
        if self.active_crop:
            return

        stack = self.image_stack()
        if item not in stack:
            return
        before = self.capture_state()

        old_index = stack.index(item)
        stack.pop(old_index)
        if operation == "front":
            new_index = len(stack)
        elif operation == "back":
            new_index = 0
        elif operation == "forward":
            new_index = min(old_index + 1, len(stack))
        elif operation == "backward":
            new_index = max(old_index - 1, 0)
        else:
            return

        stack.insert(new_index, item)
        for z, image in enumerate(stack):
            image.setZValue(z)

        self.scene_area.clearSelection()
        item.setSelected(True)
        self.viewport().update()
        self.record_edit(before, "Arrange image")

    def images_at(self, viewport_point):
        """Find all photos covering the clicked pixel, front to back."""
        scene_point = self.mapToScene(viewport_point)
        # Use each image's real visible crop, not its oversized handle bounds.
        result = []
        for image in reversed(self.image_stack()):
            local_point = image.mapFromScene(scene_point)
            if image.crop_rect.contains(local_point):
                result.append(image)
        return result

    def add_arrange_actions(self, menu, image, actions):
        """Add standard layer operations for a specific image."""
        stack = self.image_stack()
        if image not in stack:
            return
        index = stack.index(image)
        labels = (
            ("Bring to Front", "front", index < len(stack) - 1),
            ("Bring Forward", "forward", index < len(stack) - 1),
            ("Send Backward", "backward", index > 0),
            ("Send to Back", "back", index > 0),
        )
        for label, operation, enabled in labels:
            action = menu.addAction(label)
            action.setEnabled(enabled)
            actions[action] = (image, operation)

    def contextMenuEvent(self, event):
        """Show file actions plus the photos under the pointer."""
        menu = QMenu(self)
        if self.active_crop:
            apply_action = menu.addAction("Apply Crop (Enter)")
            cancel_action = menu.addAction("Cancel Crop (Esc)")
            chosen = menu.exec(event.globalPos())
            if chosen == apply_action:
                self.finish_crop(True)
            elif chosen == cancel_action:
                self.finish_crop(False)
            return

        file_menu = menu.addMenu("File")
        new_action = file_menu.addAction("New                  Ctrl+N")
        open_action = file_menu.addAction("Open...              Ctrl+O")
        save_action = file_menu.addAction("Save                 Ctrl+S")
        save_as_action = file_menu.addAction("Save As...        Ctrl+Shift+S")
        menu.addSeparator()
        undo_action = menu.addAction("Undo                  Ctrl+Z")
        redo_action = menu.addAction("Redo                  Ctrl+Y")
        undo_action.setEnabled(self.window.undo_stack.canUndo())
        redo_action.setEnabled(self.window.undo_stack.canRedo())
        menu.addSeparator()

        images_here = self.images_at(event.pos())
        arrange_actions = {}
        select_actions = {}
        crop_actions = {}

        if images_here:
            images_menu = menu.addMenu(f"Images Here ({len(images_here)})")
            for rank, image in enumerate(images_here, 1):
                name = Path(image.filename).name or f"Image {rank}"
                if len(name) > 45:
                    name = name[:42] + "..."
                image_menu = images_menu.addMenu(f"{rank}. {name}")
                action = image_menu.addAction("Select Image")
                select_actions[action] = image
                action = image_menu.addAction("Crop Image")
                crop_actions[action] = image
                image_menu.addSeparator()
                self.add_arrange_actions(image_menu, image, arrange_actions)
            menu.addSeparator()

        insert_menu = menu.addMenu("Insert")
        image_action = insert_menu.addAction("Image...")
        menu.addSeparator()

        selected = self.selected_images()
        if len(selected) == 1:
            active = selected[0]
            selected_menu = menu.addMenu("Selected Image")
            crop_selected_action = selected_menu.addAction("Crop Image")
            crop_actions[crop_selected_action] = active
            selected_menu.addSeparator()
            self.add_arrange_actions(selected_menu, active, arrange_actions)

        duplicate_action = menu.addAction("Duplicate Selected    Ctrl+D") if selected else None
        select_all_action = menu.addAction("Select All            Ctrl+A")
        delete_action = menu.addAction("Delete Selected") if selected else None
        menu.addSeparator()
        performance_action = menu.addAction("Performance Info...")
        about_action = menu.addAction("About MontaSpace...")
        minimize_action = menu.addAction("Minimize")
        exit_action = menu.addAction("Exit")

        chosen = menu.exec(event.globalPos())
        if chosen == new_action:
            self.window.new_project()
        elif chosen == open_action:
            self.window.open_project()
        elif chosen == save_action:
            self.window.save_project()
        elif chosen == save_as_action:
            self.window.save_project_as()
        elif chosen == undo_action:
            self.window.perform_undo()
        elif chosen == redo_action:
            self.window.perform_redo()
        elif chosen == image_action:
            self.insert_image()
        elif chosen == duplicate_action:
            self.duplicate_selected()
        elif chosen == select_all_action:
            for item in self.image_stack():
                item.setSelected(True)
        elif chosen in select_actions:
            image = select_actions[chosen]
            self.scene_area.clearSelection()
            image.setSelected(True)
        elif chosen in crop_actions:
            self.begin_crop(crop_actions[chosen])
        elif chosen in arrange_actions:
            image, operation = arrange_actions[chosen]
            self.arrange_image(image, operation)
        elif delete_action is not None and chosen == delete_action:
            self.delete_selected_items()
        elif chosen == performance_action:
            self.window.show_performance_info()
        elif chosen == about_action:
            self.window.show_about()
        elif chosen == minimize_action:
            self.window.showMinimized()
        elif chosen == exit_action:
            self.window.close()

    def dragEnterEvent(self, event):
        if any(u.isLocalFile() and Path(u.toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS
               for u in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        pos = self.mapToScene(event.position().toPoint())
        count = 0
        for url in event.mimeData().urls():
            if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS:
                if self.add_image(url.toLocalFile(), pos):
                    count += 1
                    pos.setX(pos.x() + 25)
                    pos.setY(pos.y() + 25)
        if count:
            event.acceptProposedAction()
        else:
            event.ignore()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            before = self.capture_state()
            factor = 1.10 ** (event.angleDelta().y() / 120.0)
            for item in self.selected_images():
                item.setScale(max(item.MIN_SCALE, min(item.MAX_SCALE, item.scale() * factor)))
            self.record_edit(before, "Resize image")
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if self.active_crop:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.finish_crop(True)
                event.accept()
                return
            if event.key() == Qt.Key.Key_Escape:
                self.finish_crop(False)
                event.accept()
                return
        if event.key() == Qt.Key.Key_Delete and not self.active_crop:
            self.delete_selected_items()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self.mapTo(self.window, event.position().toPoint())
            edges = self.window.resize_edges(pos)
            handle = self.window.windowHandle()
            if edges and handle and handle.startSystemResize(edges):
                event.accept()
                return
            if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                if handle and handle.startSystemMove():
                    event.accept()
                    return
        super().mousePressEvent(event)


class MontaSpace(QMainWindow):
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

    def project_snapshot(self):
        """Capture project state; selection itself is not a change."""
        images = []
        for item in self.canvas.image_stack():
            rect = item.crop_rect
            images.append({
                "source": str(Path(item.filename).resolve()),
                "x": item.pos().x(),
                "y": item.pos().y(),
                "scale": item.scale(),
                "rotation": item.rotation(),
                "crop": [rect.x(), rect.y(), rect.width(), rect.height()],
                "z": item.zValue(),
            })
        return images

    def project_is_modified(self):
        return self.project_snapshot() != self._saved_snapshot

    def confirm_discard_changes(self):
        """Allow Save, Discard, or Cancel before losing changes."""
        if not self.project_is_modified():
            return True
        answer = QMessageBox.question(
            self, "Unsaved changes",
            "Save the current MontaSpace project before continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            return self.save_project()
        return True

    def new_project(self):
        if not self.confirm_discard_changes():
            return
        self.canvas.finish_crop(True)
        self.canvas.scene_area.clear()
        self.canvas.image_count = 0
        self.undo_stack.clear()
        self.project_path = None
        self._embedded_sources.clear()
        self._temp_extract = None
        self._saved_snapshot = self.project_snapshot()
        self.setWindowTitle("MontaSpace — Untitled")

    def save_project(self):
        if self.project_path is None:
            return self.save_project_as()
        return self._write_project(self.project_path)

    def save_project_as(self):
        suggested = str(self.project_path or (Path.home() / "Documents" / "Untitled.mspace"))
        filename, chosen_filter = QFileDialog.getSaveFileName(
            self, "Save MontaSpace Project", suggested, PROJECT_FILTER,
        )
        if not filename:
            return False
        target = Path(filename)
        extension = ".mspacepack" if "Portable" in chosen_filter else ".mspace"
        if target.suffix.lower() != extension:
            target = target.with_suffix(extension)
        return self._write_project(target)

    def _build_payload(self, target, portable):
        records = self.project_snapshot()
        for record in records:
            src = Path(record["source"])
            if not src.is_file():
                raise FileNotFoundError(f"Original image not found:\n{src}")
            if not portable:
                # Embedded images from an opened pack need durable, linked copies.
                if str(src.resolve()) in self._embedded_sources:
                    assets_dir = target.parent / f"{target.stem}_assets"
                    assets_dir.mkdir(parents=True, exist_ok=True)
                    digest = hashlib.sha256(str(src).encode()).hexdigest()[:12]
                    dest = assets_dir / f"{digest}_{src.name}"
                    if src.resolve() != dest.resolve():
                        shutil.copy2(src, dest)
                    src = dest
                record["source"] = os.path.relpath(str(src), target.parent)
        return records

    def _write_project(self, target):
        self.canvas.finish_crop(True)
        target = Path(target).resolve()
        portable = target.suffix.lower() == ".mspacepack"
        if target.suffix.lower() not in (".mspace", ".mspacepack"):
            QMessageBox.warning(self, "Invalid extension", "Choose .mspace or .mspacepack")
            return False
        temp_path = None
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            records = self._build_payload(target, portable)
            payload = {"format": "MontaSpace", "version": 1, "images": records}
            if portable:
                assets = {}
                for record in records:
                    source = Path(record["source"])
                    # Use stable entry names; identical source files are included once.
                    if source not in assets:
                        digest = hashlib.sha256(str(source).encode()).hexdigest()[:16]
                        assets[source] = f"images/{digest}{source.suffix.lower()}"
                    record["source"] = assets[source]
                payload["portable"] = True

            with tempfile.NamedTemporaryFile(
                suffix=".tmp", prefix=".montaspace-", dir=target.parent,
                delete=False,
            ) as stream:
                temp_path = Path(stream.name)
            if portable:
                with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED,
                                     compresslevel=4, allowZip64=True) as package:
                    package.writestr("project.json", json.dumps(payload, indent=2))
                    for src, arcname in assets.items():
                        package.write(src, arcname=arcname)
            else:
                with temp_path.open("w", encoding="utf-8") as stream:
                    json.dump(payload, stream, indent=2, ensure_ascii=False)
                    stream.write("\n")
            os.replace(temp_path, target)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return False
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

        self.project_path = target
        self._saved_snapshot = self.project_snapshot()
        self.undo_stack.setClean()
        self.update_modified_title()
        return True

    def open_project(self):
        if not self.confirm_discard_changes():
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open MontaSpace Project", str(Path.home() / "Documents"),
            "MontaSpace Projects (*.mspace *.mspacepack)",
        )
        if not filename:
            return
        self._read_project(Path(filename))

    def _read_project(self, target):
        """Load either file type; extract embedded files to temporary storage."""
        target = Path(target).resolve()
        portable = target.suffix.lower() == ".mspacepack"
        temporary = None
        embedded_paths = set()
        try:
            if portable:
                temporary = QTemporaryDir()
                if not temporary.isValid():
                    raise OSError("Could not create a temporary directory for images.")
                with zipfile.ZipFile(target, "r") as package:
                    data = json.loads(package.read("project.json").decode("utf-8"))
                    if not isinstance(data, dict):
                        raise ValueError("Invalid project metadata.")
                    files = {info.filename: info for info in package.infolist()}
                    if len(files) > 10001:
                        raise ValueError("Portable project contains too many files.")
                    names = {rec["source"] for rec in data.get("images", [])}
                    if sum(files[n].file_size for n in names if n in files) > 2_000_000_000:
                        raise ValueError("Portable project exceeds the 2 GB extraction limit.")
                    for name in names:
                        if (not isinstance(name, str) or not name.startswith("images/")
                                or "/" in name[7:] or ".." in name):
                            raise ValueError("Unsafe portable image path.")
                        info = files.get(name)
                        if info is None or info.is_dir() or info.file_size > 1_000_000_000:
                            raise ValueError(f"Missing or oversized embedded image: {name}")
                        dest = Path(temporary.path()) / name
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with package.open(info) as src, dest.open("wb") as dst:
                            shutil.copyfileobj(src, dst, length=1024*1024)
                        embedded_paths.add(str(dest.resolve()))
            else:
                with target.open("r", encoding="utf-8") as stream:
                    data = json.load(stream)
            if (not isinstance(data, dict) or data.get("format") != "MontaSpace"
                    or data.get("version") != 1 or not isinstance(data.get("images"), list)):
                raise ValueError("Not a supported MontaSpace project file.")
            if len(data["images"]) > 10000:
                raise ValueError("This project contains too many image records.")
            parsed = []
            for record in data["images"]:
                source = Path(record["source"])
                if portable:
                    source = Path(temporary.path()) / source
                elif not source.is_absolute():
                    source = target.parent / source
                nums = [float(record[k]) for k in ("x", "y", "scale", "rotation", "z")]
                crop = [float(n) for n in record["crop"]]
                if len(crop) != 4 or not all(math.isfinite(n) for n in nums + crop):
                    raise ValueError("Invalid image transform or crop.")
                if not 0.05 <= nums[2] <= 20:
                    raise ValueError("Invalid image scale.")
                parsed.append((source, nums, crop))
        except (OSError, ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError,
                zipfile.BadZipFile, RuntimeError) as exc:
            QMessageBox.critical(self, "Open failed", str(exc))
            return False

        self.canvas.finish_crop(False)
        self.canvas.scene_area.clear()
        self.canvas.image_count = 0
        missing = []
        for source, nums, crop in parsed:
            if not self.canvas.add_image(str(source), record_undo=False):
                missing.append(str(source))
                continue
            item = self.canvas.selected_images()[0]
            item.setPos(nums[0], nums[1])
            item.setScale(nums[2])
            item.setRotation(nums[3])
            item.setZValue(nums[4])
            rect = QRectF(*crop).intersected(item.full_rect)
            if rect.width() >= item.MIN_CROP and rect.height() >= item.MIN_CROP:
                item.crop_rect = rect
                item.update()
        self.canvas.scene_area.clearSelection()
        self.project_path = target
        self._temp_extract = temporary
        self._embedded_sources = embedded_paths
        self.undo_stack.clear()
        self._saved_snapshot = self.project_snapshot()
        self.update_modified_title()
        if missing:
            shown = "\n".join(missing[:8])
            QMessageBox.warning(self, "Missing images",
                f"{len(missing)} image(s) could not load:\n{shown}\n\n"
                "Please locate or restore these images before saving.")
            self._saved_snapshot = None
        return True

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("MontaSpace")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(PUBLISHER)
    app.setWindowIcon(QIcon(str(asset_path("assets/MontaSpace.ico"))))
    window = MontaSpace()
    window.show()
    sys.exit(app.exec())
