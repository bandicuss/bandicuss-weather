# Bandicuss Weather v4.1

Bandicuss Weather is a lightweight aviation and weather field console built for the ClockworkPi uConsole.

Version 4.1 combines a Rich terminal interface optimized for the uConsole with a Pixel startup animation and the Horizon Observatory live acquisition screen. It provides aviation weather tools, National Weather Service products, and quick access to official graphical weather resources.

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

The v4.1 interface uses Rich terminal panels, tables, status information, and weather-impact highlighting designed for the uConsole screen.

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

The optional Pixel startup animation shows four landscape scenes before station selection. Press **any key** to continue to station selection, or let the animation finish.

The default station can be accepted by pressing **Enter**, or another ICAO airport identifier can be entered before opening the Weather Center.

### Horizon Observatory Live Acquisition

After station selection, Horizon Observatory shows the real acquisition sequence:

1. METAR acquisition
2. TAF acquisition
3. NWS Alerts check
4. Transition to the Weather Center dashboard

METAR, TAF, and NWS ALERTS remain visible together. Their labels reflect actual operations: **PENDING**, **ACQUIRING** or **CHECKING**, **ACQUIRED** or **CHECKED**, **UNAVAILABLE**, **FAILED**, or **SKIPPED**. A completed check with zero NWS alerts is successful and displays **CHECKED**.

The landscape, slowly moving dish, and outward pulse animate while requests wait. The dish and pulse are decorative visual effects; they do not represent radar measurements or imply that radar data is being acquired. There are no progress percentages or artificial minimum loading times.

A missing or failed METAR stops acquisition and shows an error acknowledgement. TAF unavailability or failure and NWS alert-check failure allow the application to continue to the dashboard. The dashboard's **R** refresh and **S** station-change controls use the same live acquisition screen.

Press **Ctrl+C** to exit during startup or acquisition; the application restores the terminal. No key is needed to advance the acquisition sequence.

## Data Sources

Bandicuss Weather uses publicly available weather information and official graphical products from:

- Aviation Weather Center
- National Weather Service
- NOAA / NESDIS
- Storm Prediction Center
- Weather Prediction Center
- National Hurricane Center

## Requirements

Bandicuss Weather v4.1 was developed and tested on a ClockworkPi uConsole running Debian Linux with a Raspberry Pi Compute Module 4.

The installer expects:

- Python 3
- Internet connection
- LXTerminal
- Graphical desktop environment

Bandicuss Weather also uses the Python **Rich** package for its terminal interface.

If Rich is not already installed, the installer will attempt to install the Debian `python3-rich` package automatically.

Chromium is required for graphical weather products. If Chromium is not installed, the terminal-based weather functions can still be used.

### Terminal Layout and Animation Controls

- Horizon Observatory requires an interactive terminal of at least **97 columns × 23 rows**, the verified uConsole acquisition layout.
- The optional Pixel startup animation requires at least **79 columns × 24 rows**. At 97×23, the startup animation is skipped and Horizon Observatory remains available.
- If the terminal is too small for Horizon Observatory, or output is redirected, acquisition continues with text status messages. Shrinking the terminal during acquisition also falls back to text.
- Set `BANDICUSS_NO_ANIMATION=1` to disable both animations. Setting `NO_COLOR`, including an empty value, also disables them. Acquisition and the normal weather interface remain available.

For example, launch without animations:

```bash
BANDICUSS_NO_ANIMATION=1 python3 ~/.local/share/bandicuss-weather/weather.py
```

## Installation

Clone the v4.1 release branch:

```bash
git clone --branch v4.1 https://github.com/bandicuss/bandicuss-weather.git
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
3. Install the application, Horizon Observatory acquisition components, Pixel drawing helpers, and their license to `~/.local/share/bandicuss-weather`.
4. Create a Bandicuss Weather desktop launcher.
5. Configure automatic fullscreen launching when a compatible labwc configuration is detected.
6. Preserve a backup of the labwc configuration before adding the fullscreen rule.

If labwc is not detected, installation will continue normally without automatic fullscreen configuration.

After installation, double-click **Bandicuss Weather** on the desktop and choose **Execute**.

## Updating to v4.1

In your existing repository clone, fetch the release branch, switch to it, update it, and rerun the installer:

```bash
cd bandicuss-weather
git fetch origin
git switch v4.1
git pull --ff-only origin v4.1
./install.sh
```

Use the location of your existing clone for the first command. Keep any personal source changes safe before switching or updating branches.

Updating the repository alone does not update the installed application. Rerunning `./install.sh` copies the new runtime modules to `~/.local/share/bandicuss-weather` and updates the normal desktop launcher. Do not copy only `weather.py`: v4.1 also needs its acquisition and Pixel modules.

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

**Current version: v4.1**

Bandicuss Weather is an actively developed personal uConsole weather project.

The v4.1 startup, live acquisition, refresh, station change, and terminal cleanup have been tested on the uConsole.

## Author

Created by Bandicuss.
