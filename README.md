# UFO Sightings Explorer:)

A 3D interactive globe visualization of UFO sightings built with HTML/JS and Python.

## Structure
- `docs/`: Contains the web application (HTML/CSS/JS) and data.
    - `data/`: Dataset and generated JSONs.
- `src/`: Python scripts for data processing.

## Usage
1. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Process data:
   ```sh
   python src/main.py
   ```
3. Open `docs/index.html` in a browser.
   - For best results (and to avoid CORS errors with local JSON), use a local server like "Live Server" in VS Code.
   - Or view the live deployment on GitHub Pages.
