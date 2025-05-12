# SunC - Solar Panel Position and Energy Production Simulator

## Overview
**SunC** is a Python-based application designed to simulate and analyze the energy production of a 1m² solar panel at a specified location. The simulator calculates energy output for panels that either track the sun or are fixed at optimal or custom tilt angles (East-West and North-South). It provides detailed monthly energy production data, visualizes results through graphs, and exports findings to an Excel file.

This tool is ideal for researchers, engineers, and enthusiasts interested in optimizing solar panel placement and understanding energy yield under clear-sky conditions.

## Features
- **Solar Position Calculation**: Computes solar vectors using the `pvlib` library for accurate sun positioning.
- **Energy Production Analysis**:
  - Simulates energy output for sun-tracking panels.
  - Determines optimal fixed tilt angles for maximum energy production.
  - Allows custom fixed tilt angles for user-defined configurations.
- **Visualizations**:
  - Monthly energy production graphs.
  - Annual total energy comparison (tracking vs. fixed positions).
  - Efficiency comparison of fixed systems relative to tracking.
  - 3D visualization of panel orientations.
- **Data Export**: Saves results (summary, monthly data, and graph descriptions) to an Excel file and exports visualizations as PNG images.
- **User Interface**: A Tkinter-based GUI for easy input of location data, panel efficiency, and simulation parameters.

## Requirements
To run SunC, ensure you have Python 3.8 or higher installed. The required dependencies are listed in `requirements.txt`. Install them using:

```bash
pip install -r requirements.txt
```

### Dependencies
- `tkinter`: For the graphical user interface.
- `pandas`: For data manipulation and Excel export.
- `numpy`: For numerical computations.
- `pvlib`: For solar position and clear-sky irradiance calculations.
- `matplotlib`: For generating visualizations.
- `openpyxl`: For Excel file handling.

See `requirements.txt` for specific versions.

## Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/mnsoylemez/SunC.git
   cd SunC
   ```

2. **Create a Virtual Environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**:
   ```bash
   python main.py
   ```

## Usage
1. **Launch the Application**:
   Run `main.py` to open the Tkinter GUI.

2. **Input Parameters**:
   - **Location**: Enter the name, latitude, longitude, and timezone (e.g., GMT+3 for Istanbul).
   - **Start Year**: Specify the year for simulation (e.g., 2025).
   - **Panel Efficiency**: Enter the panel efficiency as a percentage (e.g., 20 for 20%).
   - **Custom Position** (optional): Check the box to specify custom East-West and North-South tilt angles.

3. **Calculate and Export**:
   - Click "Hesapla ve Verileri Dışa Aktar" (Calculate and Export Data).
   - Choose a location to save the Excel file (e.g., `output.xlsx`).
   - The program will generate:
     - An Excel file with summary, monthly data, and column descriptions.
     - PNG images of visualizations (e.g., monthly energy, total energy, efficiency, and panel tilt).

4. **View Results**:
   - The GUI displays the monthly energy production graph.
   - Check the exported Excel file and PNG images for detailed results.

## Example
For a location in Istanbul (Latitude: 41.0082, Longitude: 28.9784, Timezone: GMT+3):
- Set panel efficiency to 20%.
- Choose 2025 as the start year.
- Optionally, set custom tilt angles (e.g., East-West: 0°, North-South: 30°).
- Run the simulation and save the output.

The output will include:
- Monthly energy production (kWh) for tracking, optimal fixed, and custom fixed configurations.
- Optimal tilt angles for fixed panels.
- Visualizations saved as `output_Istanbul_monthly.png`, `output_Istanbul_total.png`, etc.

## File Structure
- `main.py`: The main application script containing the GUI and simulation logic.
- `requirements.txt`: Lists Python dependencies.
- `README.md`: This file, providing project documentation.
- `.gitignore`: Specifies files and directories to ignore in version control.

## Notes
- The simulation assumes clear-sky conditions and a 1m² panel.
- Calculations are based on 10-minute intervals for accuracy.
- The application supports only one location at a time in the current version.
- Ensure the timezone is correctly set to avoid discrepancies in solar position calculations.

## Contributing
Contributions are welcome! To contribute:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit your changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

Please ensure your code follows PEP 8 style guidelines and includes appropriate documentation.

## License
See the `LICENSE` file for details.

## Contact
For questions or suggestions, please open an issue on GitHub or contact the maintainer at [soylemeznurhan@gmail.com].

---
Developed by [Nurhan Soylemez](https://github.com/mnsoylemez)
