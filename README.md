# DeepDive (datamap-explorer)

Desktop app for visualizing geographic records on a **satellite map** with a **PyQt** UI: ingest CSV/JSON, filter, sort, and sync a **directory list** with **Leaflet** markers.

## Tech stack (source of truth)

| Piece | Technology |
|--------|------------|
| Runtime | **Python 3.10+** (type hints) |
| Desktop UI | **PyQt5** + **QSS** (`ui/styles.qss`) |
| Embedded map | **PyQtWebEngine** → `map/index.html` |
| Map library | **Leaflet 1.9** (CDN) |
| Basemap | **Esri World Imagery** |
| Bridge | **Qt WebChannel** + `qwebchannel.js` |
| Data model | **`dataclasses`** — `models/datapoint.py` |
| Formats | **CSV / JSON** — `utils/parser.py` |

There is **no** React/Vite/Next.js app in this repo; run the desktop entrypoint only.

## Run

```bash
cd datamap-explorer
python -m venv venv
venv\Scripts\activate
pip install -r requirements-pyqt.txt
python main.py
```

(On macOS/Linux: `source venv/bin/activate`.)

## Layout

- `main.py` — `AppController`, filters, table/map sync
- `ui/` — windows, sidebar, directory list, map bridge, styles
- `map/index.html` — Leaflet + Esri tiles + JS API used from Python
- `utils/` — parsing and filter/sort helpers
- `models/` — `DataPoint`

## Data shape (CSV / JSON)

Each row/object should include **`city`**, **`lat`**, **`lng`**, **`value`**. An **`id`** may be present or generated on import.

```json
[
  { "city": "New York", "lat": 40.7128, "lng": -74.0060, "value": 8400000 }
]
```

```csv
city,lat,lng,value
New York,40.7128,-74.0060,8400000
```
