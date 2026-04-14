"""Main application window — layout and QSS-driven styling."""

from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWebEngineWidgets import QWebEngineSettings, QWebEngineView
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QSizePolicy,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from map_config import map_boot_json

from ui.directory_list import DirectoryListWidget
from ui.map_bridge import MapBridge
from ui.sidebar import LeftSidebar

_MAP_INDEX = Path(__file__).resolve().parent.parent / "map" / "index.html"


def _map_page_html_with_config() -> tuple[str, QUrl]:
    """Inline ``window.__MAP_CONFIG__`` so the map script sees keys before it runs."""
    raw = _MAP_INDEX.read_text(encoding="utf-8")
    cfg = json.dumps(map_boot_json(), separators=(",", ":"))
    inject = f"<script>window.__MAP_CONFIG__={cfg};</script>\n"
    if "</head>" in raw:
        html = raw.replace("</head>", inject + "</head>", 1)
    else:
        html = inject + raw
    map_dir = _MAP_INDEX.parent.resolve()
    base_path = str(map_dir)
    if not base_path.endswith(os.sep):
        base_path += os.sep
    return html, QUrl.fromLocalFile(base_path)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DEEPDIVE")
        self.setMinimumSize(900, 600)

        central = QWidget()
        central.setObjectName("mainCentral")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(10, 12, 10, 12)
        root.setSpacing(10)

        self._web_view: QWebEngineView | None = None
        self._map_bridge: MapBridge | None = None

        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("mainSplitter")
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)

        left = self._build_left_panel()
        center = self._build_center_panel()
        right = self._build_right_panel()

        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        # Reasonable defaults that still allow the user to resize/collapse.
        splitter.setSizes([320, 900, 420])
        root.addWidget(splitter, stretch=1)

    def _build_left_panel(self) -> QFrame:
        glass = QFrame()
        glass.setObjectName("glassPanelLeft")
        glass.setMinimumWidth(260)
        glass.setMaximumWidth(420)
        glass.setFrameShape(QFrame.NoFrame)
        glass.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        layout = QVBoxLayout(glass)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("leftPanelHeader")
        head_lay = QVBoxLayout(header)
        head_lay.setContentsMargins(24, 22, 24, 18)
        head_lay.setSpacing(0)

        row = QHBoxLayout()
        row.setSpacing(16)
        row.setContentsMargins(0, 0, 0, 0)

        compass = QLabel("✧")
        compass.setObjectName("compassRing")
        compass.setAlignment(Qt.AlignCenter)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_col.setContentsMargins(0, 0, 0, 0)

        brand = QLabel()
        brand.setObjectName("titleBrand")
        brand.setTextFormat(Qt.RichText)
        brand.setText(
            "<span style='color:#f5f2ed;'>DEEP</span>"
            "<span style='color:#D4AF37;font-style:italic;'>DIVE</span>"
        )

        sub = QLabel("Global Intelligence Mapping")
        sub.setObjectName("microLabel")

        title_col.addWidget(brand)
        title_col.addSpacing(14)
        title_col.addWidget(sub)

        row.addWidget(compass, 0, Qt.AlignTop)
        row.addLayout(title_col, 1)
        head_lay.addLayout(row)

        layout.addWidget(header)

        self.left_sidebar = LeftSidebar()
        layout.addWidget(self.left_sidebar, stretch=1)
        return glass

    def _build_center_panel(self) -> QFrame:
        outer = QFrame()
        outer.setObjectName("mapOuter")
        outer.setFrameShape(QFrame.NoFrame)

        outer_l = QVBoxLayout(outer)
        outer_l.setContentsMargins(0, 0, 0, 0)
        outer_l.setSpacing(0)

        map_frame = QFrame()
        map_frame.setObjectName("mapFrame")
        map_frame.setFrameShape(QFrame.NoFrame)

        inner = QVBoxLayout(map_frame)
        inner.setContentsMargins(0, 0, 0, 0)

        self._web_view = QWebEngineView()
        self._web_view.setObjectName("mapWebView")
        self._web_view.setStyleSheet("background-color: #e8e4e0; border: none;")
        self._web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        page = self._web_view.page()
        settings = page.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)

        self._map_bridge = MapBridge()
        channel = QWebChannel(page)
        channel.registerObject("bridge", self._map_bridge)
        page.setWebChannel(channel)

        inner.addWidget(self._web_view, stretch=1)

        html, base_url = _map_page_html_with_config()
        self._web_view.setHtml(html, base_url)

        outer_l.addWidget(map_frame, stretch=1)
        return outer

    @property
    def web_view(self) -> QWebEngineView | None:
        return self._web_view

    @property
    def map_bridge(self) -> MapBridge | None:
        return self._map_bridge

    def send_map_dataset(self, data: list, selected_id: str | None = None) -> None:
        """Python → JS: push marker payloads; ``selected_id`` keeps highlight; map fits bounds to all points."""
        if self._web_view is None:
            return
        payload = json.dumps(data)
        sel = json.dumps(selected_id)
        self._web_view.page().runJavaScript(f"addMarkers({payload}, {sel});")

    def focus_map_marker(self, marker_id: str, *, fly: bool = True) -> None:
        """Python → JS: center on marker; ``fly=False`` only opens popup (e.g. after marker rebuild)."""
        if self._web_view is None:
            return
        fly_js = "true" if fly else "false"
        self._web_view.page().runJavaScript(
            f"focusMarker({json.dumps(marker_id)}, {{ fly: {fly_js} }});"
        )

    def highlight_marker_on_map(self, marker_id: str, *, fly: bool = True) -> None:
        """Python → JS: restyle markers so ``marker_id`` is highlighted (table → map)."""
        if self._web_view is None:
            return
        fly_js = "true" if fly else "false"
        self._web_view.page().runJavaScript(
            f"highlightMarkerOnMap({json.dumps(marker_id)}, {{ fly: {fly_js} }});"
        )

    def set_city_boundary(self, geojson_obj: dict | None, *, fit: bool = True) -> None:
        """Python → JS: render a single city's boundary polygon (GeoJSON)."""
        if self._web_view is None:
            return
        if geojson_obj is None:
            self._web_view.page().runJavaScript(
                "typeof clearCityBoundary === 'function' && clearCityBoundary();"
            )
            return
        payload = json.dumps(geojson_obj)
        fit_js = "true" if fit else "false"
        self._web_view.page().runJavaScript(
            f"typeof setCityBoundary === 'function' && setCityBoundary({payload}, {{ fit: {fit_js} }});"
        )

    def _build_right_panel(self) -> QFrame:
        glass = QFrame()
        glass.setObjectName("glassPanelRight")
        glass.setMinimumWidth(320)
        glass.setMaximumWidth(560)
        glass.setFrameShape(QFrame.NoFrame)
        glass.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        layout = QVBoxLayout(glass)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("rightPanelHeader")
        head_lay = QVBoxLayout(header)
        head_lay.setContentsMargins(24, 22, 24, 18)
        head_lay.setSpacing(8)

        title = QLabel("Directory")
        title.setObjectName("titleDirectory")
        head_lay.addWidget(title)

        self.edit_directory_filter = QLineEdit()
        self.edit_directory_filter.setObjectName("lineEditElite")
        self.edit_directory_filter.setPlaceholderText("Filter directory by city…")
        head_lay.addWidget(self.edit_directory_filter)

        self.label_record_count = QLabel("0 Records Found")
        self.label_record_count.setObjectName("labelRecordCount")
        head_lay.addWidget(self.label_record_count)

        layout.addWidget(header)

        sep = QFrame()
        sep.setObjectName("dirSeparator")
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        body = QWidget()
        body_l = QVBoxLayout(body)
        body_l.setContentsMargins(24, 8, 20, 20)
        body_l.setSpacing(0)

        self.data_table = DirectoryListWidget()
        body_l.addWidget(self.data_table, stretch=1)

        layout.addWidget(body, stretch=1)

        return glass
