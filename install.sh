#!/bin/bash
set -e

# Default prefix
PREFIX=${1:-/usr/local}

# Define paths
BIN_DIR="$PREFIX/bin"
SHARE_DIR="$PREFIX/share"
APP_ID="io.github.p82590037723122.CPU_Affinity_Manager"
APP_DIR="$SHARE_DIR/$APP_ID"
LOCALE_DIR="$SHARE_DIR/locale"
APPLICATIONS_DIR="$SHARE_DIR/applications"

echo "Installing to $PREFIX..."

# Create directories
mkdir -p "$BIN_DIR"
mkdir -p "$APP_DIR"
mkdir -p "$LOCALE_DIR"
mkdir -p "$APPLICATIONS_DIR"

# Copy application files
echo "Copying application files..."
cp main.py "$APP_DIR/"
cp utils.py "$APP_DIR/"
cp settings.py "$APP_DIR/"
cp auto_apply.py "$APP_DIR/"
cp affinity_window.ui "$APP_DIR/"
cp "$APP_ID.desktop" "$APPLICATIONS_DIR/"

# Compile and copy translations
if [ -d "locale" ]; then
    echo "Compiling and installing translations..."
    # Find all .po files
    find locale -name "*.po" | while read po_file; do
        lang=$(basename "$po_file" .po)
        mkdir -p "$LOCALE_DIR/$lang/LC_MESSAGES"
        msgfmt "$po_file" -o "$LOCALE_DIR/$lang/LC_MESSAGES/$APP_ID.mo"
    done
fi

# Create executable wrapper
echo "Creating executable wrapper..."
cat > "$BIN_DIR/cpu-affinity-manager" <<EOF
#!/bin/bash
export APP_ID="$APP_ID"
export APP_DIR="$APP_DIR"
export LOCALE_DIR="$LOCALE_DIR"
exec python3 "\$APP_DIR/main.py" "\$@"
EOF

chmod +x "$BIN_DIR/cpu-affinity-manager"

# Update desktop file to point to wrapper
sed -i "s|Exec=.*|Exec=$BIN_DIR/cpu-affinity-manager|" "$APPLICATIONS_DIR/$APP_ID.desktop"

echo "Installation complete!"
echo "Run 'cpu-affinity-manager' to start the application."

