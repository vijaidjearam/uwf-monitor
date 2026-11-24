import sys
import subprocess
import threading
import re
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject

if sys.platform == 'win32':
    if not hasattr(subprocess, 'CREATE_NO_WINDOW'):
        subprocess.CREATE_NO_WINDOW = 0x08000000
    if not hasattr(subprocess, 'STARTF_USESHOWWINDOW'):
        subprocess.STARTF_USESHOWWINDOW = 0x00000001
    if not hasattr(subprocess, 'SW_HIDE'):
        subprocess.SW_HIDE = 0

_UNIT_TO_MB = {'B': 1/1048576, 'BYTES': 1/1048576, 'KB': 1/1024,
               'MB': 1.0, 'GB': 1024.0, 'TB': 1048576.0}


def run_uwfmgr(args):
    """Run uwfmgr.exe silently and return decoded output."""
    startupinfo, creationflags = None, 0
    if sys.platform == 'win32':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = subprocess.CREATE_NO_WINDOW
    result = subprocess.run(['uwfmgr.exe'] + args, capture_output=True, timeout=5,
                            startupinfo=startupinfo, creationflags=creationflags)
    raw = result.stdout
    if b'\x00' in raw:
        return raw.decode('utf-16-le', errors='ignore')
    return raw.decode('utf-8', errors='ignore')


def parse_size_mb(output, keyword):
    """Extract a size (in MB) from uwfmgr output, preferring the line with `keyword`."""
    pattern = re.compile(r'(\d[\d,\.]*)\s*(bytes|B|KB|MB|GB|TB)\b', re.IGNORECASE)
    lines = [l for l in output.splitlines() if keyword.lower() in l.lower()]
    for text in lines + [output]:
        matches = pattern.findall(text)
        if matches:
            num, unit = matches[-1]
            try:
                return float(num.replace(',', '')) * _UNIT_TO_MB.get(unit.upper(), 1.0)
            except ValueError:
                continue
    for line in lines:  # number without unit -> assume MB
        m = re.search(r'(\d[\d,\.]*)', line)
        if m:
            try:
                return float(m.group(1).replace(',', ''))
            except ValueError:
                pass
    return None


def format_size(mb):
    if mb is None:
        return "?"
    return f"{mb / 1024:.1f} GB" if mb >= 1024 else f"{mb:.0f} MB"


def usage_bar(percent, width=20):
    filled = max(0, min(width, int(round(width * percent / 100.0))))
    return "\u2588" * filled + "\u2591" * (width - filled)


class UWFMonitor(QObject):
    status_changed = pyqtSignal(bool, str, float, float)

    def __init__(self):
        super().__init__()
        self.is_protected = False
        self.overlay_info = ""
        self.used_mb = -1.0
        self.total_mb = -1.0

    def get_overlay_usage(self):
        """Return (used_mb, total_mb) of the UWF overlay, or (-1, -1)."""
        try:
            used = parse_size_mb(run_uwfmgr(['overlay', 'get-consumption']), 'consumption')
            avail = parse_size_mb(run_uwfmgr(['overlay', 'get-availablespace']), 'available')
            if used is None or avail is None:
                return -1.0, -1.0
            return used, used + avail
        except Exception:
            return -1.0, -1.0

    def check_uwf_status(self):
        try:
            filter_on = bool(re.search(r'Filter\s+state:\s+ON', run_uwfmgr(['get-config'])))
            volume_protected = bool(re.search(r'Volume\s+state:\s+Protected',
                                              run_uwfmgr(['volume', 'get-config', 'c:'])))
            is_protected = filter_on and volume_protected
            status_msg = (f"Filter: {'ON' if filter_on else 'OFF'}, "
                          f"Volume C: {'Protected' if volume_protected else 'Unprotected'}")
            used_mb, total_mb = self.get_overlay_usage()

            if (is_protected, status_msg, used_mb, total_mb) != \
               (self.is_protected, self.overlay_info, self.used_mb, self.total_mb):
                self.is_protected, self.overlay_info = is_protected, status_msg
                self.used_mb, self.total_mb = used_mb, total_mb
                self.status_changed.emit(is_protected, status_msg, used_mb, total_mb)
        except Exception:
            pass


