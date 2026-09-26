# Bandicuss Weather

Bandicuss Weather is a lightweight aviation and weather field console built for the ClockworkPi uConsole.

It provides terminal-based aviation weather information along with quick access to official graphical weather products.

## Features

### Aviation Weather

- Quick aviation weather summary
- Current conditions
- Raw METAR
- Decoded METAR information
- TAF retrieval
- Formatted TAF change groups
- Flight category
- Temperature and dewpoint
- Relative humidity
- Wind and gust information
- Visibility
- Altimeter setting
- Ceiling information
- Weather and cloud layers

### NWS Weather

- Active NWS alerts
- Active alert count on the main screen
- Detailed watch, warning, and advisory information
- NWS point forecasts
- Weather refresh
- ICAO station selection

### Graphical Weather

Bandicuss Weather can launch official graphical weather products in Chromium:

- NWS Radar
- NOAA GOES Satellite
- SPC Convective Outlooks
- WPC Forecast Products
- National Hurricane Center / Tropical Weather

## Data Sources

Bandicuss Weather uses publicly available weather information from:

- Aviation Weather Center
- National Weather Service
- NOAA / NESDIS
- Storm Prediction Center
- Weather Prediction Center
- National Hurricane Center

## Requirements

Bandicuss Weather was developed and tested on a ClockworkPi uConsole running Debian Linux with a Raspberry Pi Compute Module 4.

The current installer expects:

- Python 3
- Internet connection
- Chromium
- LXTerminal
- Graphical desktop environment

No additional Python packages are currently required.

## Installation

Open a terminal and clone the repository:

```bash
git clone https://github.com/bandicuss/bandicuss-weather.git

Enter the downloaded folder:

```bash
cd bandicuss-weather
```

Run the installer:

```bash
./install.sh
```

The installer will:

1. Create the Bandicuss Weather application directory.
2. Install `weather.py`.
3. Create a Bandicuss Weather desktop launcher.
4. Make the desktop launcher executable.

After installation, double-click **Bandicuss Weather** on the desktop and choose **Execute**.

## Manual Launch

The installed application can also be started from a terminal:

```bash
python3 ~/.local/share/bandicuss-weather/weather.py
```

## Default Weather Station

The default ICAO station is:

```text
KDCA
```

A different ICAO identifier can be entered when the application starts.

Examples:

```text
KDCA
KADW
KBWI
KJFK
EGLL
```

## Updating Weather Data

Use **Refresh Weather** from the main Weather Center to retrieve updated METAR, TAF, and NWS alert information.

## Notes

NWS alerts and NWS point forecasts are primarily intended for locations supported by the U.S. National Weather Service.

METAR and TAF availability depends on the selected aviation station and the data available from the Aviation Weather Center.

Graphical products require Chromium and an active internet connection.

## Project Status

Bandicuss Weather is an actively developed personal uConsole project.

Additional features may be added as development continues.

## Author

Created by Bandicuss.
