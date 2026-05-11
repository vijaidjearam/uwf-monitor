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

## Source Code

Save the following code as `uwf_tray_monitor.py`:

```python
import sys
import subprocess
import threading
import time
import re
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject

# Windows-specific subprocess flags to hide console windows
if sys.platform == 'win32':
    if not hasattr(subprocess, 'CREATE_NO_WINDOW'):
        subprocess.CREATE_NO_WINDOW = 0x08000000
    if not hasattr(subprocess, 'STARTF_USESHOWWINDOW'):
        subprocess.STARTF_USESHOWWINDOW = 0x00000001
    if not hasattr(subprocess, 'SW_HIDE'):
        subprocess.SW_HIDE = 0

class UWFMonitor(QObject):
    status_changed = pyqtSignal(bool, str)
    
    def __init__(self):
        super().__init__()
        self.is_protected = False
        self.overlay_info = ""
        
    def check_uwf_status(self):
        """Check UWF protection status - Filter state and Volume state"""
        try:
            # Configure subprocess to hide all windows
            startupinfo = None
            creationflags = 0
            
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW
            
            # Check if filter is enabled - uwfmgr outputs UTF-16
            result = subprocess.run(
                ['uwfmgr.exe', 'get-config'],
                capture_output=True,
                timeout=5,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            # Decode from UTF-16
            output = result.stdout.decode('utf-16-le', errors='ignore')
            
            # Check Filter state: ON
            filter_on = bool(re.search(r'Filter\s+state:\s+ON', output))
            
            # Check volume protection status
            volume_result = subprocess.run(
                ['uwfmgr.exe', 'volume', 'get-config', 'c:'],
                capture_output=True,
                timeout=5,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            # Decode from UTF-16
            volume_output = volume_result.stdout.decode('utf-16-le', errors='ignore')
            
            # Check Volume state: Protected
            volume_protected = bool(re.search(r'Volume\s+state:\s+Protected', volume_output))
            
            # Both conditions must be true for protected status
            is_protected = filter_on and volume_protected
            
            # Create status message
            status_msg = f"Filter: {'ON' if filter_on else 'OFF'}, Volume C: {'Protected' if volume_protected else 'Unprotected'}"
            
            if is_protected != self.is_protected or status_msg != self.overlay_info:
                self.is_protected = is_protected
                self.overlay_info = status_msg
                self.status_changed.emit(self.is_protected, self.overlay_info)
                
        except:
            pass

class UWFTrayIcon(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.monitor = UWFMonitor()
        self.monitor.status_changed.connect(self.update_icon)
        
        # Create initial icon
        self.update_icon(False, "Checking...")
        
        # Create context menu
        self.create_menu()
        
        # Set up timer for periodic checks
        self.timer = QTimer()
        self.timer.timeout.connect(self.monitor.check_uwf_status)
        self.timer.start(5000)  # Check every 5 seconds
        
        # Initial check
        threading.Thread(target=self.monitor.check_uwf_status, daemon=True).start()
        
        self.show()
    
    def create_icon(self, is_protected):
        """Create a colored circular icon"""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw circle
        color = QColor(0, 200, 0) if is_protected else QColor(200, 0, 0)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, 56, 56)
        
        # Add white border
        painter.setPen(QColor(255, 255, 255))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(4, 4, 56, 56)
        
        painter.end()
        
        return QIcon(pixmap)
    
    def update_icon(self, is_protected, overlay_info):
        """Update the tray icon and tooltip"""
        icon = self.create_icon(is_protected)
        self.setIcon(icon)
        
        status_text = "System is Protected" if is_protected else "System is Unprotected"
        tooltip = f"{overlay_info}\n{status_text}"
        self.setToolTip(tooltip)
    
    def create_menu(self):
        """Create the context menu"""
        menu = QMenu()
        
        status_action = menu.addAction("Refresh Status")
        status_action.triggered.connect(lambda: threading.Thread(
            target=self.monitor.check_uwf_status, daemon=True).start())
        
        menu.addSeparator()
        
        overlay_action = menu.addAction("Show UWF Info")
        overlay_action.triggered.connect(self.show_overlay_info)
        
        menu.addSeparator()
        
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.exit_application)
        
        self.setContextMenu(menu)
    
    def show_overlay_info(self):
        """Show detailed UWF status information"""
        try:
            # Configure subprocess to hide all windows
            startupinfo = None
            creationflags = 0
            
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW
            
            # Get filter config
            filter_result = subprocess.run(
                ['uwfmgr.exe', 'get-config'],
                capture_output=True,
                timeout=5,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            # Get volume config
            volume_result = subprocess.run(
                ['uwfmgr.exe', 'volume', 'get-config', 'c:'],
                capture_output=True,
                timeout=5,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            # Decode from UTF-16
            filter_output = filter_result.stdout.decode('utf-16-le', errors='ignore')
            volume_output = volume_result.stdout.decode('utf-16-le', errors='ignore')
            
            info = f"Filter Configuration:\n{filter_output}\n\nVolume C: Configuration:\n{volume_output}"
            
            self.showMessage(
                "UWF Status Information",
                info if info else "No information available",
                QSystemTrayIcon.Information,
                5000
            )
        except:
            self.showMessage(
                "Error",
                "Failed to get UWF info",
                QSystemTrayIcon.Critical,
                3000
            )
    
    def exit_application(self):
        """Exit the application"""
        QApplication.quit()

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    tray_icon = UWFTrayIcon()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
```

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

## License

This tool is provided as-is for monitoring Windows Unified Write Filter status. Use at your own discretion.

## Credits

Developed for system administrators managing Windows devices with UWF enabled.

---

*Last updated: 2026*