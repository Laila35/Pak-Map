"""Directory table: filtered ``DataPoint`` rows; ID stored on column 0 for sync."""

from __future__ import annotations

from PyQt5.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from models.datapoint import DataPoint


class DataTableWidget(QTableWidget):
    """Columns: ID, City, Lat, Lng, Value. Row identity in ``Qt.UserRole`` on column 0."""

    rowClicked = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(0, 5, parent)
        self.setObjectName("directoryTable")
        self.setHorizontalHeaderLabels(["ID", "City", "Lat", "Lng", "Value"])
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWordWrap(False)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.itemClicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, item: QTableWidgetItem) -> None:
        row = item.row()
        id_item = self.item(row, 0)
        if id_item is None:
            return
        rid = id_item.data(Qt.UserRole)
        if rid is not None:
            self.rowClicked.emit(str(rid))

    def row_index_for_id(self, row_id: str) -> int:
        for r in range(self.rowCount()):
            it = self.item(r, 0)
            if it is not None and str(it.data(Qt.UserRole)) == row_id:
                return r
        return -1

    def select_row_by_id(self, row_id: str) -> bool:
        """Select and scroll to the row for ``row_id`` (blocks selection signals)."""
        idx = self.row_index_for_id(row_id)
        if idx < 0:
            return False
        sm = self.selectionModel()
        if sm is None:
            return False
        with QSignalBlocker(sm):
            self.selectRow(idx)
        it = self.item(idx, 0)
        if it is not None:
            self.scrollToItem(it, QAbstractItemView.PositionAtCenter)
        return True

    def set_filtered_points(self, points: list[DataPoint]) -> None:
        """Replace all rows from the filtered/sorted dataset."""
        sm = self.selectionModel()
        if sm is not None:
            with QSignalBlocker(sm):
                self.setRowCount(0)
                for p in points:
                    self._append_point(p)
        else:
            self.setRowCount(0)
            for p in points:
                self._append_point(p)
        for col in (0, 2, 3, 4):
            self.resizeColumnToContents(col)

    def _append_point(self, p: DataPoint) -> None:
        row = self.rowCount()
        self.insertRow(row)

        id_item = QTableWidgetItem(p.id)
        id_item.setData(Qt.UserRole, p.id)
        id_item.setToolTip(p.id)

        city_item = QTableWidgetItem(p.city)
        lat_item = QTableWidgetItem(f"{p.lat:.4f}")
        lng_item = QTableWidgetItem(f"{p.lng:.4f}")
        val_item = QTableWidgetItem(self._format_value(p.value))
        val_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        for col, it in enumerate(
            (id_item, city_item, lat_item, lng_item, val_item)
        ):
            self.setItem(row, col, it)

    @staticmethod
    def _format_value(value: float) -> str:
        if value == int(value):
            return f"{int(value):,}"
        s = f"{value:,.2f}"
        if s.endswith(".00"):
            return s[:-3]
        return s
