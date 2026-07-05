#!/bin/bash
# Builds a real, double-clickable macOS app bundle for Insight
# (Insight.app) and installs it to ~/Desktop.
#
# Usage (from anywhere):
#   bash insight_desktop/packaging/build_app.sh

set -euo pipefail

PACKAGING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSIGHT_DESKTOP_DIR="$(dirname "$PACKAGING_DIR")"
REPO_ROOT="$(dirname "$INSIGHT_DESKTOP_DIR")"

APP_NAME="Insight"
BUNDLE_ID="com.tasktorch.insight"
DIST_DIR="$INSIGHT_DESKTOP_DIR/dist"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
ICON_MASTER="$PACKAGING_DIR/iconset_src/icon_master.png"
ICONSET_DIR="$PACKAGING_DIR/AppIcon.iconset"
ICNS_PATH="$PACKAGING_DIR/AppIcon.icns"
LAUNCHER_TEMPLATE="$PACKAGING_DIR/Insight.launcher.sh"

echo "==> Repo root:        $REPO_ROOT"
echo "==> App bundle output: $APP_BUNDLE"

# ---------------------------------------------------------------------
# 0. Generate icon assets if missing
# ---------------------------------------------------------------------
if [ ! -f "$ICON_MASTER" ]; then
    echo "==> Generating icon assets"
    "$REPO_ROOT/.venv/bin/python" "$INSIGHT_DESKTOP_DIR/tools/generate_icon.py"
fi

# ---------------------------------------------------------------------
# 1. Rebuild the .icns from the master icon (if present)
# ---------------------------------------------------------------------
if [ -f "$ICON_MASTER" ]; then
    echo "==> Rebuilding AppIcon.icns from $ICON_MASTER"
    rm -rf "$ICONSET_DIR"
    mkdir -p "$ICONSET_DIR"
    sips -z 16 16     "$ICON_MASTER" --out "$ICONSET_DIR/icon_16x16.png"      >/dev/null
    sips -z 32 32     "$ICON_MASTER" --out "$ICONSET_DIR/icon_16x16@2x.png"   >/dev/null
    sips -z 32 32     "$ICON_MASTER" --out "$ICONSET_DIR/icon_32x32.png"      >/dev/null
    sips -z 64 64     "$ICON_MASTER" --out "$ICONSET_DIR/icon_32x32@2x.png"   >/dev/null
    sips -z 128 128   "$ICON_MASTER" --out "$ICONSET_DIR/icon_128x128.png"    >/dev/null
    sips -z 256 256   "$ICON_MASTER" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
    sips -z 256 256   "$ICON_MASTER" --out "$ICONSET_DIR/icon_256x256.png"    >/dev/null
    sips -z 512 512   "$ICON_MASTER" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
    sips -z 512 512   "$ICON_MASTER" --out "$ICONSET_DIR/icon_512x512.png"    >/dev/null
    if [ -f "$PACKAGING_DIR/iconset_src/icon_master@2x.png" ]; then
        cp "$PACKAGING_DIR/iconset_src/icon_master@2x.png" "$ICONSET_DIR/icon_512x512@2x.png"
    else
        cp "$ICON_MASTER" "$ICONSET_DIR/icon_512x512@2x.png"
    fi
    iconutil -c icns "$ICONSET_DIR" -o "$ICNS_PATH"
else
    echo "==> No master icon found at $ICON_MASTER, reusing existing $ICNS_PATH"
fi

# ---------------------------------------------------------------------
# 2. Assemble the .app bundle
# ---------------------------------------------------------------------
echo "==> Assembling $APP_BUNDLE"
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources"

cp "$ICNS_PATH" "$APP_BUNDLE/Contents/Resources/AppIcon.icns"

# Bake the repo path into the launcher template, then install it as the
# bundle executable.
sed "s|__REPO_ROOT__|$REPO_ROOT|g" "$LAUNCHER_TEMPLATE" > "$APP_BUNDLE/Contents/MacOS/$APP_NAME"
chmod +x "$APP_BUNDLE/Contents/MacOS/$APP_NAME"

cat > "$APP_BUNDLE/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleVersion</key>
    <string>1.1</string>
    <key>CFBundleShortVersionString</key>
    <string>1.1</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.productivity</string>
    <key>NSMicrophoneUsageDescription</key>
    <string>Insight uses your microphone for local, offline voice input. Audio never leaves this device.</string>
    <key>NSCameraUsageDescription</key>
    <string>Insight uses the camera on supported devices for local, offline visual grounding. Frames never leave this device.</string>
</dict>
</plist>
PLIST

echo "==> Built $APP_BUNDLE"

# ---------------------------------------------------------------------
# 3. Install a copy to the Desktop
# ---------------------------------------------------------------------
DESKTOP_APP="$HOME/Desktop/$APP_NAME.app"
echo "==> Installing to $DESKTOP_APP"
rm -rf "$DESKTOP_APP"
cp -R "$APP_BUNDLE" "$DESKTOP_APP"

xattr -dr com.apple.quarantine "$DESKTOP_APP" 2>/dev/null || true
codesign --force --deep --sign - "$DESKTOP_APP" 2>/dev/null || true

echo ""
echo "Done. Double-click $DESKTOP_APP to launch $APP_NAME."
if [[ "$REPO_ROOT" == *"/Desktop"* ]]; then
    echo ""
    echo "Note: your project lives on the Desktop. macOS may block double-clicked"
    echo "apps from reading Desktop folders — the launcher will open a small Terminal"
    echo "window to start Insight with the right permissions."
    echo "For a cleaner launch, move the project to ~/Projects and rebuild."
fi
