# Pak-Map Desktop Application

Pak-Map is a desktop application for exploring maps of Pakistan, built with PyQt5. It displays interactive maps with boundaries, markers, and points of interest (POIs) using embedded web technologies.

## Tech Stacks Used

### Backend / Desktop Framework
- **Python**: Core programming language.
- **PyQt5**: GUI framework for creating the desktop application, including QtWebEngine for rendering web content.
- **QtWebChannel**: Enables communication between Python and JavaScript in the embedded web view.

### Frontend / Web Technologies
- **HTML/CSS/JavaScript**: For the map interface.
- **Leaflet.js**: Interactive map library for displaying maps, boundaries, markers, and POIs.
- **Bootstrap.js**: Custom JavaScript for initializing the map and handling interactions.

### Utilities and Libraries
- **python-dotenv**: For loading environment variables from a .env file.
- **pathlib**: For handling file paths, especially in frozen (packaged) applications.
- **PyInstaller**: Tool for packaging the Python application into a standalone executable.

### Data Handling
- **GeoJSON Files**: Boundary data stored in `boundaries/` folder (e.g., abbottabad.geojson, lahore.geojson, etc.).
- **Datapoint Model**: Custom Python class in `models/datapoint.py` for handling map data points.
- **No Database**: The application does not use a traditional database (e.g., SQL, NoSQL). Data is loaded from local GeoJSON files and Python models.

## Prerequisites

- **Python 3.8 or higher**: Ensure Python is installed on your system.
- **Virtual Environment**: Recommended to use a virtual environment to manage dependencies.

## Step-by-Step Installation

1. **Clone or Download the Repository**:
   - Download the project files to your local machine and navigate to the `desktop/` folder.

2. **Set Up Virtual Environment**:
   - Open a terminal in the project directory (`desktop/` folder).
   - Create a virtual environment:
     ```
     python -m venv .venv
     ```
   - Activate the virtual environment:
     - On Windows: `.\.venv\Scripts\Activate.ps1`
     - On macOS/Linux: `source .venv/bin/activate`

3. **Install Dependencies**:
   - Install the required Python packages:
     ```
     pip install -r requirements.txt
     ```
   - For PyQt5 specifically (if needed):
     ```
     pip install -r requirements-pyqt.txt
     ```

4. **Configure Environment Variables**:
   - Edit the `.env` file in the `desktop/` folder with your API keys if needed (e.g., for map providers). Example:
     ```
     MAP_PROVIDER=osm
     GOOGLE_MAPS_API_KEY=your_key_here
     ```

## Step-by-Step Building the Application

The application uses PyInstaller to create a standalone executable.

1. **Ensure Virtual Environment is Activated**:
   - Activate the virtual environment as described above.

2. **Run the Build Script**:
   - Execute the build script:
     ```
     .\build.bat
     ```
     (On Windows; for other OS, run `pyinstaller pak_map.spec` directly after activating venv.)

3. **Build Output**:
   - The built application will be in the `dist/Pak-Map/` folder.
   - The executable is `Pak-Map.exe` (on Windows).

## Step-by-Step Running the Application

### Option 1: Run from Source (Development Mode)
1. Activate the virtual environment.
2. Run the main script:
   ```
   python main.py
   ```

### Option 2: Run the Packaged Executable (Production Mode)
1. Navigate to the `dist/Pak-Map/` folder.
2. Run the executable:
   - On Windows: `.\Pak-Map.exe`
   - On macOS/Linux: `./Pak-Map` (adjust permissions if needed: `chmod +x Pak-Map`)

## Key Features

- Interactive map of Pakistan with city boundaries.
- Markers and POIs displayed on the map.
- Embedded web view for smooth map interactions.
- Configurable map settings via `map_config.py`.
- Data filtering, sorting, and search support.

## Important Files

- `main.py` — Application entrypoint.
- `ui/main_window.py` — Main window and web view setup.
- `map_config.py` — .env loader and map provider configuration.
- `map/` — HTML, CSS, and JavaScript assets for the Leaflet map.
- `boundaries/` — Cached GeoJSON boundary data.
- `requirements-pyqt.txt` — Minimal runtime dependencies for this desktop app.
- `pak_map.spec` — PyInstaller packaging spec file.
- `build.bat` — Windows build helper for PyInstaller.

## Troubleshooting

- **PyQt5 Installation Issues**: Ensure you have the correct Qt libraries installed. On Windows, PyQt5 wheels are available via pip.
- **Build Errors**: Make sure all dependencies are installed and the virtual environment is activated.
- **Map Not Loading**: Check that the `map/` folder and its contents are intact in the packaged build.
- **File Paths in Frozen App**: The app handles frozen executable paths automatically using `sys.frozen` checks.

## Contributing

- Fork the repository and submit pull requests for improvements.
- Report issues on the GitHub repository.

## License

This project is licensed under the MIT License. See LICENSE file for details.

### Output

The packaged app appears in:

```text
dist\Pak-Map\Pak-Map.exe
```

Distribute the entire `dist\Pak-Map` folder. Do not remove the bundled asset directories.

## Notes

- This is a desktop application, not a web service. It cannot be directly deployed to Render or other web-only hosts.
- Keep `map/`, `ui/`, `boundaries/`, and `.env` available alongside the executable.
- If you need to rebuild, use `build.bat` after activating the local virtual environment.
- Do not change the UI asset files unless you want to modify the app behavior.

## Troubleshooting

- If the app fails to start, confirm `PyQtWebEngine` is installed and `.env` exists.
- If packaging fails, ensure you are on Windows and that `.venv` is active.
- Use the local `.venv` interpreter so the packaged app matches the same environment.

## Project Structure

```text
.
├── .env
├── .venv/
├── boundaries/
├── main.py
├── map/
│   ├── index.html
│   ├── styles.css
│   └── js/
├── map_config.py
├── models/
├── ui/
├── utils/
├── requirements-pyqt.txt
├── requirements.txt
├── pak_map.spec
└── build.bat
```

## Summary

- Use `requirements-pyqt.txt` for the desktop app runtime.
- Run `python main.py` to start the app.
- Use `build.bat` to package into `dist\Pak-Map`.
- Keep the existing UI and map asset files unchanged.
