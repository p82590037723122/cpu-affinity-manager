#!/bin/bash
set -e

# Default prefix
PREFIX=${1:-/usr/local}

# Define paths
BIN_DIR="$PREFIX/bin"
SHARE_DIR="$PREFIX/share"
APP_ID="io.github.p82590037723122.CPU_Affinity_Manager"
APP_DIR="$SHARE_DIR/$APP_ID"
APPLICATIONS_DIR="$SHARE_DIR/applications"
LOCALE_DIR="$SHARE_DIR/locale"

echo "Uninstalling from $PREFIX..."

# Remove wrapper script
if [ -f "$BIN_DIR/cpu-affinity-manager" ]; then
    echo "Removing executable wrapper..."
    rm "$BIN_DIR/cpu-affinity-manager"
else
    echo "Executable wrapper not found, skipping."
fi

# Remove application directory
if [ -d "$APP_DIR" ]; then
    echo "Removing application files..."
    rm -rf "$APP_DIR"
else
    echo "Application directory not found, skipping."
fi

# Remove desktop file
if [ -f "$APPLICATIONS_DIR/$APP_ID.desktop" ]; then
    echo "Removing desktop entry..."
    rm "$APPLICATIONS_DIR/$APP_ID.desktop"
else
    echo "Desktop entry not found, skipping."
fi

# Remove translations
# We need to be careful not to remove the entire locale directory if it's shared
# But we can remove the specific .mo files for our app
echo "Removing translations..."
find "$LOCALE_DIR" -name "$APP_ID.mo" -type f -delete

# Clean up systemd user units
# Determine the home directory to check (invoking user if sudo)
if [ -n "$SUDO_USER" ]; then
    USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
    USER_HOME="$HOME"
fi

SYSTEMD_USER_DIR="$USER_HOME/.config/systemd/user"

if [ -d "$SYSTEMD_USER_DIR" ]; then
    if [ -f "$SYSTEMD_USER_DIR/cpu-affinity-manager.service" ] || [ -f "$SYSTEMD_USER_DIR/cpu-affinity-manager.timer" ]; then
        echo "Found systemd user configuration in $SYSTEMD_USER_DIR"
        
        # Try to disable if we are running as the user (not root)
        if [ "$EUID" -ne 0 ]; then
             echo "Disabling systemd timer..."
             systemctl --user disable --now cpu-affinity-manager.timer 2>/dev/null || true
        fi
        
        echo "Removing systemd service files..."
        rm -f "$SYSTEMD_USER_DIR/cpu-affinity-manager.service"
        rm -f "$SYSTEMD_USER_DIR/cpu-affinity-manager.timer"
        
        if [ "$EUID" -ne 0 ]; then
             systemctl --user daemon-reload 2>/dev/null || true
        fi
        
        echo "Systemd user units removed."
    fi
fi

echo "Uninstallation complete!"

