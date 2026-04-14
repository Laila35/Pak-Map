"""Left sidebar: data ingestion, file upload, manual entry, filter/search placeholders."""

from __future__ import annotations

import math

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QScroller,
    QSlider,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class LeftSidebar(QWidget):
    """
    Left panel content (branding, file + manual ingest, search/filter/sort placeholders).

    Widgets are exposed for later wiring; no signals connected here.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("leftSidebarRoot")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("sidebarScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setSizeAdjustPolicy(QScrollArea.AdjustIgnored)

        inner = QWidget()
        inner.setObjectName("sidebarScrollInner")
        inner.setMinimumWidth(260)
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 8, 24, 24)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignTop)

        # --- Data ingestion ---
        ingest_title = QLabel("DATA INGESTION")
        ingest_title.setObjectName("sectionTitle")
        layout.addWidget(ingest_title)

        upload_lbl = QLabel("File upload")
        upload_lbl.setObjectName("microLabel")
        layout.addWidget(upload_lbl)

        self.btn_upload_file = QPushButton("SELECT CSV / JSON")
        self.btn_upload_file.setObjectName("btnElite")
        self.btn_upload_file.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_upload_file)

        layout.addSpacing(4)

        manual_lbl = QLabel("Manual entry")
        manual_lbl.setObjectName("microLabel")
        layout.addWidget(manual_lbl)

        city_lbl = QLabel("City")
        city_lbl.setObjectName("microLabel")
        layout.addWidget(city_lbl)
        self.edit_city = QLineEdit()
        self.edit_city.setObjectName("lineEditElite")
        self.edit_city.setPlaceholderText("e.g. New York")
        layout.addWidget(self.edit_city)

        row = QHBoxLayout()
        row.setSpacing(12)
        lat_wrap = QVBoxLayout()
        lat_lbl = QLabel("Latitude")
        lat_lbl.setObjectName("microLabel")
        self.edit_lat = QLineEdit()
        self.edit_lat.setObjectName("lineEditElite")
        self.edit_lat.setPlaceholderText("40.7128")
        lat_wrap.addWidget(lat_lbl)
        lat_wrap.addWidget(self.edit_lat)
        lng_wrap = QVBoxLayout()
        lng_lbl = QLabel("Longitude")
        lng_lbl.setObjectName("microLabel")
        self.edit_lng = QLineEdit()
        self.edit_lng.setObjectName("lineEditElite")
        self.edit_lng.setPlaceholderText("-74.0060")
        lng_wrap.addWidget(lng_lbl)
        lng_wrap.addWidget(self.edit_lng)
        row.addLayout(lat_wrap)
        row.addLayout(lng_wrap)
        layout.addLayout(row)

        val_lbl = QLabel("Value")
        val_lbl.setObjectName("microLabel")
        layout.addWidget(val_lbl)
        self.edit_value = QLineEdit()
        self.edit_value.setObjectName("lineEditElite")
        self.edit_value.setPlaceholderText("0 or 82%")
        layout.addWidget(self.edit_value)

        self.btn_add_manual = QPushButton("ADD RECORD")
        self.btn_add_manual.setObjectName("btnElite")
        self.btn_add_manual.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_add_manual)

        # --- Placeholder: search ---
        layout.addSpacing(8)
        sep1 = QFrame()
        sep1.setObjectName("dirSeparator")
        sep1.setFrameShape(QFrame.HLine)
        layout.addWidget(sep1)

        search_title = QLabel("SEARCH INDEX")
        search_title.setObjectName("microLabelAccent")
        layout.addWidget(search_title)

        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        search_row.setContentsMargins(0, 0, 0, 0)

        self.edit_search = QLineEdit()
        self.edit_search.setObjectName("lineEditElite")
        self.edit_search.setPlaceholderText("Search by city name…")
        search_row.addWidget(self.edit_search, stretch=1)

        # Use a non-emoji glyph so the color is controlled by QSS (emoji can render blue).
        self.btn_search_city = QPushButton("⌕")
        self.btn_search_city.setObjectName("btnSearchIcon")
        self.btn_search_city.setCursor(Qt.PointingHandCursor)
        self.btn_search_city.setToolTip("Search city on map")
        self.btn_search_city.setFixedSize(36, 34)
        search_row.addWidget(self.btn_search_city, stretch=0)

        layout.addLayout(search_row)

        # --- Placeholder: filter slider ---
        filter_title = QLabel("VALUE THRESHOLD")
        filter_title.setObjectName("microLabelAccent")
        layout.addWidget(filter_title)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self._label_filter_min = QLabel("0")
        self._label_filter_min.setObjectName("microLabel")
        self.slider_filter = QSlider(Qt.Horizontal)
        self.slider_filter.setObjectName("sliderFilter")
        self.slider_filter.setRange(0, 100)
        self.slider_filter.setValue(0)
        self._label_filter_max = QLabel("100")
        self._label_filter_max.setObjectName("microLabel")
        filter_row.addWidget(self._label_filter_min)
        filter_row.addWidget(self.slider_filter, stretch=1)
        filter_row.addWidget(self._label_filter_max)
        layout.addLayout(filter_row)

        # --- Placeholder: sort ---
        sort_title = QLabel("DATA ORDERING")
        sort_title.setObjectName("microLabelAccent")
        layout.addWidget(sort_title)

        self.combo_sort = QComboBox()
        self.combo_sort.setObjectName("comboElite")
        self.combo_sort.addItems(
            [
                "Value (high → low)",
                "Value (low → high)",
                "City (A → Z)",
                "City (Z → A)",
            ]
        )
        self.combo_sort.setCurrentIndex(0)
        layout.addWidget(self.combo_sort)

        self.label_empty_hint = QLabel()
        self.label_empty_hint.setObjectName("sidebarEmptyHint")
        self.label_empty_hint.setWordWrap(True)
        self.label_empty_hint.setVisible(False)
        layout.addWidget(self.label_empty_hint)

        self.btn_export_filtered = QPushButton("EXPORT FILTERED (CSV / JSON)")
        self.btn_export_filtered.setObjectName("btnElite")
        self.btn_export_filtered.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_export_filtered)

        layout.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        QScroller.grabGesture(
            scroll.viewport(),
            QScroller.LeftMouseButtonGesture,
        )

    def set_filter_slider_maximum_from_dataset(self, max_value: float) -> None:
        """Scale slider to ``[0, max]`` from dataset; empty data resets to 0–100."""
        self.slider_filter.blockSignals(True)
        if max_value <= 0:
            self.slider_filter.setMaximum(100)
            self.slider_filter.setValue(0)
            self._label_filter_max.setText("100")
        else:
            top = max(1, int(math.ceil(max_value)))
            self.slider_filter.setMaximum(top)
            if self.slider_filter.value() > top:
                self.slider_filter.setValue(top)
            self._label_filter_max.setText(f"{top:,}")
        self.slider_filter.blockSignals(False)

    def update_empty_hint(self, *, has_data: bool, filtered_count: int) -> None:
        """Show contextual copy when filters exclude all rows or no data is loaded."""
        if not has_data:
            self.label_empty_hint.setText(
                "Load CSV/JSON or use manual entry to add records."
            )
            self.label_empty_hint.setVisible(True)
        elif filtered_count == 0:
            self.label_empty_hint.setText("No records found — adjust search, threshold, or sort.")
            self.label_empty_hint.setVisible(True)
        else:
            self.label_empty_hint.setVisible(False)
