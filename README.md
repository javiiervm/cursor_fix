<div align="center">
  <h1>Hackintosh macOS Custom Cursor Fix</h1>
  <p>
    <img src="https://img.shields.io/github/last-commit/javiiervm/cursor_fix?color=blue" alt="Last Commit" />
    <img src="https://img.shields.io/badge/platform-macOS%20Monterey%2B-lightgrey" alt="Platform Support" />
    <img src="https://img.shields.io/badge/python-3.10%2B-yellow" alt="Python Version" />
    <img src="https://img.shields.io/github/issues/javiiervm/cursor_fix" alt="Issues" />
    <img src="https://img.shields.io/github/stars/javiiervm/cursor_fix" alt="Stars" />
  </p>
</div>
<br />

A custom, smooth, and smart software cursor designed specifically to solve the "hardware cursor glitch" on Hackintosh systems running macOS Monterey or higher.

Instead of relying on the native GPU-drawn cursor, this project replaces it with a minimalist, software-rendered dot (built with Python + PyObjC). It runs flawlessly at 120Hz without lag and intelligently reacts (changes color) when hovering over interactive UI elements or window resizing borders.

## Features

* **Multithreading:** Separates the geometry logic from the rendering engine. The main graphics thread runs at an uninterrupted 120 FPS, while a lightweight background thread scans the screen for interactions.
* **Smart Hover:** Uses the macOS Accessibility API and CoreGraphics to detect buttons, links, text fields, and invisible window borders, changing the cursor's color instantly.
* **App Nap Immune:** Configured at the system level as a critical user interface process to prevent macOS from suspending the Python thread to save battery.
* **Persistent Auto-Start:** Integrated with `launchd` so it starts automatically upon login and instantly revives itself if the process ever crashes.

## Prerequisites

1. **macOS Monterey (12.x)** or higher.
2. **Python 3** installed on your system.
3. **Mousecape** (A free, open-source tool to hide the native cursor).

## Installation

### Step 1: Clone the repository & install dependencies
Clone this repository or download the files into a safe, permanent folder in your user directory (e.g., `~/Scripts/CursorFix/`).

```bash
cd ~/Path/To/Your/Folder
pip3 install -r requirements.txt
```

### Step 2: Hide the glitched native cursor
To prevent the hardware cursor from flickering beneath our new Python cursor, we need to make it completely transparent at the system level.

1. Download and install [Mousecape](https://github.com/alexzielenski/Mousecape).
2. Run the included `crear_png.py` script to generate a 1x1 transparent PNG on your desktop (or use your own).
3. Open Mousecape, press `Cmd + N` to create a new cape, right-click it, and select **Edit**.
4. Add two cursors by clicking the `+` button at the bottom left:
   * Type: **Arrow** (Standard pointer). Drag the transparent PNG into the image box and set the Hot Spot to `0, 0`.
   * Type: **Pointing Hand** (For links and the Dock). Drag the exact same transparent PNG into the image box and set the Hot Spot to `0, 0`.
5. Close the edit window and double-click your new cape in the main Mousecape list to apply it.

### Step 3: Configure the daemon (Auto-start)
1. Open the `com.javier.cursorfix.plist` file with any text editor.
2. **CRITICAL:** Edit the two paths inside the `<array>` tag so they exactly match the absolute path of your Python 3 executable (find it by running `which python3`) and the absolute path where you saved `cursor_fix.py`.
3. Move the file to your `LaunchAgents` folder and load the service:

```bash
mkdir -p ~/Library/LaunchAgents
cp com.javier.cursorfix.plist ~/Library/LaunchAgents/
chmod 644 ~/Library/LaunchAgents/com.javier.cursorfix.plist
launchctl load ~/Library/LaunchAgents/com.javier.cursorfix.plist
```

### Step 4: Grant Accessibility Permissions
1. Go to **System Settings > Privacy & Security > Accessibility**.
2. Add and toggle on the Python executable or the Terminal app running the script. This is required for the background thread to read the UI elements beneath the cursor.

## Uninstallation

If you want to revert the changes and remove the program entirely:

1. Stop the background service:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.javier.cursorfix.plist
   ```
2. Delete the `.plist` file:
   ```bash
   rm ~/Library/LaunchAgents/com.javier.cursorfix.plist
   ```
3. Open Mousecape, right-click your transparent cape, and select **Remove** to restore the native cursor (or go to *Mousecape > Restore Default* in the top menu bar).
4. Delete the folder where you cloned this repository.

## Known Limitations

Due to macOS's strict security architecture (Sandboxing), it is **impossible** for third-party applications to draw overlays on top of the operating system's Secure Input UI. 

When macOS prompts you for your administrator password to install a program, or when you are on the lock/login screen, the Python cursor will temporarily disappear. This is an intended security feature of macOS to prevent clickjacking.

Also, the glitchy cursor can still appear briefly when performing certain actions.
