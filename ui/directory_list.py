"""Directory panel: card rows (avatar, title, coords, tier, value) like reference UI."""

from __future__ import annotations

import hashlib

from PyQt5.QtCore import QSignalBlocker, QSize, Qt
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.datapoint import DataPoint


def _tier_label(value: float, vmin: float, vmax: float) -> str:
    if vmax <= vmin:
        return "TIER II"
    t = (value - vmin) / (vmax - vmin)
    if t >= 0.66:
        return "TIER I"
    if t >= 0.33:
        return "TIER II"
    return "TIER III"


def _display_title(p: DataPoint) -> str:
    c = (p.city or "").strip()
    if c:
        return c
    return f"Target {p.id[:8]}" if len(p.id) >= 4 else f"Target {p.id}"


def _make_avatar_pixmap(seed: str, size: int = 48) -> QPixmap:
    """Circular grayscale 'skyline' placeholder derived from seed (no external assets)."""
    h = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16)
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    bg = QColor(22, 22, 24)
    painter.fillRect(0, 0, size, size, bg)
    n = 5 + (h % 4)
    for i in range(n):
        x = (h >> (i * 3)) % max(1, size - 8)
        w = 4 + ((h >> i) % 5)
        ht = 12 + ((h >> (i + 2)) % (size // 2))
        gray = 55 + ((h >> (4 + i)) % 40)
        painter.fillRect(4 + (i * (size - 8) // max(1, n - 1)), size - ht, w, ht, QColor(gray, gray, gray))
    painter.end()
    return pix


def _format_value(value: float) -> str:
    if value == int(value):
        return f"{int(value):,}"
    s = f"{value:,.2f}"
    if s.endswith(".00"):
        return s[:-3]
    return s


class DirectoryRowWidget(QFrame):
    """Single directory row: avatar | title + coords | tier + value."""

    def __init__(self, point: DataPoint, tier: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("directoryRowCard")
        self._point_id = point.id
        self.setMinimumHeight(92)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), self.sizePolicy().verticalPolicy())

        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 10, 14, 10)
        outer.setSpacing(12)

        av = QLabel()
        av.setObjectName("directoryAvatar")
        av.setFixedSize(48, 48)
        av.setPixmap(_make_avatar_pixmap(point.id + point.city, 48))
        av.setScaledContents(False)
        outer.addWidget(av, 0, Qt.AlignVCenter)

        center = QVBoxLayout()
        center.setSpacing(4)
        center.setContentsMargins(0, 0, 0, 0)

        title = QLabel(_display_title(point))
        title.setObjectName("directoryRowTitle")
        title.setWordWrap(False)

        lat_l = QLabel(f"LAT: {point.lat:.2f}")
        lat_l.setObjectName("directoryRowCoords")
        lng_l = QLabel(f"LNG: {point.lng:.2f}")
        lng_l.setObjectName("directoryRowCoords")
        center.addWidget(title)
        center.addWidget(lat_l)
        center.addWidget(lng_l)
        outer.addLayout(center, stretch=1)

        right = QVBoxLayout()
        right.setSpacing(6)
        right.setAlignment(Qt.AlignTop | Qt.AlignRight)
        tier_l = QLabel(tier)
        tier_l.setObjectName("directoryRowTier")
        val_l = QLabel(_format_value(point.value))
        val_l.setObjectName("directoryRowValue")
        right.addWidget(tier_l, 0, Qt.AlignRight)
        right.addWidget(val_l, 0, Qt.AlignRight)
        outer.addLayout(right, 0)

    @property
    def point_id(self) -> str:
        return self._point_id

    def set_highlighted(self, on: bool) -> None:
        self.setProperty("active", on)
        self.style().unpolish(self)
        self.style().polish(self)


class DirectoryListWidget(QListWidget):
    """
    Card-style list mirroring the former table API: ``set_filtered_points``,
    ``select_row_by_id``, ``selectionModel`` for controller wiring.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("directoryList")
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setUniformItemSizes(True)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.setSpacing(2)
        self.currentRowChanged.connect(self._sync_highlights)

    def _sync_highlights(self, current: int, previous: int) -> None:
        for i in range(self.count()):
            w = self.itemWidget(self.item(i))
            if isinstance(w, DirectoryRowWidget):
                w.set_highlighted(i == current)

    def set_filtered_points(self, points: list[DataPoint]) -> None:
        self.blockSignals(True)
        with QSignalBlocker(self.selectionModel()):
            self.clear()
        vals = [p.value for p in points]
        vmin = min(vals) if vals else 0.0
        vmax = max(vals) if vals else 1.0

        for p in points:
            tier = _tier_label(p.value, vmin, vmax)
            item = QListWidgetItem()
            item.setData(Qt.UserRole, p.id)
            item.setSizeHint(QSize(0, 98))
            row = DirectoryRowWidget(p, tier)
            self.addItem(item)
            self.setItemWidget(item, row)

        self.blockSignals(False)
        self._sync_highlights(self.currentRow(), -1)

    def row_index_for_id(self, row_id: str) -> int:
        for r in range(self.count()):
            it = self.item(r)
            if it is not None and str(it.data(Qt.UserRole)) == row_id:
                return r
        return -1

    def select_row_by_id(self, row_id: str) -> bool:
        idx = self.row_index_for_id(row_id)
        if idx < 0:
            return False
        sm = self.selectionModel()
        if sm is None:
            return False
        with QSignalBlocker(sm):
            self.setCurrentRow(idx)
        it = self.item(idx)
        if it is not None:
            self.scrollToItem(it, QAbstractItemView.PositionAtCenter)
        self._sync_highlights(idx, -1)
        return True