class UWFTrayIcon(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.monitor = UWFMonitor()
        self.monitor.status_changed.connect(self.update_icon)
        self.create_menu()
        self.update_icon(False, "Checking...", -1.0, -1.0)

        self.timer = QTimer()
        self.timer.timeout.connect(self.monitor.check_uwf_status)
        self.timer.start(5000)
        threading.Thread(target=self.monitor.check_uwf_status, daemon=True).start()
        self.show()

    def create_icon(self, is_protected, percent=None):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing)

        p.setBrush(QColor(0, 200, 0) if is_protected else QColor(200, 0, 0))
        p.setPen(Qt.NoPen)
        p.drawEllipse(4, 4, 56, 56)
        p.setPen(QColor(255, 255, 255))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(4, 4, 56, 56)

        # Drive-style usage bar (like "This PC")
        if percent is not None:
            x, y, w, h = 4, 46, 56, 14
            p.setPen(QColor(60, 60, 60))
            p.setBrush(QColor(230, 230, 230))
            p.drawRect(x, y, w, h)
            fill_w = int((w - 2) * max(0.0, min(100.0, percent)) / 100.0)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(218, 38, 38) if percent >= 90 else QColor(38, 160, 218))
            p.drawRect(x + 1, y + 1, fill_w, h - 1)

        p.end()
        return QIcon(pixmap)

    def update_icon(self, is_protected, overlay_info, used_mb, total_mb):
        percent = used_mb / total_mb * 100.0 if (used_mb >= 0 and total_mb > 0) else None
        self.setIcon(self.create_icon(is_protected, percent))
        status_text = "System is Protected" if is_protected else "System is Unprotected"

        if percent is not None:
            usage_line = (f"Overlay: {format_size(used_mb)} used of "
                          f"{format_size(total_mb)} ({percent:.1f}%)")
            tooltip = (f"{overlay_info}\n{status_text}\n{usage_line}\n"
                       f"[{usage_bar(percent)}]\n"
                       f"{format_size(total_mb - used_mb)} free of {format_size(total_mb)}")
        else:
            usage_line = "Overlay: usage unavailable"
            tooltip = f"{overlay_info}\n{status_text}\n{usage_line}"

        self.setToolTip(tooltip[:127])  # Windows tooltip limit
        self.usage_action.setText(usage_line)

    def create_menu(self):
        menu = QMenu()
        self.usage_action = menu.addAction("Overlay: checking...")
        self.usage_action.setEnabled(False)
        menu.addSeparator()
        menu.addAction("Refresh Status").triggered.connect(lambda: threading.Thread(
            target=self.monitor.check_uwf_status, daemon=True).start())
        menu.addSeparator()
        menu.addAction("Show UWF Info").triggered.connect(self.show_overlay_info)
        menu.addSeparator()
        menu.addAction("Exit").triggered.connect(QApplication.quit)
        self.setContextMenu(menu)
        self._menu = menu

    def show_overlay_info(self):
        try:
            filter_output = run_uwfmgr(['get-config'])
            volume_output = run_uwfmgr(['volume', 'get-config', 'c:'])
            used_mb, total_mb = self.monitor.get_overlay_usage()
            if used_mb >= 0 and total_mb > 0:
                usage = (f"Overlay: {format_size(used_mb)} used of {format_size(total_mb)} "
                         f"({used_mb / total_mb * 100:.1f}%)\n"
                         f"{format_size(total_mb - used_mb)} free")
            else:
                usage = "Overlay usage unavailable"
            info = (f"{usage}\n\nFilter Configuration:\n{filter_output}"
                    f"\n\nVolume C: Configuration:\n{volume_output}")
            self.showMessage("UWF Status Information", info,
                             QSystemTrayIcon.Information, 5000)
        except Exception:
            self.showMessage("Error", "Failed to get UWF info",
                             QSystemTrayIcon.Critical, 3000)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray_icon = UWFTrayIcon()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
