"""Application entry point: sidebar → ``self.data`` → filtered → map + table."""

from __future__ import annotations

import csv
import json
import sys
import threading
import uuid
from pathlib import Path

from PyQt5.QtCore import QCoreApplication, QObject, Qt
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
from utils.parser import is_in_pakistan_bbox, parse_csv, parse_json, parse_value_field
from utils.boundaries import load_boundary_geojson_for_city, save_boundary_geojson_for_city
from utils.boundary_fetch import (
    boundary_covers_points,
    fetch_city_boundary_geojson,
    generate_fallback_polygon,
)
from utils.geocode import geocode_pk_query


def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path.cwd()))
    return Path(__file__).resolve().parent


def load_stylesheet() -> str:
    qss_path = _resource_root() / "ui" / "styles.qss"
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
        self._boundary_inflight: set[str] = set()

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
        if hasattr(sb, "btn_search_city"):
            sb.btn_search_city.clicked.connect(self._on_search_clicked)
        # Magnifier button removed: allow pressing Enter in the search box.
        sb.edit_search.returnPressed.connect(self._on_search_clicked)

        sm = window.data_table.selectionModel()
        if sm is not None:
            sm.selectionChanged.connect(self._on_table_selection_changed)

        if hasattr(window, "edit_directory_filter") and window.edit_directory_filter is not None:
            window.edit_directory_filter.textChanged.connect(lambda *_: self._update_table())

    @property
    def filtered_dataset(self) -> list[DataPoint]:
        return list(self._filtered)

    def _on_map_load_finished(self, ok: bool) -> None:
        if not ok:
            return
        print("Map loaded")
        self._apply_filters_and_update_map()

    def _sort_field_and_desc(self) -> tuple[SortField, bool]:
        idx = self._window.left_sidebar.combo_sort.currentIndex()
        if idx == 0:
            return ("value", True)
        if idx == 1:
            return ("value", False)
        if idx == 2:
            return ("city", False)
        return ("city", True)

    def _on_search_clicked(self) -> None:
        """Fly the map to a free-text Pakistan query (city or POI)."""
        query = self._window.left_sidebar.edit_search.text().strip()
        if not query:
            return

        def worker() -> None:
            hit = geocode_pk_query(query)
            if hit is None:
                return
            lat, lng, _display = hit

            def apply_on_ui() -> None:
                try:
                    if self._window.web_view is not None:
                        self._window.web_view.page().runJavaScript(
                            f"typeof flyToLocation === 'function' && flyToLocation({lat}, {lng}, 14);"
                        )
                        # Also drop a temporary "search result" marker with a rich popup (image + details).
                        safe_q = json.dumps(query)
                        self._window.web_view.page().runJavaScript(
                            f"typeof showSearchResult === 'function' && showSearchResult({lat}, {lng}, {safe_q}, '');"
                        )
                except Exception:
                    pass

                # If the query exactly matches a city that exists in the dataset,
                # refresh that city's boundary outline.
                city_key = query.strip().lower()
                city_match = next(
                    (p.city for p in self.data if (p.city or "").strip().lower() == city_key),
                    "",
                )
                if city_match:
                    self._update_boundary_for_city_search(city_match, float(lat), float(lng), query)

            try:
                from PyQt5.QtCore import QTimer

                QTimer.singleShot(0, apply_on_ui)
            except Exception:
                apply_on_ui()

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _city_key(p: DataPoint) -> str:
        c = (p.city or "").strip().lower()
        return c if c else p.id

    def _map_points_for_display(self, filtered: list[DataPoint], search: str) -> list[DataPoint]:
        """
        Clean map when nothing to show: no CSV → none; else pins for:
        - the directory-selected row (always, if that row is in the current filter), and
        - the rest of the filtered dataset (so the map is always populated).
        """
        if not self.data:
            return []
        if search.strip():
            # In search mode, show the actual matching results (places inside cities).
            limit = 700
            out = list(filtered[:limit])
            return out

        # No active search: keep map populated with the top chunk.
        limit = 900
        out = list(filtered[:limit])
        if self.selected_point_id:
            sel_pt = next((p for p in filtered if p.id == self.selected_point_id), None)
            if sel_pt is not None and all(p.id != sel_pt.id for p in out):
                out.insert(0, sel_pt)
        return out

    def _sync_map_and_boundary(self, filtered: list[DataPoint], search: str) -> None:
        """Push markers + city outline without rebuilding the directory table."""
        map_points = self._map_points_for_display(filtered, search)
        map_sel = self._map_selection_id_for_pins(map_points, filtered)
        self._window.send_map_dataset(
            [p.to_dict() for p in map_points],
            map_sel,
        )
        if self.selected_point_id is not None:
            self._update_boundary_for_selected()
        else:
            # No selection → do not keep stale outlines.
            self._window.set_city_boundary(None)

    def _update_boundary_for_city_search(self, city: str, lat: float, lng: float, search: str) -> None:
        """Outline boundary while user is searching (without selecting a specific point)."""
        city_points_now = [
            (float(p.lat), float(p.lng))
            for p in self.data
            if (p.city or "").strip().lower() == (city or "").strip().lower()
        ]
        gj = load_boundary_geojson_for_city(city)
        if gj is not None:
            # If cached boundary doesn't actually cover the city's points, refresh it.
            if not city_points_now or boundary_covers_points(gj, city_points_now, min_fraction=0.85):
                self._window.set_city_boundary(gj, fit=True)
                return

        self._window.set_city_boundary(None)
        city_key = city.strip().lower()
        if not city_key or city_key in self._boundary_inflight:
            return
        self._boundary_inflight.add(city_key)

        search_key_at_start = search.strip().lower()

        def worker() -> None:
            fetched = None
            try:
                city_points = city_points_now
                fetched = fetch_city_boundary_geojson(
                    city,
                    points_latlng=city_points or None,
                    fallback_center=(lat, lng),
                )
                if fetched is None:
                    fetched = generate_fallback_polygon(lat, lng, radius_km=4.0)
                if fetched is not None:
                    save_boundary_geojson_for_city(city, fetched)
            finally:
                def apply_if_still_searching() -> None:
                    self._boundary_inflight.discard(city_key)
                    # If user selected something since, do not override selection outline.
                    if self.selected_point_id is not None:
                        return
                    cur_search = self._window.left_sidebar.edit_search.text().strip().lower()
                    if cur_search != search_key_at_start:
                        return
                    fresh = load_boundary_geojson_for_city(city) or fetched
                    if fresh is not None:
                        self._window.set_city_boundary(fresh, fit=True)

                try:
                    from PyQt5.QtCore import QTimer

                    QTimer.singleShot(0, apply_if_still_searching)
                except Exception:
                    apply_if_still_searching()

        threading.Thread(target=worker, daemon=True).start()

    def _map_selection_id_for_pins(
        self, map_points: list[DataPoint], filtered: list[DataPoint]
    ) -> str | None:
        """Highlight the on-map pin when the table row matches that pin or same city."""
        if self.selected_point_id is None:
            return None
        on_map = {p.id for p in map_points}
        if self.selected_point_id in on_map:
            return self.selected_point_id
        selected = next((p for p in filtered if p.id == self.selected_point_id), None)
        if selected is None:
            return None
        key = self._city_key(selected)
        for p in map_points:
            if self._city_key(p) == key:
                return p.id
        return None

    def _update_table(self) -> None:
        """Rebuild directory rows from ``self._filtered`` only."""
        pts = list(self._filtered)
        q = ""
        if hasattr(self._window, "edit_directory_filter") and self._window.edit_directory_filter is not None:
            q = self._window.edit_directory_filter.text().strip().lower()
        if q:
            pts = [p for p in pts if q in (p.city or "").strip().lower()]
        self._window.data_table.set_filtered_points(pts)

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
            self._window.set_city_boundary(None)

        self._update_table()

        if self.selected_point_id is not None:
            self._syncing_table_from_map = True
            try:
                self._window.data_table.select_row_by_id(self.selected_point_id)
            finally:
                self._syncing_table_from_map = False

        self._sync_map_and_boundary(filtered, search)

    def _selected_point(self) -> DataPoint | None:
        if not self.selected_point_id:
            return None
        for p in self.data:
            if p.id == self.selected_point_id:
                return p
        return None

    def _update_boundary_for_selected(self) -> None:
        p = self._selected_point()
        if p is None:
            self._window.set_city_boundary(None)
            return
        # No strict polygon validation here (per your request to remove that recent change).
        city_points_now = [
            (float(pp.lat), float(pp.lng))
            for pp in self.data
            if (pp.city or "").strip().lower() == (p.city or "").strip().lower()
        ]
        gj = load_boundary_geojson_for_city(p.city)
        if gj is not None:
            if not city_points_now or boundary_covers_points(gj, city_points_now, min_fraction=0.85):
                self._window.set_city_boundary(gj, fit=True)
                return

        self._window.set_city_boundary(None)
        city_key = p.city.strip().lower()
        if not city_key or city_key in self._boundary_inflight:
            return
        self._boundary_inflight.add(city_key)

        selected_id_at_start = self.selected_point_id
        city_at_start = p.city
        lat_at_start = float(p.lat)
        lng_at_start = float(p.lng)

        def worker() -> None:
            fetched = None
            try:
                city_points = city_points_now
                fetched = fetch_city_boundary_geojson(
                    city_at_start,
                    points_latlng=city_points or None,
                    fallback_center=(lat_at_start, lng_at_start),
                )
                if fetched is None:
                    fetched = generate_fallback_polygon(lat_at_start, lng_at_start, radius_km=4.0)
                if fetched is not None:
                    save_boundary_geojson_for_city(city_at_start, fetched)
            finally:
                def apply_if_still_selected() -> None:
                    self._boundary_inflight.discard(city_key)
                    if self.selected_point_id != selected_id_at_start:
                        return
                    fresh = load_boundary_geojson_for_city(city_at_start) or fetched
                    self._window.set_city_boundary(fresh, fit=True) if fresh is not None else None

                try:
                    from PyQt5.QtCore import QTimer

                    QTimer.singleShot(0, apply_if_still_selected)
                except Exception:
                    apply_if_still_selected()

        threading.Thread(target=worker, daemon=True).start()

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
                    w.writerow(
                        [
                            "id",
                            "city",
                            "lat",
                            "lng",
                            "value",
                            "place_type",
                            "place_name",
                            "description",
                            "image_url",
                            "image_url_2",
                            "address",
                            "rating",
                            "reviews",
                            "hours",
                            "open_status",
                            "website",
                            "sponsored",
                        ]
                    )
                    for p in self._filtered:
                        w.writerow(
                            [
                                p.id,
                                p.city,
                                p.lat,
                                p.lng,
                                p.value,
                                p.place_type,
                                p.place_name,
                                p.description,
                                p.image_url,
                                p.image_url_2,
                                p.address,
                                p.rating,
                                p.reviews,
                                p.hours,
                                p.open_status,
                                p.website,
                                p.sponsored,
                            ]
                        )
        except OSError as exc:
            QMessageBox.warning(self._window, "Export failed", str(exc))

    def _on_add_manual(self) -> None:
        city = self._window.left_sidebar.edit_city.text().strip()
        address = self._window.left_sidebar.edit_address.text().strip()
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
        if not is_in_pakistan_bbox(lat, lng):
            QMessageBox.warning(
                self._window,
                "Pakistan only",
                "This app is configured for Pakistan-only locations.\n"
                "Please enter coordinates within Pakistan (including ex-FATA regions).",
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
                place_name=city,
                address=address,
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
        search = self._window.left_sidebar.edit_search.text()
        self._sync_map_and_boundary(self._filtered, search)
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
            search = self._window.left_sidebar.edit_search.text()
            self._sync_map_and_boundary(self._filtered, search)
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
        search = self._window.left_sidebar.edit_search.text()
        self._sync_map_and_boundary(self._filtered, search)
        self._window.highlight_marker_on_map(rid_str, fly=True)


def main() -> None:
    # Sharper map tiles / UI on high-DPI displays (fixes blurry Leaflet when zooming).
    try:
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except Exception:
        pass
    app = QApplication(sys.argv)
    app.setStyleSheet(load_stylesheet())

    window = MainWindow()
    AppController(window)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
