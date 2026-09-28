# Bandicuss Weather v4.0

Bandicuss Weather is a lightweight aviation and weather field console built for the ClockworkPi uConsole.

Version 4.0 features a redesigned Rich terminal interface optimized for the uConsole display, aviation weather tools, National Weather Service products, and quick access to official graphical weather resources.

## Features

### Weather Center

The main Weather Center provides quick access to:

- Aviation Summary
- METAR / Conditions
- TAF
- NWS Alerts
- NWS Forecast
- Graphical Weather
- Weather refresh
- ICAO station selection

The v4.0 interface uses Rich terminal panels, tables, status information, and weather-impact highlighting designed for the uConsole screen.

### Aviation Summary

The Aviation Summary provides a quick operational overview of the selected station, including:

- Flight category
- TAF availability
- Current conditions
- METAR
- Formatted TAF information

### METAR / Conditions

Detailed current aviation weather information includes:

- Raw METAR
- Decoded conditions
- Flight category
- Ceiling
- Visibility
- Temperature
- Dewpoint
- Relative humidity
- Wind chill when applicable
- Heat index when applicable
- Wind direction and speed
- Wind gusts
- Altimeter setting
- Sea-level pressure
- Present weather
- Cloud layers

Weather-impact information such as ceiling and visibility is highlighted by flight category.

### TAF

The TAF display includes:

- Raw TAF
- Formatted forecast groups
- Change groups
- Aviation weather impact highlighting

### NWS Alerts

Bandicuss Weather retrieves active National Weather Service alerts for supported locations.

Alert information includes:

- Active alert count
- Event
- Severity
- Urgency
- Certainty
- Effective and expiration information
- Alert details

Alert panels are visually highlighted according to NWS-provided severity.

### NWS Forecast

The forecast display provides National Weather Service point forecast information including:

- Day and night forecast periods
- Temperature
- Wind
- Forecast summary
- Detailed forecast information

### Graphical Weather

Bandicuss Weather can launch official graphical weather products in Chromium:

- NWS Radar
- NOAA GOES Satellite
- Storm Prediction Center
- Weather Prediction Center
- National Hurricane Center

## Startup Interface

Version 4.0 includes an animated Bandicuss Weather startup screen and station-selection interface.

The default station can be accepted by pressing **Enter**, or another ICAO airport identifier can be entered before opening the Weather Center.

## Data Sources

Bandicuss Weather uses publicly available weather information and official graphical products from:

- Aviation Weather Center
- National Weather Service
- NOAA / NESDIS
- Storm Prediction Center
- Weather Prediction Center
- National Hurricane Center

## Requirements

Bandicuss Weather v4.0 was developed and tested on a ClockworkPi uConsole running Debian Linux with a Raspberry Pi Compute Module 4.

The installer expects:

- Python 3
- Internet connection
- LXTerminal
- Graphical desktop environment

Bandicuss Weather also uses the Python **Rich** package for its terminal interface.

If Rich is not already installed, the installer will attempt to install the Debian `python3-rich` package automatically.

Chromium is required for graphical weather products. If Chromium is not installed, the terminal-based weather functions can still be used.

## Installation

Clone the repository:

```bash
git clone https://github.com/bandicuss/bandicuss-weather.git
```

Enter the downloaded folder:

```bash
cd bandicuss-weather
```

Run the installer:

```bash
./install.sh
```

The installer will:

1. Verify Python 3 is available.
2. Install `python3-rich` if Rich is not already available.
3. Install Bandicuss Weather to `~/.local/share/bandicuss-weather`.
4. Create a Bandicuss Weather desktop launcher.
5. Configure automatic fullscreen launching when a compatible labwc configuration is detected.
6. Preserve a backup of the labwc configuration before adding the fullscreen rule.

If labwc is not detected, installation will continue normally without automatic fullscreen configuration.

After installation, double-click **Bandicuss Weather** on the desktop and choose **Execute**.

## Fullscreen Support

On supported ClockworkPi uConsole labwc desktops, the installer configures the Bandicuss Weather LXTerminal window to automatically open fullscreen.

The fullscreen rule applies specifically to the terminal window titled:

```text
Bandicuss Weather
```

Other LXTerminal windows are not affected.

The installer checks for an existing Bandicuss Weather rule before making changes, preventing duplicate fullscreen rules when the installer is run again.

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

A different ICAO airport identifier can be entered when the application starts.

Examples:

```text
KDCA
KADW
KBWI
KJFK
EGLL
```

## Controls

From the main Weather Center:

```text
[1] Aviation Summary
[2] METAR / Conditions
[3] TAF
[4] NWS Alerts
[5] NWS Forecast
[6] Graphical Weather
[R] Refresh Weather
[S] Change Station
[Q] Exit
```

## Weather Data Notes

NWS alerts and NWS point forecasts are primarily intended for locations supported by the U.S. National Weather Service.

METAR and TAF availability depends on the selected aviation station and the data available from the Aviation Weather Center.

Graphical weather products require Chromium and an active internet connection.

An active internet connection is required to retrieve live weather data.

## Project Status

**Current version: v4.0**

Bandicuss Weather is an actively developed personal uConsole weather project.

Additional features and modules may be added as development continues.

## Author

Created by Bandicuss.
