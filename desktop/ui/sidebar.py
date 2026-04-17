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
    QStackedWidget,
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
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignTop)

        # --- Data ingestion ---
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 8)
        ingest_title = QLabel("DATA INGESTION")
        ingest_title.setObjectName("sectionTitle")
        header_row.addWidget(ingest_title)
        layout.addLayout(header_row)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(0)
        self.btn_tab_file = QPushButton("FILE\nUPLOAD")
        self.btn_tab_file.setObjectName("btnTabActive")
        self.btn_tab_file.setCursor(Qt.PointingHandCursor)
        self.btn_tab_manual = QPushButton("MANUAL\nENTRY")
        self.btn_tab_manual.setObjectName("btnTabInactive")
        self.btn_tab_manual.setCursor(Qt.PointingHandCursor)
        tab_row.addWidget(self.btn_tab_file)
        tab_row.addWidget(self.btn_tab_manual)
        layout.addLayout(tab_row)

        self.ingest_stack = QStackedWidget()
        self.ingest_stack.setObjectName("ingestStack")
        layout.addWidget(self.ingest_stack)

        # Upload Page
        upload_page = QWidget()
        upload_layout = QVBoxLayout(upload_page)
        upload_layout.setContentsMargins(0, 16, 0, 0)
        upload_layout.addStretch()
        self.btn_upload_file = QPushButton()
        self.btn_upload_file.setObjectName("btnUploadArea")
        self.btn_upload_file.setCursor(Qt.PointingHandCursor)
        self.btn_upload_file.setMinimumHeight(160)
        
        btn_layout = QVBoxLayout(self.btn_upload_file)
        btn_layout.setAlignment(Qt.AlignCenter)
        btn_layout.setSpacing(12)
        
        icon_wrap = QVBoxLayout()
        icon_wrap.setSpacing(2)
        icon_wrap.setAlignment(Qt.AlignCenter)
        lbl_arrow = QLabel("↑")
        lbl_arrow.setObjectName("uploadIconArrow")
        lbl_arrow.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        lbl_arrow.setAttribute(Qt.WA_TransparentForMouseEvents)
        lbl_bracket = QLabel()
        lbl_bracket.setObjectName("uploadIconBracket")
        lbl_bracket.setFixedSize(22, 5)
        lbl_bracket.setAttribute(Qt.WA_TransparentForMouseEvents)
        icon_wrap.addWidget(lbl_arrow)
        icon_wrap.addWidget(lbl_bracket)
        
        lbl_title = QLabel("Select or drop file")
        lbl_title.setObjectName("uploadTitle")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        lbl_sub = QLabel("CSV / JSON SUPPORTED")
        lbl_sub.setObjectName("uploadSub")
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        btn_layout.addLayout(icon_wrap)
        btn_layout.addWidget(lbl_title)
        btn_layout.addWidget(lbl_sub)
        
        upload_layout.addWidget(self.btn_upload_file)
        upload_layout.addStretch()
        self.ingest_stack.addWidget(upload_page)

        # Manual Page
        manual_page = QWidget()
        manual_layout = QVBoxLayout(manual_page)
        manual_layout.setContentsMargins(0, 16, 0, 0)
        manual_layout.setSpacing(6)

        city_lbl = QLabel("CITY")
        city_lbl.setObjectName("microLabel")
        self.edit_city = QLineEdit()
        self.edit_city.setObjectName("lineEditElite")
        self.edit_city.setPlaceholderText("Type city name here...")
        manual_layout.addWidget(city_lbl)
        manual_layout.addWidget(self.edit_city)
        
        addr_lbl = QLabel("ADDRESS")
        addr_lbl.setObjectName("microLabel")
        self.edit_address = QLineEdit()
        self.edit_address.setObjectName("lineEditElite")
        self.edit_address.setPlaceholderText("Type address here...")
        manual_layout.addWidget(addr_lbl)
        manual_layout.addWidget(self.edit_address)

        row = QHBoxLayout()
        row.setSpacing(12)
        lat_wrap = QVBoxLayout()
        lat_wrap.setSpacing(4)
        lat_lbl = QLabel("LATITUDE")
        lat_lbl.setObjectName("microLabel")
        self.edit_lat = QLineEdit()
        self.edit_lat.setObjectName("lineEditElite")
        self.edit_lat.setPlaceholderText("Enter latitude...")
        lat_wrap.addWidget(lat_lbl)
        lat_wrap.addWidget(self.edit_lat)
        
        lng_wrap = QVBoxLayout()
        lng_wrap.setSpacing(4)
        lng_lbl = QLabel("LONGITUDE")
        lng_lbl.setObjectName("microLabel")
        self.edit_lng = QLineEdit()
        self.edit_lng.setObjectName("lineEditElite")
        self.edit_lng.setPlaceholderText("Enter longitude...")
        lng_wrap.addWidget(lng_lbl)
        lng_wrap.addWidget(self.edit_lng)
        row.addLayout(lat_wrap)
        row.addLayout(lng_wrap)
        manual_layout.addLayout(row)

        val_lbl = QLabel("POPULATION")
        val_lbl.setObjectName("microLabel")
        self.edit_value = QLineEdit()
        self.edit_value.setObjectName("lineEditElite")
        self.edit_value.setPlaceholderText("Enter population value...")
        manual_layout.addWidget(val_lbl)
        manual_layout.addWidget(self.edit_value)
        
        manual_layout.addSpacing(4)
        
        self.btn_add_manual = QPushButton("+ APPEND RECORD")
        self.btn_add_manual.setObjectName("btnAppendRecord")
        self.btn_add_manual.setCursor(Qt.PointingHandCursor)
        manual_layout.addWidget(self.btn_add_manual)
        
        self.ingest_stack.addWidget(manual_page)
        
        # Connect tabs
        self.btn_tab_file.clicked.connect(lambda: self._switch_ingest_tab(0))
        self.btn_tab_manual.clicked.connect(lambda: self._switch_ingest_tab(1))

        # --- Search Index (city + POI search) ---
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
        self.edit_search.setPlaceholderText("Search for a city or location...")
        search_row.addWidget(self.edit_search, stretch=1)

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

    def _switch_ingest_tab(self, index: int) -> None:
        self.ingest_stack.setCurrentIndex(index)
        if index == 0:
            self.btn_tab_file.setObjectName("btnTabActive")
            self.btn_tab_manual.setObjectName("btnTabInactive")
        else:
            self.btn_tab_file.setObjectName("btnTabInactive")
            self.btn_tab_manual.setObjectName("btnTabActive")
        
        self.btn_tab_file.style().unpolish(self.btn_tab_file)
        self.btn_tab_file.style().polish(self.btn_tab_file)
        self.btn_tab_manual.style().unpolish(self.btn_tab_manual)
        self.btn_tab_manual.style().polish(self.btn_tab_manual)

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
