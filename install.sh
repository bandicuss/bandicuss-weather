#!/bin/bash

set -e

APP_NAME="Bandicuss Weather"
INSTALL_DIR="$HOME/.local/share/bandicuss-weather"
DESKTOP_DIR="$HOME/Desktop"
LAUNCHER="$DESKTOP_DIR/bandicuss-weather.desktop"
LABWC_CONFIG="$HOME/.config/labwc/rc.xml"

echo "=============================================="
echo "       BANDICUSS WEATHER INSTALLER"
echo "=============================================="
echo

# Check for Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: Python 3 was not found."
    echo "Please install Python 3 and run this installer again."
    exit 1
fi

# Check for Rich
if ! python3 -c "import rich" >/dev/null 2>&1; then
    echo "Rich is required for the Bandicuss Weather interface."
    echo
    echo "Installing python3-rich..."
    echo

    sudo apt update
    sudo apt install -y python3-rich

    echo
fi

# Verify Rich after installation
if ! python3 -c "import rich" >/dev/null 2>&1; then
    echo "ERROR: Rich could not be installed."
    echo "Bandicuss Weather requires python3-rich."
    exit 1
fi

# Check for Chromium
if ! command -v chromium >/dev/null 2>&1; then
    echo "WARNING: Chromium was not found."
    echo "Text weather products should still work,"
    echo "but graphical weather products may not open."
    echo
fi

# Check for LXTerminal
if ! command -v lxterminal >/dev/null 2>&1; then
    echo "ERROR: lxterminal was not found."
    echo "This installer is currently designed for"
    echo "the ClockworkPi uConsole desktop environment."
    exit 1
fi

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
# Include the approved acquisition artwork and its standard-library helpers.
for module in bandicuss_acquisition.py bandicuss_horizon.py bandicuss_intro.py bandicuss_intro_layout.py LICENSE-intros; do
    cp "$SCRIPT_DIR/$module" "$INSTALL_DIR/$module"
done

# Create desktop launcher
cat > "$LAUNCHER" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Bandicuss Weather
Comment=Aviation and weather field console
Exec=lxterminal --title="Bandicuss Weather" -e bash -c "python3 $INSTALL_DIR/weather.py"
Icon=weather-clear
Terminal=false
Categories=Utility;
EOF

chmod +x "$LAUNCHER"

# Configure labwc fullscreen rule when available
if [ -f "$LABWC_CONFIG" ]; then

    echo "Configuring fullscreen launch..."

    if grep -Fq '<windowRule title="Bandicuss Weather">' "$LABWC_CONFIG"; then

        echo "Fullscreen rule already configured."

    else

        BACKUP_FILE="${LABWC_CONFIG}.bandicuss-backup-$(date +%Y%m%d-%H%M%S)"
        cp "$LABWC_CONFIG" "$BACKUP_FILE"

        if grep -Fq '<windowRules>' "$LABWC_CONFIG"; then

            python3 - "$LABWC_CONFIG" <<'PY'
import sys

path = sys.argv[1]

with open(path, "r", encoding="utf-8") as file:
    text = file.read()

rule = """    <windowRule title="Bandicuss Weather">
      <action name="ToggleFullscreen"/>
    </windowRule>
"""

marker = "</windowRules>"

if marker not in text:
    raise SystemExit("Could not locate closing windowRules tag.")

text = text.replace(
    marker,
    rule + "  " + marker,
    1,
)

with open(path, "w", encoding="utf-8") as file:
    file.write(text)
PY

        else

            python3 - "$LABWC_CONFIG" <<'PY'
import sys

path = sys.argv[1]

with open(path, "r", encoding="utf-8") as file:
    text = file.read()

rules = """  <windowRules>
    <windowRule title="Bandicuss Weather">
      <action name="ToggleFullscreen"/>
    </windowRule>
  </windowRules>
"""

marker = "</openbox_config>"

if marker not in text:
    raise SystemExit("Could not locate closing openbox_config tag.")

text = text.replace(
    marker,
    rules + marker,
    1,
)

with open(path, "w", encoding="utf-8") as file:
    file.write(text)
PY

        fi

        echo "Fullscreen rule added."
        echo "labwc backup created:"
        echo " $BACKUP_FILE"

    fi

    # Reload labwc when running inside an active labwc session.
    if command -v labwc >/dev/null 2>&1 && [ -n "${LABWC_PID:-}" ]; then
        labwc --reconfigure >/dev/null 2>&1 || true
    fi

else

    echo "labwc configuration was not found."
    echo "Fullscreen setup was skipped."

fi

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
