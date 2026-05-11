# Windows Unified Write Filter (UWF) Status Monitor - System Tray Application

## Overview

This lightweight system tray application monitors the status of Windows Unified Write Filter (UWF) in real-time and displays a visual indicator:

- 🟢 **Green Icon** - System is protected (Filter ON & Volume Protected)
- 🔴 **Red Icon** - System is unprotected (Filter OFF or Volume Unprotected)

The application runs silently in the background with no console windows or pop-ups, checking the UWF status every 5 seconds.

## Features

- Real-time UWF status monitoring
- Visual status indicator in system tray
- Hover tooltip showing current filter and volume state
- Right-click menu for manual refresh and detailed status view
- Completely silent operation (no console windows)
- Lightweight and minimal resource usage

## Prerequisites

- Windows 10/11 with UWF enabled
- Python 3.7 or higher
- Administrator privileges (required for `uwfmgr.exe` commands)

## Installation and Setup

### Step 1: Create Project Directory

```bash
mkdir uwf_monitor
cd uwf_monitor
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
```

### Step 3: Activate Virtual Environment

**Command Prompt:**
```bash
venv\Scripts\activate.bat
```

**PowerShell:**
```bash
venv\Scripts\Activate.ps1
```

*Note: If PowerShell shows an execution policy error, run:*
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 4: Create Requirements File

Create a file named `requirements.txt` with the following content:

```txt
PyQt5==5.15.10
```

### Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 6: Test the Script

```bash
python uwf_tray_monitor.py
```

You should see the system tray icon appear showing the current UWF status.

## Building the Executable

### Step 1: Install PyInstaller

```bash
pip install pyinstaller
```

### Step 2: Build the EXE

```bash
pyinstaller --onefile --windowed --noconsole --name UWF_Monitor uwf_tray_monitor.py
```

**PyInstaller Options Explained:**
- `--onefile` - Creates a single executable file
- `--windowed` - No console window appears
- `--noconsole` - Suppresses console (same as --windowed)
- `--name UWF_Monitor` - Name of the output executable

### Step 3: Locate the Executable

The executable will be created in:
```
dist\UWF_Monitor.exe
```

### Step 4: Clean Build (Optional)

If you need to rebuild, first clean up:

```bash
rmdir /s /q build dist
del /f UWF_Monitor.spec
```

Then run the PyInstaller command again.

## Deployment

### Run at Startup (Optional)

To automatically start the monitor when Windows boots:

1. Copy `UWF_Monitor.exe` to a permanent location (e.g., `C:\Program Files\UWF_Monitor\`)

2. Press `Win + R` and type: `shell:startup`

3. Create a shortcut to `UWF_Monitor.exe` in the Startup folder

4. Right-click the shortcut → Properties → Advanced → Check "Run as administrator"

## Usage

### System Tray Icon

- **Green Circle** - UWF is active and protecting the system
- **Red Circle** - UWF is inactive or volume is not protected

### Tooltip Information

Hover over the tray icon to see:
- Current filter state (ON/OFF)
- Volume C: protection status (Protected/Unprotected)
- Overall system status

### Context Menu

Right-click the tray icon for options:
- **Refresh Status** - Manually trigger a status check
- **Show UWF Info** - Display detailed UWF configuration
- **Exit** - Close the application

## Technical Details

### How It Works

1. The application runs `uwfmgr.exe get-config` to check the filter state
2. It runs `uwfmgr.exe volume get-config c:` to check volume protection
3. Both commands output UTF-16 encoded text, which is decoded properly
4. The status is checked every 5 seconds
5. All subprocess calls use Windows flags to prevent console windows from appearing

### UWF Status Detection

The application checks for:
- **Filter state: ON** in the UWF configuration output
- **Volume state: Protected** for the C: drive

Both conditions must be true for the system to be considered "Protected".

## Troubleshooting

### Permission Issues

If the application can't read UWF status:
- Run the executable as Administrator
- Ensure UWF is installed and configured on your system

### Icon Not Appearing

- Check Windows notification area settings
- Ensure the application is running (check Task Manager)
- Try restarting the application

### Build Errors

If PyInstaller fails:
```bash
# Upgrade PyInstaller
pip install --upgrade pyinstaller

# Try with clean build
rmdir /s /q build dist
pyinstaller --clean --onefile --windowed --name UWF_Monitor uwf_tray_monitor.py
```

## UWF Configuration Example

For reference, here's how to configure UWF with the parameters mentioned:

```bash
uwfmgr overlay set-type disk
uwfmgr overlay set-size 20480
uwfmgr overlay set-criticalthreshold 20000
uwfmgr overlay set-warningthreshold 20000
uwfmgr.exe volume protect c:
uwfmgr.exe filter enable
```
## Github [link](https://github.com/vijaidjearam/unifiedwritefilter/tree/main) for excpetions of antivirus
## License

This tool is provided as-is for monitoring Windows Unified Write Filter status. Use at your own discretion.



---

*Last updated: 2026*
