"""Application entry point: sidebar → ``self.data`` → filtered → map + table."""

from __future__ import annotations

import csv
import json
import sys
import uuid
from pathlib import Path

from PyQt5.QtCore import QObject, Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView  # noqa: F401 — init WebEngine before QApplication
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox

from models.datapoint import DataPoint
from ui.main_window import MainWindow
from utils.dataset_ops import (
    SortField,
    filter_points,
    max_value,
    sort_points,
)
from utils.parser import parse_csv, parse_json, parse_value_field

DEMO_MAP_POINTS: list[dict[str, object]] = [
    {"id": "1", "city": "London", "lat": 51.5, "lng": -0.09, "value": 80},
    {"id": "2", "city": "New York", "lat": 40.7, "lng": -74.0, "value": 60},
]


def load_stylesheet() -> str:
    qss_path = Path(__file__).resolve().parent / "ui" / "styles.qss"
    return qss_path.read_text(encoding="utf-8")


class AppController(QObject):
    """
    ``self.data`` = full dataset; ``_filtered`` = filtered/sorted view.

    Sidebar updates both map and table via ``_apply_filters_and_update_map``.
    """

    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self._window = window
        self.data: list[DataPoint] = []
        self._filtered: list[DataPoint] = []
        self.selected_point_id: str | None = None
        self._syncing_table_from_map = False

        wv = window.web_view
        if wv is not None:
            wv.loadFinished.connect(self._on_map_load_finished)

        bridge = window.map_bridge
        if bridge is not None:
            bridge.pointSelected.connect(self._on_map_marker_clicked)

        sb = window.left_sidebar
        sb.edit_search.textChanged.connect(lambda *_: self._apply_filters_and_update_map())
        sb.slider_filter.valueChanged.connect(lambda *_: self._apply_filters_and_update_map())
        sb.combo_sort.currentIndexChanged.connect(lambda *_: self._apply_filters_and_update_map())
        sb.btn_upload_file.clicked.connect(self._on_file_upload)
        sb.btn_add_manual.clicked.connect(self._on_add_manual)
        sb.btn_export_filtered.clicked.connect(self._export_filtered)

        sm = window.data_table.selectionModel()
        if sm is not None:
            sm.selectionChanged.connect(self._on_table_selection_changed)

    @property
    def filtered_dataset(self) -> list[DataPoint]:
        return list(self._filtered)

    def _on_map_load_finished(self, ok: bool) -> None:
        if not ok:
            return
        print("Map loaded")
        self._apply_filters_and_update_map()
        if not self.data:
            self._window.send_map_dataset(DEMO_MAP_POINTS, None)
            self._window.label_record_count.setText("2 Demo Points (no dataset loaded)")

    def _sort_field_and_desc(self) -> tuple[SortField, bool]:
        idx = self._window.left_sidebar.combo_sort.currentIndex()
        if idx == 0:
            return ("value", True)
        if idx == 1:
            return ("value", False)
        if idx == 2:
            return ("city", False)
        return ("city", True)

    def _update_table(self) -> None:
        """Rebuild directory rows from ``self._filtered`` only."""
        self._window.data_table.set_filtered_points(self._filtered)

    def _apply_filters_and_update_map(self) -> None:
        search = self._window.left_sidebar.edit_search.text()
        min_val = float(self._window.left_sidebar.slider_filter.value())
        field, descending = self._sort_field_and_desc()

        filtered = filter_points(
            self.data,
            search_query=search,
            min_value=min_val,
        )
        filtered = sort_points(filtered, field, descending=descending)
        self._filtered = filtered

        self._window.label_record_count.setText(f"{len(filtered):,} Records Found")
        self._window.left_sidebar.update_empty_hint(
            has_data=bool(self.data),
            filtered_count=len(filtered),
        )

        if self.selected_point_id is not None and not any(
            p.id == self.selected_point_id for p in filtered
        ):
            self.selected_point_id = None

        self._update_table()

        self._window.send_map_dataset(
            [p.to_dict() for p in filtered],
            self.selected_point_id,
        )

        if self.selected_point_id is not None:
            self._syncing_table_from_map = True
            try:
                self._window.data_table.select_row_by_id(self.selected_point_id)
            finally:
                self._syncing_table_from_map = False

    def _after_dataset_change(self) -> None:
        self._window.left_sidebar.set_filter_slider_maximum_from_dataset(max_value(self.data))
        self._apply_filters_and_update_map()

    def _on_file_upload(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self._window,
            "Open dataset",
            "",
            "CSV (*.csv);;JSON (*.json)",
        )
        if not path:
            return
        try:
            if path.lower().endswith(".csv"):
                new_pts = parse_csv(path)
            else:
                new_pts = parse_json(path)
        except OSError as exc:
            QMessageBox.warning(self._window, "File error", str(exc))
            return
        if not new_pts:
            QMessageBox.information(
                self._window,
                "No data",
                "No valid rows were found in this file.",
            )
            return
        self.data = new_pts
        self._after_dataset_change()

    def _export_filtered(self) -> None:
        if not self._filtered:
            QMessageBox.information(
                self._window,
                "Export",
                "No rows to export. Adjust filters or add data.",
            )
            return
        path, selected_filter = QFileDialog.getSaveFileName(
            self._window,
            "Export filtered dataset",
            "",
            "CSV (*.csv);;JSON (*.json)",
        )
        if not path:
            return
        lower = path.lower()
        if lower.endswith(".json"):
            as_json = True
        elif lower.endswith(".csv"):
            as_json = False
        else:
            as_json = "JSON" in (selected_filter or "")
            path = path + (".json" if as_json else ".csv")
        try:
            if as_json:
                payload = [p.to_dict() for p in self._filtered]
                Path(path).write_text(
                    json.dumps(payload, indent=2),
                    encoding="utf-8",
                )
            else:
                with Path(path).open("w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(["id", "city", "lat", "lng", "value"])
                    for p in self._filtered:
                        w.writerow([p.id, p.city, p.lat, p.lng, p.value])
        except OSError as exc:
            QMessageBox.warning(self._window, "Export failed", str(exc))

    def _on_add_manual(self) -> None:
        city = self._window.left_sidebar.edit_city.text().strip()
        lat_s = self._window.left_sidebar.edit_lat.text().strip()
        lng_s = self._window.left_sidebar.edit_lng.text().strip()
        val_s = self._window.left_sidebar.edit_value.text().strip()
        if not city:
            QMessageBox.warning(self._window, "Input error", "City is required.")
            return
        try:
            lat = float(lat_s)
            lng = float(lng_s)
        except ValueError:
            QMessageBox.warning(
                self._window,
                "Input error",
                "Latitude and longitude must be valid numbers.",
            )
            return
        val = parse_value_field(val_s)
        if val is None:
            QMessageBox.warning(
                self._window,
                "Input error",
                "Value must be a number (e.g. 42 or 82%).",
            )
            return
        self.data.append(
            DataPoint(
                id=uuid.uuid4().hex[:12],
                city=city,
                lat=lat,
                lng=lng,
                value=val,
            )
        )
        self._after_dataset_change()

    def _on_map_marker_clicked(self, marker_id: str) -> None:
        print(f"[App] selectedPointId = {marker_id}")
        self.selected_point_id = marker_id
        self._syncing_table_from_map = True
        try:
            self._window.data_table.select_row_by_id(marker_id)
        finally:
            self._syncing_table_from_map = False
        self._window.highlight_marker_on_map(marker_id, fly=False)

    def _on_table_selection_changed(self, selected, deselected) -> None:
        """Table → map: highlight marker when user selects a row."""
        if self._syncing_table_from_map:
            return
        sm = self._window.data_table.selectionModel()
        if sm is None:
            return
        rows = sm.selectedRows()
        if not rows:
            self.selected_point_id = None
            self._window.highlight_marker_on_map("", fly=False)
            return
        row = rows[0].row()
        id_item = self._window.data_table.item(row)
        if id_item is None:
            return
        rid = id_item.data(Qt.UserRole)
        if rid is None:
            return
        rid_str = str(rid)
        self.selected_point_id = rid_str
        self._window.highlight_marker_on_map(rid_str, fly=True)


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(load_stylesheet())

    window = MainWindow()
    AppController(window)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
