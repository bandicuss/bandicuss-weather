#!/bin/bash

set -e

APP_NAME="Bandicuss Weather"
INSTALL_DIR="$HOME/.local/share/bandicuss-weather"
DESKTOP_DIR="$HOME/Desktop"
LAUNCHER="$DESKTOP_DIR/bandicuss-weather.desktop"

echo "=============================================="
echo "       BANDICUSS WEATHER INSTALLER"
echo "=============================================="
echo

# Make sure Python 3 exists
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: Python 3 was not found."
    echo "Please install Python 3 and run this installer again."
    exit 1
fi

# Make sure Chromium exists
if ! command -v chromium >/dev/null 2>&1; then
    echo "WARNING: Chromium was not found."
    echo "Text weather products should still work,"
    echo "but graphical weather products may not open."
    echo
fi

# Make sure lxterminal exists
if ! command -v lxterminal >/dev/null 2>&1; then
    echo "ERROR: lxterminal was not found."
    echo "This installer is currently designed for"
    echo "the ClockworkPi uConsole desktop environment."
    exit 1
fi

# Make sure weather.py is beside this installer
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$SCRIPT_DIR/weather.py" ]; then
    echo "ERROR: weather.py was not found."
    exit 1
fi

echo "Installing Bandicuss Weather..."
echo

mkdir -p "$INSTALL_DIR"
mkdir -p "$DESKTOP_DIR"

cp "$SCRIPT_DIR/weather.py" "$INSTALL_DIR/weather.py"

cat > "$LAUNCHER" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Bandicuss Weather
Comment=Aviation and weather field console
Exec=lxterminal -e bash -c "python3 $INSTALL_DIR/weather.py"
Icon=weather-clear
Terminal=false
Categories=Utility;
EOF

chmod +x "$LAUNCHER"

echo
echo "=============================================="
echo " INSTALLATION COMPLETE"
echo "=============================================="
echo
echo "Installed to:"
echo " $INSTALL_DIR"
echo
echo "Desktop launcher created:"
echo " $LAUNCHER"
echo
echo "Double-click 'Bandicuss Weather' on the"
echo "desktop and choose Execute to launch it."
echo
