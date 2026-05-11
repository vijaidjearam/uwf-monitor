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