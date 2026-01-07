#!/bin/bash
# Upwork Wayland Screenshot Patch
# This script patches Upwork's app.asar to use spectacle for screenshots on Wayland
#
# The problem: Upwork's native module detects Wayland and disables screenshots,
# showing "Wayland screenshots not supported" error.
#
# The solution: Patch the JavaScript to use spectacle (KDE's screenshot tool)
# instead of the native module for screen capture.

set -e

UPWORK_RESOURCES="/opt/Upwork/resources"
APP_ASAR="$UPWORK_RESOURCES/app.asar"
BACKUP_ASAR="$UPWORK_RESOURCES/app.asar.original"
TEMP_DIR="/tmp/upwork-patch-$$"

# Check dependencies
check_deps() {
    local missing=()
    command -v npx >/dev/null || missing+=("npm/npx")
    command -v spectacle >/dev/null || missing+=("spectacle")

    if [ ${#missing[@]} -gt 0 ]; then
        echo "Missing dependencies: ${missing[*]}"
        echo "Please install them and try again."
        exit 1
    fi
}

# Extract app.asar
extract() {
    echo "Extracting app.asar..."
    mkdir -p "$TEMP_DIR"
    npx asar extract "$APP_ASAR" "$TEMP_DIR/extracted"
}

# Apply the patch
patch_js() {
    echo "Applying screenshot patch..."

    local main_js="$TEMP_DIR/extracted/out/main/main.js"

    if [ ! -f "$main_js" ]; then
        echo "Error: main.js not found"
        exit 1
    fi

    # The code we're replacing (handles screenshot capture)
    local old_code='if(this.c.utaNative.isWayland())return J.screenSnap={},J.activeProcessName=null,J.activeWindowTitle=null,J.processes=[],J;{const L=R.snapOnlyActiveDisplay?"display":"desktop",z=yield this.c.utaNative.snapScreen(L,!1);J.activeProcessName=z.activeProcessName,J.activeWindowTitle=z.activeWindowTitle,J.processes=z.processes,J.screenSnap={blob:z.data,filename:z.filename,width:z.width,height:z.height}}'

    # New code using spectacle for screenshot capture
    local new_code='{const _cp=require("child_process"),_fs=require("fs");const _tmpFile="/tmp/upwork-snap.png";try{_cp.execSync("/usr/bin/spectacle -b -n -f -o "+_tmpFile,{timeout:10000,env:process.env});const _data=_fs.readFileSync(_tmpFile);J.screenSnap={blob:_data,filename:"screenshot.png",width:1920,height:1080};try{_fs.unlinkSync(_tmpFile)}catch(e){}}catch(e){console.log("Screenshot error:",e);J.screenSnap={}}J.activeProcessName=null;J.activeWindowTitle=null;J.processes=[]}'

    node -e "
const fs = require('fs');
let content = fs.readFileSync('$main_js', 'utf8');
const oldCode = \`$old_code\`;
const newCode = \`$new_code\`;
if(content.includes(oldCode)) {
    content = content.replace(oldCode, newCode);
    fs.writeFileSync('$main_js', content);
    console.log('Patch applied successfully');
    process.exit(0);
} else {
    console.log('ERROR: Could not find code to patch. Upwork version may have changed.');
    process.exit(1);
}
"
}

# Repack app.asar
repack() {
    echo "Repacking app.asar..."
    npx asar pack "$TEMP_DIR/extracted" "$TEMP_DIR/app-patched.asar"
}

# Install the patched version
install_patch() {
    echo "Installing patched app.asar..."

    if [ ! -f "$BACKUP_ASAR" ]; then
        echo "Creating backup at $BACKUP_ASAR"
        sudo cp "$APP_ASAR" "$BACKUP_ASAR"
    fi

    sudo cp "$TEMP_DIR/app-patched.asar" "$APP_ASAR"
    echo "Patch installed successfully!"
}

# Restore original
restore() {
    if [ -f "$BACKUP_ASAR" ]; then
        echo "Restoring original app.asar..."
        sudo cp "$BACKUP_ASAR" "$APP_ASAR"
        echo "Original restored."
    else
        echo "No backup found at $BACKUP_ASAR"
        exit 1
    fi
}

# Cleanup
cleanup() {
    rm -rf "$TEMP_DIR"
}

# Main
case "${1:-install}" in
    install)
        check_deps
        extract
        patch_js
        repack
        install_patch
        cleanup
        echo ""
        echo "Done! Launch Upwork with: upwork-wayland"
        ;;
    restore)
        restore
        ;;
    *)
        echo "Usage: $0 [install|restore]"
        exit 1
        ;;
esac
