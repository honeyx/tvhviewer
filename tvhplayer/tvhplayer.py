from datetime import datetime, timedelta
import sys
import os

# When running as a PyInstaller-frozen executable, make sure Qt can find
# its platform plugin (qwindows.dll / libqxcb.so etc.). PyInstaller's
# --collect-all PyQt5 bundles it under PyQt5/Qt5/plugins, which isn't
# where Qt looks by default - without this, the app fails to start with
# "no Qt platform plugin could be initialized".
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _bundled_plugin_dir = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt5', 'plugins')
    if os.path.isdir(_bundled_plugin_dir):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(_bundled_plugin_dir, 'platforms')
        os.environ.setdefault('QT_PLUGIN_PATH', _bundled_plugin_dir)

import vlc
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QToolBar, QComboBox, QAction, QSplitter, QFrame,
    QListWidget, QDialog, QFormLayout, QLineEdit,
    QDialogButtonBox, QMessageBox, QApplication,
    QPushButton, QLabel, QSlider, QStatusBar, QGridLayout, QMenuBar, QRadioButton, QSpinBox, QGraphicsOpacityEffect, QFileDialog,
    QMenu, QListWidgetItem, QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QTextEdit, QSizePolicy, QToolButton, QShortcut, QCheckBox, QGroupBox,  # Added QGroupBox here
    QScrollArea, QActionGroup, QAbstractItemView, QStackedWidget, QWidgetAction
)
from PyQt5.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, QAbstractAnimation, QRect, QRectF, QCoreApplication, QDateTime, pyqtSignal
from PyQt5.QtGui import QIcon, QPainter, QColor, QKeySequence, QPalette, QBrush, QPen, QFont, QFontMetrics
import json
import requests
# Note: this app loads all icons via filesystem paths (see get_icon()),
# not Qt's compiled resource system, so no resources_rc import is needed.
import time
import subprocess
import os
import traceback
from pathlib import Path
import logging
import platform


# ---------------------------------------------------------------------------
# Themes (compact panels, blue accent, clear grid lines)
# ---------------------------------------------------------------------------

DARK_THEME = {
    'window_bg': '#20242a',
    'panel_bg': '#262b33',
    'alt_row': '#2c313a',
    'border': '#3a4048',
    'text': '#e0e3e8',
    'text_dim': '#9aa2ad',
    'accent': '#3d8ef8',
    'accent_dark': '#2d6fd0',
    'header_bg': '#1a1d22',
    'now_line': '#ff5a5a',
    'epg_now': '#2d4a6b',
    'epg_future': '#2c313a',
    'epg_border': '#3a4048',
}

LIGHT_THEME = {
    'window_bg': '#eef1f5',
    'panel_bg': '#ffffff',
    'alt_row': '#f3f5f8',
    'border': '#c7ccd3',
    'text': '#20242a',
    'text_dim': '#5b6270',
    'accent': '#2f7cd6',
    'accent_dark': '#2266b8',
    'header_bg': '#dde3ea',
    'now_line': '#e03030',
    'epg_now': '#cfe1f7',
    'epg_future': '#f3f5f8',
    'epg_border': '#c7ccd3',
}


def build_stylesheet(c):
    """Build a Qt stylesheet from a color dict."""
    return f"""
    QMainWindow, QDialog, QWidget#centralArea {{
        background-color: {c['window_bg']};
    }}
    QWidget {{
        color: {c['text']};
        selection-background-color: {c['accent']};
        selection-color: #ffffff;
        font-size: 13px;
    }}
    QMenuBar {{
        background-color: {c['header_bg']};
        color: {c['text']};
        border-bottom: 1px solid {c['border']};
        padding: 2px;
    }}
    QMenuBar::item {{
        background: transparent;
        padding: 4px 10px;
        border-radius: 4px;
    }}
    QMenuBar::item:selected {{
        background: {c['accent']};
        color: #ffffff;
    }}
    QMenu {{
        background-color: {c['panel_bg']};
        color: {c['text']};
        border: 1px solid {c['border']};
    }}
    QMenu::item {{
        padding: 5px 22px;
    }}
    QMenu::item:selected {{
        background-color: {c['accent']};
        color: #ffffff;
    }}
    QToolBar {{
        background-color: {c['header_bg']};
        border-bottom: 1px solid {c['border']};
        spacing: 4px;
        padding: 3px;
    }}
    QToolBar::separator {{
        background-color: {c['border']};
        width: 1px;
        margin: 4px 6px;
    }}
    QToolButton {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 5px;
        padding: 4px;
    }}
    QToolButton:hover {{
        background-color: {c['alt_row']};
        border: 1px solid {c['border']};
    }}
    QToolButton:pressed, QToolButton:checked {{
        background-color: {c['accent']};
    }}
    QStatusBar {{
        background-color: {c['header_bg']};
        color: {c['text_dim']};
        border-top: 1px solid {c['border']};
    }}
    QStatusBar::item {{
        border: none;
    }}
    QFrame {{
        color: {c['text']};
    }}
    QSplitter::handle {{
        background-color: {c['border']};
    }}
    QSplitter::handle:horizontal {{
        width: 2px;
    }}
    QTableWidget, QListWidget, QTreeWidget, QListView, QTreeView, QColumnView {{
        background-color: {c['panel_bg']};
        alternate-background-color: {c['alt_row']};
        gridline-color: {c['border']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        color: {c['text']};
    }}
    QTableWidget::item, QListWidget::item, QListView::item, QTreeView::item {{
        padding: 3px;
        color: {c['text']};
    }}
    QTableWidget::item:selected, QListWidget::item:selected, QListView::item:selected, QTreeView::item:selected {{
        background-color: {c['accent']};
        color: #ffffff;
    }}
    QFileDialog {{
        background-color: {c['window_bg']};
        color: {c['text']};
    }}
    QFileDialog QWidget {{
        color: {c['text']};
    }}
    QFileDialog QLineEdit, QFileDialog QComboBox {{
        background-color: {c['panel_bg']};
        color: {c['text']};
    }}
    QSidebar, QFileDialog QListView, QFileDialog QTreeView {{
        background-color: {c['panel_bg']};
        color: {c['text']};
    }}
    QFileDialog QToolButton, QFileDialog QPushButton {{
        background-color: {c['panel_bg']};
        color: {c['text']};
        border: 1px solid {c['border']};
    }}
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        background-color: {c['panel_bg']};
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: {c['header_bg']};
        color: {c['text']};
        padding: 6px 14px;
        border: 1px solid {c['border']};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background-color: {c['panel_bg']};
        color: {c['text']};
    }}
    QTabBar::tab:!selected {{
        color: {c['text_dim']};
    }}
    QTabBar::tab:hover {{
        background-color: {c['alt_row']};
        color: {c['text']};
    }}
    QTextEdit, QPlainTextEdit, QTextBrowser {{
        background-color: {c['panel_bg']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        selection-background-color: {c['accent']};
        selection-color: #ffffff;
    }}
    QHeaderView::section {{
        background-color: {c['header_bg']};
        color: {c['text_dim']};
        padding: 5px;
        border: none;
        border-bottom: 1px solid {c['border']};
        border-right: 1px solid {c['border']};
    }}
    QComboBox, QLineEdit, QSpinBox {{
        background-color: {c['panel_bg']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        padding: 3px 5px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c['panel_bg']};
        selection-background-color: {c['accent']};
    }}
    QPushButton {{
        background-color: {c['panel_bg']};
        border: 1px solid {c['border']};
        border-radius: 5px;
        padding: 5px 10px;
    }}
    QPushButton:hover {{
        background-color: {c['alt_row']};
        border-color: {c['accent']};
    }}
    QPushButton:pressed {{
        background-color: {c['accent']};
        color: #ffffff;
    }}
    QScrollBar:vertical {{
        background: {c['panel_bg']};
        width: 12px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border']};
        min-height: 24px;
        border-radius: 5px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['accent']};
    }}
    QScrollBar:horizontal {{
        background: {c['panel_bg']};
        height: 12px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['border']};
        min-width: 24px;
        border-radius: 5px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {c['accent']};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0px;
        width: 0px;
    }}
    QLabel#serverLabel {{
        color: {c['text_dim']};
    }}
    """


class Logger:
    def __init__(self, name="TVHplayer"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Create logs directory
        log_dir = Path.home() / '.tvhplayer' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f'tvhplayer_{timestamp}.log'
        
        # File handler with detailed formatting
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler with simpler formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Store log file path
        self.log_file = log_file
        
        # Log system info at startup
        self.log_system_info()
    
    def log_system_info(self):
        """Log detailed system information"""
        import platform
        import sys
        try:
            import psutil
        except ImportError:
            psutil = None
        
        self.logger.info("=== System Information ===")
        self.logger.info(f"OS: {platform.platform()}")
        self.logger.info(f"Python: {sys.version}")
        self.logger.info(f"CPU: {platform.processor()}")
        
        if psutil:
            self.logger.info(f"Memory: {psutil.virtual_memory().total / (1024**3):.2f} GB")
            self.logger.info(f"Disk Space: {psutil.disk_usage('/').free / (1024**3):.2f} GB free")
        
        # Log environment variables
        self.logger.info("=== Environment Variables ===")
        for key, value in os.environ.items():
            if any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key', 'token']):
                self.logger.info(f"{key}=<REDACTED>")
            else:
                self.logger.info(f"{key}={value}")
        
        self.logger.info("=== Dependencies ===")
        try:
            import PyQt5
            self.logger.info(f"PyQt5 version: {PyQt5.QtCore.QT_VERSION_STR}")
        except ImportError:
            self.logger.error("PyQt5 not found")
        
        try:
            import vlc
            self.logger.info(f"python-vlc version: {vlc.__version__}")
        except ImportError:
            self.logger.error("python-vlc not found")
        
        try:
            import requests
            self.logger.info(f"requests version: {requests.__version__}")
        except ImportError:
            self.logger.error("requests not found")
    
    def debug(self, msg):
        self.logger.debug(msg)
    
    def info(self, msg):
        self.logger.info(msg)
    
    def warning(self, msg):
        self.logger.warning(msg)
    
    def error(self, msg):
        self.logger.error(msg)
    
    def critical(self, msg):
        self.logger.critical(msg)
    
    def exception(self, msg):
        self.logger.exception(msg)

class DVRStatusDialog(QDialog):
    def __init__(self, server, parent=None):
        super().__init__(parent)
        self.server = server
        self.setWindowTitle("DVR Status")
        self.resize(800, 600)
        self.setup_ui()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(5000)  # Update every 5 seconds
        
        # Initial update
        self.update_status()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Upcoming/Current recordings tab
        self.upcoming_table = QTableWidget()
        self.upcoming_table.setColumnCount(5)  # Added one more column for status
        self.upcoming_table.setHorizontalHeaderLabels(['Channel', 'Title', 'Start Time', 'Duration', 'Status'])
        self.upcoming_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabs.addTab(self.upcoming_table, "Upcoming/Current")  # Changed tab title
        
        # Finished recordings tab
        self.finished_table = QTableWidget()
        self.finished_table.setColumnCount(4)
        self.finished_table.setHorizontalHeaderLabels(['Channel', 'Title', 'Start Time', 'Duration'])
        self.finished_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabs.addTab(self.finished_table, "Finished")
        
        # Failed recordings tab
        self.failed_table = QTableWidget()
        self.failed_table.setColumnCount(4)
        self.failed_table.setHorizontalHeaderLabels(['Channel', 'Title', 'Start Time', 'Error'])
        self.failed_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabs.addTab(self.failed_table, "Failed")
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
    def update_status(self):
        try:
            # Create auth if needed
            auth = None
            if self.server.get('username') or self.server.get('password'):
                auth = (self.server.get('username', ''), self.server.get('password', ''))
            
            # Get DVR entries
            api_url = f'{self.server["url"]}/api/dvr/entry/grid'
            response = requests.get(api_url, auth=auth)
            
            if response.status_code == 200:
                data = response.json()
                entries = data.get('entries', [])
                print(f"Debug: Found {len(entries)} DVR entries")
                
                # Sort entries by status
                upcoming = []
                finished = []
                failed = []
                
                for entry in entries:
                    status = entry.get('status', '')  # Don't convert to lowercase yet
                    sched_status = entry.get('sched_status', '').lower()
                    errors = entry.get('errors', 0)
                    error_code = entry.get('errorcode', 0)
                    
                    print(f"\nDebug: Processing entry: {entry.get('disp_title', 'Unknown')}")
                    print(f"  Status: {status}")
                    print(f"  Sched Status: {sched_status}")
                    
                    # Check status (case-sensitive for "Running")
                    if status == "Running":
                        print(f"Debug: Found active recording: {entry.get('disp_title', 'Unknown')}")
                        upcoming.append((entry.get('channelname', 'Unknown'), entry.get('disp_title', 'Unknown'), datetime.fromtimestamp(entry.get('start', 0)), timedelta(seconds=entry.get('duration', 0)), True))
                    elif 'scheduled' in status.lower() or sched_status == 'scheduled':
                        upcoming.append((entry.get('channelname', 'Unknown'), entry.get('disp_title', 'Unknown'), datetime.fromtimestamp(entry.get('start', 0)), timedelta(seconds=entry.get('duration', 0)), False))
                    elif 'completed' in status.lower() or status.lower() == 'finished':
                        finished.append((entry.get('channelname', 'Unknown'), entry.get('disp_title', 'Unknown'), datetime.fromtimestamp(entry.get('start', 0)), timedelta(seconds=entry.get('duration', 0))))
                    elif ('failed' in status.lower() or 'invalid' in status.lower() or 
                          'error' in status.lower() or errors > 0 or error_code != 0):
                        error_msg = entry.get('error', '')
                        if not error_msg and errors > 0:
                            error_msg = f"Recording failed with {errors} errors"
                        if not error_msg and error_code != 0:
                            error_msg = f"Error code: {error_code}"
                        if not error_msg:
                            error_msg = "Unknown error"
                        failed.append((entry.get('channelname', 'Unknown'), entry.get('disp_title', 'Unknown'), datetime.fromtimestamp(entry.get('start', 0)), error_msg))
                        print(f"Debug: Added to failed: {entry.get('disp_title', 'Unknown')} (Error: {error_msg})")
                    else:
                        print(f"Debug: Unhandled status: {status} for entry: {entry.get('disp_title', 'Unknown')}")
                
                print(f"\nDebug: Sorted entries - Upcoming: {len(upcoming)}, "
                      f"Finished: {len(finished)}, Failed: {len(failed)}")
                
                # Sort upcoming recordings by start time
                upcoming.sort(key=lambda x: x[2])  # Sort by start_time
                
                # Update tables
                self.upcoming_table.setRowCount(len(upcoming))
                for i, (channel, title, start, duration, is_recording) in enumerate(upcoming):
                    self.upcoming_table.setItem(i, 0, QTableWidgetItem(channel))
                    self.upcoming_table.setItem(i, 1, QTableWidgetItem(title))
                    self.upcoming_table.setItem(i, 2, QTableWidgetItem(start.strftime('%Y-%m-%d %H:%M')))
                    self.upcoming_table.setItem(i, 3, QTableWidgetItem(str(duration)))
                    
                    # Add status column
                    status = "Recording" if is_recording else entry.get('sched_status', 'scheduled').capitalize()
                    self.upcoming_table.setItem(i, 4, QTableWidgetItem(status))
                    
                    # Highlight currently recording entries
                    if is_recording:
                        for col in range(5):  # Update range to include new column
                            self.upcoming_table.item(i, col).setBackground(Qt.green)
                
                # Sort finished recordings by start time (most recent first)
                finished.sort(key=lambda x: x[2], reverse=True)
                
                self.finished_table.setRowCount(len(finished))
                for i, (channel, title, start, duration) in enumerate(finished):
                    self.finished_table.setItem(i, 0, QTableWidgetItem(channel))
                    self.finished_table.setItem(i, 1, QTableWidgetItem(title))
                    self.finished_table.setItem(i, 2, QTableWidgetItem(start.strftime('%Y-%m-%d %H:%M')))
                    self.finished_table.setItem(i, 3, QTableWidgetItem(str(duration)))
                
                # Sort failed recordings by start time (most recent first)
                failed.sort(key=lambda x: x[2], reverse=True)
                
                self.failed_table.setRowCount(len(failed))
                for i, (channel, title, start, error) in enumerate(failed):
                    self.failed_table.setItem(i, 0, QTableWidgetItem(channel))
                    self.failed_table.setItem(i, 1, QTableWidgetItem(title))
                    self.failed_table.setItem(i, 2, QTableWidgetItem(start.strftime('%Y-%m-%d %H:%M')))
                    self.failed_table.setItem(i, 3, QTableWidgetItem(error))
                    # Highlight failed entries in red
                    for col in range(4):
                        self.failed_table.item(i, col).setBackground(Qt.red)
                
            else:
                print(f"Debug: Failed to fetch DVR entries. Status code: {response.status_code}")
                
        except Exception as e:
            print(f"Debug: Error updating DVR status: {str(e)}")
            print(f"Debug: Traceback: {traceback.format_exc()}")
    
    def closeEvent(self, event):
        self.update_timer.stop()
        super().closeEvent(event)

class RecordingDurationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recording Duration")
        self.setModal(True)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Quick duration buttons
        quick_duration_layout = QHBoxLayout()
        
        btn_30min = QPushButton("30 minutes")
        btn_1hr = QPushButton("1 hour") 
        btn_2hr = QPushButton("2 hours")
        btn_4hr = QPushButton("4 hours")
        
        btn_30min.clicked.connect(lambda: self.set_duration(0, 30))
        btn_1hr.clicked.connect(lambda: self.set_duration(1, 0))
        btn_2hr.clicked.connect(lambda: self.set_duration(2, 0))
        btn_4hr.clicked.connect(lambda: self.set_duration(4, 0))
        
        quick_duration_layout.addWidget(btn_30min)
        quick_duration_layout.addWidget(btn_1hr)
        quick_duration_layout.addWidget(btn_2hr)
        quick_duration_layout.addWidget(btn_4hr)
        
        layout.addLayout(quick_duration_layout)

        # Duration spinboxes
        duration_layout = QHBoxLayout()
        
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 24)
        self.hours_spin.setSuffix(" hours")
        
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setSuffix(" minutes")
        
        duration_layout.addWidget(self.hours_spin)
        duration_layout.addWidget(self.minutes_spin)
        
        layout.addWidget(QLabel("Set custome recording duration:"))
        layout.addLayout(duration_layout)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def set_duration(self, hours, minutes):
        self.hours_spin.setValue(hours)
        self.minutes_spin.setValue(minutes)
    def get_duration(self):
        """Return duration in seconds"""
        hours = self.hours_spin.value()
        minutes = self.minutes_spin.value()
        return (hours * 3600) + (minutes * 60)

class ServerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Server Management")
        self.setModal(True)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Server list
        self.server_list = QListWidget()
        layout.addWidget(QLabel("Configured Servers:"))
        layout.addWidget(self.server_list)
        
        # Connect double-click signal
        self.server_list.itemDoubleClicked.connect(self.edit_server)
        
        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Server")
        edit_btn = QPushButton("Edit Server")
        remove_btn = QPushButton("Remove Server")
        
        add_btn.clicked.connect(self.add_server)
        edit_btn.clicked.connect(self.edit_server)
        remove_btn.clicked.connect(self.remove_server)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(remove_btn)
        layout.addLayout(btn_layout)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
    def load_servers(self, servers):
        self.servers = servers
        self.server_list.clear()
        for server in self.servers:
            self.server_list.addItem(server['name'])
            
    def add_server(self):
        print("Debug: Opening add server dialog")
        dialog = ServerConfigDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            server = dialog.get_server_config()
            print(f"Debug: Adding new server: {server['name']}")
            self.servers.append(server)
            self.server_list.addItem(server['name'])
            
    def edit_server(self):
        current_row = self.server_list.currentRow()
        if current_row >= 0:
            print(f"Debug: Editing server at index {current_row}")
            dialog = ServerConfigDialog(self)
            dialog.set_server_config(self.servers[current_row])
            if dialog.exec_() == QDialog.Accepted:
                self.servers[current_row] = dialog.get_server_config()
                print(f"Debug: Updated server: {self.servers[current_row]['name']}")
                self.server_list.item(current_row).setText(self.servers[current_row]['name'])
                
    def remove_server(self):
        current_row = self.server_list.currentRow()
        if current_row >= 0:
            server_name = self.servers[current_row]['name']
            print(f"Debug: Removing server: {server_name}")
            self.servers.pop(current_row)
            self.server_list.takeItem(current_row)
        else:
            print("Debug: No server selected for removal")
            
class ServerConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Server Configuration")
        self.setModal(True)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit()
        self.url_input = QLineEdit()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        # Style placeholder text
        placeholder_color = QColor(100, 100, 100)  # Dark gray color
        palette = self.palette()
        palette.setColor(QPalette.PlaceholderText, placeholder_color)
        self.setPalette(palette)
        
        # Apply placeholder text
        layout.addRow("Name:", self.name_input)
        self.name_input.setPlaceholderText("My Server")
        layout.addRow("Server address:", self.url_input)
        self.url_input.setPlaceholderText("http://127.0.0.1:9981")
        layout.addRow("Username:", self.username_input)
        self.username_input.setPlaceholderText("Optional")
        layout.addRow("Password:", self.password_input)
        self.password_input.setPlaceholderText("Optional")
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_server_config(self):
        return {
            'name': self.name_input.text(),
            'url': self.url_input.text(),
            'username': self.username_input.text(),
            'password': self.password_input.text()
        }
        
    def set_server_config(self, config):
        self.name_input.setText(config.get('name', ''))
        self.url_input.setText(config.get('url', ''))
        self.username_input.setText(config.get('username', ''))
        self.password_input.setText(config.get('password', ''))

    def validate_url(self, url):
        """Validate server URL format"""
        if not url.startswith('http://') and not url.startswith('https://'):
            return False, "URL must start with http:// or https://"
            
        # Remove http:// or https:// for validation
        if url.startswith('http://'):
            url = url[7:]
        else:  # https://
            url = url[8:]
            
        # Split URL into host:port and path parts
        url_parts = url.split('/', 1)
        host_port = url_parts[0]
            
        # Split host and port
        if ':' in host_port:
            host, port = host_port.split(':')
            # Validate port
            try:
                port = int(port)
                if port < 1 or port > 65535:
                    return False, "Port must be between 1 and 65535"
            except ValueError:
                return False, "Invalid port number"
        else:
            host = host_port
            
        # Validate IP address format if it looks like an IP
        if all(c.isdigit() or c == '.' for c in host):
            parts = host.split('.')
            if len(parts) != 4:
                return False, "Invalid IP address format"
            for part in parts:
                try:
                    num = int(part)
                    if num < 0 or num > 255:
                        return False, "IP numbers must be between 0 and 255"
                except ValueError:
                    return False, "Invalid IP address format"
                    
        return True, ""

    def accept(self):
        print("Debug: Validating server configuration")
        config = self.get_server_config()
        print(f"Debug: Server config: {config['name']} @ {config['url']}")
        
        if not config['name']:
            QMessageBox.warning(self, "Invalid Configuration",
                              "Please provide a server name")
            return
            
        if not config['url']:
            QMessageBox.warning(self, "Invalid Configuration",
                              "Please provide a server URL")
            return
            
        # Validate URL format
        is_valid, error_msg = self.validate_url(config['url'])
        if not is_valid:
            QMessageBox.warning(self, "Invalid Configuration",
                              f"Invalid server URL: {error_msg}")
            return
            
        super().accept()
class ConnectionErrorDialog(QDialog):
    def __init__(self, server_name, error_msg, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connection Error")
        self.setup_ui(server_name, error_msg)
        
    def setup_ui(self, server_name, error_msg):
        layout = QVBoxLayout(self)
        
        # Error icon and message
        message_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(QMessageBox.standardIcon(QMessageBox.Critical))
        message_layout.addWidget(icon_label)
        
        error_text = QLabel(
            f"Failed to connect to server: {server_name}\n"
            f"Error: {error_msg}\n\n"
            "Would you like to retry the connection?"
        )
        error_text.setWordWrap(True)
        message_layout.addWidget(error_text)
        layout.addLayout(message_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        retry_btn = QPushButton("Retry")
        abort_btn = QPushButton("Abort")
        
        retry_btn.clicked.connect(self.accept)
        abort_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(retry_btn)
        button_layout.addWidget(abort_btn)
        layout.addLayout(button_layout)

class ServerStatusDialog(QDialog):
    def __init__(self, server, parent=None):
        super().__init__(parent)
        self.server = server
        self.parent = parent
        self.setWindowTitle("Server Status")
        self.resize(800, 600)
        self.setup_ui()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(5000)  # Update every 5 seconds
        
        # Initial update
        self.update_status()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Active streams/subscriptions tab
        self.subscriptions_table = QTableWidget()
        self.subscriptions_table.setColumnCount(5)
        self.subscriptions_table.setHorizontalHeaderLabels([
            'Channel/Peer', 
            'User', 
            'Start Time', 
            'Duration',
            'Type/Status'
        ])
        self.subscriptions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabs.addTab(self.subscriptions_table, "Active Streams")
        
        # Signal Status tab (new)
        self.signal_table = QTableWidget()
        self.signal_table.setColumnCount(5)
        self.signal_table.setHorizontalHeaderLabels([
            'Input', 
            'Signal Strength', 
            'SNR',
            'Stream',
            'Weight'
        ])
        self.signal_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabs.addTab(self.signal_table, "Signal Status")
        
        # Server info tab
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.tabs.addTab(self.info_text, "Server Info")
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
    def update_status(self):
        try:
            auth = None
            if self.server.get('username') or self.server.get('password'):
                auth = (self.server.get('username', ''), self.server.get('password', ''))

            # 1. Update Server Info Tab
            server_info = f"Server Information:\n\n"
            server_info += f"Name: {self.server.get('name', 'Unknown')}\n"
            server_info += f"URL: {self.server.get('url', 'Unknown')}\n"
            
            # Get server version and capabilities
            version_url = f"{self.server['url']}/api/serverinfo"
            try:
                version_response = requests.get(version_url, auth=auth)
                if version_response.status_code == 200:
                    server_data = version_response.json()
                    server_info += f"\nServer Version: {server_data.get('sw_version', 'Unknown')}\n"
                    server_info += f"API Version: {server_data.get('api_version', 'Unknown')}\n"
                    server_info += f"Server Name: {server_data.get('server_name', 'Unknown')}\n"
                    
                    if 'capabilities' in server_data:
                        server_info += "\nCapabilities:\n"
                        for cap in server_data['capabilities']:
                            server_info += f"- {cap}\n"
            except Exception as e:
                server_info += f"\nError fetching server info: {str(e)}\n"
            
            self.info_text.setText(server_info)

            # 2. Update Signal Status Tab
            inputs_url = f"{self.server['url']}/api/status/inputs"
            try:
                inputs_response = requests.get(inputs_url, auth=auth)
                
                if inputs_response.status_code == 200:
                    inputs = inputs_response.json().get('entries', [])
                    
                    # Set up table with double the rows (signal and SNR on separate rows)
                    self.signal_table.setRowCount(len(inputs) * 2)
                    
                    for i, input in enumerate(inputs):
                        # Base row for this input (multiply by 2 since we're using 2 rows per input)
                        base_row = i * 2
                        
                        # Input name spans both rows
                        input_item = QTableWidgetItem(str(input.get('input', 'Unknown')))
                        self.signal_table.setItem(base_row, 0, input_item)
                        self.signal_table.setSpan(base_row, 0, 2, 1)  # Span 2 rows
                        
                        # Signal row
                        signal = input.get('signal')
                        signal_scale = input.get('signal_scale', 0)
                        if signal is not None and signal_scale > 0:
                            if signal_scale == 1:  # Relative (65535 = 100%)
                                signal_value = f"{(signal * 100 / 65535):.1f}%"
                            elif signal_scale == 2:  # Absolute (1000 = 1dB)
                                signal_value = f"{(signal / 1000):.1f} dB"
                            else:
                                signal_value = "N/A"
                        else:
                            signal_value = "N/A"
                        
                        signal_item = QTableWidgetItem(signal_value)
                        self.signal_table.setItem(base_row, 1, signal_item)
                        self.signal_table.setItem(base_row, 2, QTableWidgetItem("Signal"))
                        
                        # SNR row
                        snr = input.get('snr')
                        snr_scale = input.get('snr_scale', 0)
                        if snr is not None and snr_scale > 0:
                            if snr_scale == 1:  # Relative (65535 = 100%)
                                snr_value = f"{(snr * 100 / 65535):.1f}%"
                            elif snr_scale == 2:  # Absolute (1000 = 1dB)
                                snr_value = f"{(snr / 1000):.1f} dB"
                            else:
                                snr_value = "N/A"
                        else:
                            snr_value = "N/A"
                        
                        snr_item = QTableWidgetItem(snr_value)
                        self.signal_table.setItem(base_row + 1, 1, snr_item)
                        self.signal_table.setItem(base_row + 1, 2, QTableWidgetItem("SNR"))
                        
                        # Stream and Weight info (spans both rows)
                        self.signal_table.setItem(base_row, 3, QTableWidgetItem(str(input.get('stream', 'N/A'))))
                        self.signal_table.setItem(base_row, 4, QTableWidgetItem(str(input.get('weight', 'N/A'))))
                        self.signal_table.setSpan(base_row, 3, 2, 1)  # Span 2 rows for stream
                        self.signal_table.setSpan(base_row, 4, 2, 1)  # Span 2 rows for weight
                        
                        # Color coding for signal and SNR
                        self.color_code_cell(signal_item, signal, signal_scale, 'signal')
                        self.color_code_cell(snr_item, snr, snr_scale, 'snr')
            except Exception as e:
                print(f"Debug: Error updating signal status: {str(e)}")

            # 3. Update Active Streams Tab
            connections_url = f"{self.server['url']}/api/status/connections"
            subscriptions_url = f"{self.server['url']}/api/status/subscriptions"
            
            try:
                # Get both connections and subscriptions
                connections_response = requests.get(connections_url, auth=auth)
                subscriptions_response = requests.get(subscriptions_url, auth=auth)
                
                if connections_response.status_code == 200 and subscriptions_response.status_code == 200:
                    connections = connections_response.json().get('entries', [])
                    subscriptions = subscriptions_response.json().get('entries', [])
                    
                    # Calculate total rows needed (connections + subscriptions)
                    total_rows = len(connections) + len(subscriptions)
                    self.subscriptions_table.setRowCount(total_rows)
                    
                    # Add connections
                    row = 0
                    for conn in connections:
                        # Peer (IP address/hostname)
                        peer = conn.get('peer', 'Unknown')
                        self.subscriptions_table.setItem(row, 0, QTableWidgetItem(str(peer)))
                        self.subscriptions_table.setItem(row, 1, QTableWidgetItem(str(conn.get('user', 'N/A'))))
                        
                        # Start time
                        start = datetime.fromtimestamp(conn.get('started', 0)).strftime('%H:%M:%S')
                        self.subscriptions_table.setItem(row, 2, QTableWidgetItem(start))
                        
                        # Duration
                        duration = int(time.time() - conn.get('started', 0))
                        hours = duration // 3600
                        minutes = (duration % 3600) // 60
                        seconds = duration % 60
                        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        self.subscriptions_table.setItem(row, 3, QTableWidgetItem(duration_str))
                        
                        # Type/Status
                        self.subscriptions_table.setItem(row, 4, QTableWidgetItem("Connection"))
                        
                        row += 1
                    
                    # Add subscriptions
                    for sub in subscriptions:
                        # Channel/Service name
                        channel = sub.get('channel', 'Unknown')
                        if isinstance(channel, dict):
                            channel = channel.get('name', 'Unknown')
                        self.subscriptions_table.setItem(row, 0, QTableWidgetItem(str(channel)))
                        self.subscriptions_table.setItem(row, 1, QTableWidgetItem(str(sub.get('username', 'N/A'))))
                        
                        # Start time
                        start = datetime.fromtimestamp(sub.get('start', 0)).strftime('%H:%M:%S')
                        self.subscriptions_table.setItem(row, 2, QTableWidgetItem(start))
                        
                        # Duration
                        duration = int(time.time() - sub.get('start', 0))
                        hours = duration // 3600
                        minutes = (duration % 3600) // 60
                        seconds = duration % 60
                        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        self.subscriptions_table.setItem(row, 3, QTableWidgetItem(duration_str))
                        
                        # Type/Status
                        status = f"Subscription ({sub.get('state', 'Unknown')})"
                        self.subscriptions_table.setItem(row, 4, QTableWidgetItem(status))
                        
                        row += 1

            except Exception as e:
                print(f"Debug: Error fetching connections/subscriptions: {str(e)}")

        except Exception as e:
            print(f"Debug: Error in update_status: {str(e)}")
            print(f"Debug: Traceback: {traceback.format_exc()}")

    def color_code_cell(self, item, value, scale, type='signal'):
        """Helper method to color code signal and SNR values"""
        if value is not None and scale > 0:
            if scale == 1:
                quality = (value * 100 / 65535)
            else:  # scale == 2
                if type == 'signal':
                    quality = min(100, max(0, (value / 1000 + 15) * 6.67))
                else:  # SNR
                    quality = min(100, max(0, (value / 1000 - 10) * 10))
            
            if quality >= 80:
                item.setBackground(Qt.green)
            elif quality >= 60:
                item.setBackground(Qt.yellow)
            elif quality >= 40:
                item.setBackground(Qt.darkYellow)
            else:
                item.setBackground(Qt.red)
    
    def closeEvent(self, event):
        self.update_timer.stop()
        super().closeEvent(event)

class TVHeadendClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_paths()
        
        # Get OS-specific config path using sys.platform
        if sys.platform == 'darwin':  # macOS
            self.config_dir = os.path.join(os.path.expanduser('~/Library/Application Support'), 'TVHplayer')
        elif sys.platform == 'win32':  # Windows
            self.config_dir = os.path.join(os.getenv('APPDATA'), 'TVHplayer')
        else:  # Linux/Unix
            CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
            self.config_dir = os.path.join(CONFIG_HOME, "tvhplayer")
        
        # Ensure config directory exists
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Set config file path
        self.config_file = os.path.join(self.config_dir, 'tvhplayer.conf')
        print(f"Debug: Config file location: {self.config_file}")
        self.config = self.load_config()
        print(f"Debug: Current config: {json.dumps(self.config, indent=2)}")
        print("Debug: Initializing TVHeadendClient")
        
        # Initialize fullscreen state        
        # Rest of initialization code...


        # Set window title and geometry from config
        self.setWindowTitle("TVHviewer")
        geometry = self.config.get('window_geometry', {'x': 100, 'y': 100, 'width': 1200, 'height': 700})
        self.setGeometry(
            geometry['x'],
            geometry['y'],
            geometry['width'],
            geometry['height']
        )
        
        # Initialize servers from config
        self.servers = self.config.get('servers', [])
        print(f"Debug: Loaded {len(self.servers)} servers")
        
        # Initialize channels list
        self.channels = []
        
        self.is_fullscreen = False

        # Reference to the (single) open all-channel EPG grid dialog, if any
        self._epg_grid_dialog = None

        # Tracks whichever channel is currently playing (or was last
        # played), regardless of what's selected in the (now hidden)
        # channel table - recording buttons fall back to this.
        self.current_channel_data = None

        
        # Add recording indicator variables
        self.recording_indicator_timer = None
        self.recording_indicator_visible = False
        self.is_recording = False
        self.recording_animation = None
        self.opacity_effect = None
        
        # Initialize VLC with basic instance first
        print("Debug: Initializing VLC instance")
        try:
            if getattr(sys, 'frozen', False):
                # If running as compiled executable
                base_path = sys._MEIPASS
                plugin_path = os.path.join(base_path, 'vlc', 'plugins')
                
                # Set VLC plugin path via environment variable
                os.environ['VLC_PLUGIN_PATH'] = plugin_path
                
                # On Linux, might also need these
                if sys.platform.startswith('linux'):
                    os.environ['LD_LIBRARY_PATH'] = base_path
                    
                print(f"Debug: VLC plugin path set to: {plugin_path}")
                
            # Initialize VLC with hardware acceleration parameters
            vlc_args = [
                # Enable hardware decoding
                '--avcodec-hw=any',  # Try any hardware acceleration method
                '--file-caching=1000',  # Increase file caching for smoother playback
                '--network-caching=1000',  # Increase network caching for streaming
                '--no-video-title-show',  # Don't show the video title
                '--no-snapshot-preview',  # Don't show snapshot previews
                # Let Qt handle ALL keyboard/mouse input on the embedded
                # video surface. Without these, libvlc's own hotkey layer
                # (which has its own F=fullscreen / double-click=fullscreen
                # bindings) fires *in addition* to our Qt-level toggle,
                # which caused fullscreen to get stuck or double-toggle.
                '--no-keyboard-events',
                '--no-mouse-events',
            ]
            
            self.instance = vlc.Instance(vlc_args)
            if not self.instance:
                raise RuntimeError("VLC Instance creation returned None")
                
            print("Debug: VLC instance created successfully with hardware acceleration")
            
            self.media_player = self.instance.media_player_new()
            if not self.media_player:
                raise RuntimeError("VLC media player creation returned None")
                
            print("Debug: VLC media player created successfully")
            
        except Exception as e:
            print(f"Error initializing VLC: {str(e)}")
            raise RuntimeError(f"Failed to initialize VLC: {str(e)}")
        
        # Apply color theme (dark/light) before building the UI
        self.apply_theme(self.config.get('theme', 'dark'), persist=False)

        # Then setup UI
        self.setup_ui()
        
        # Update to use config for last server
        self.server_combo.setCurrentIndex(self.config.get('last_server', 0))
        
        # Now configure hardware acceleration after UI is set up
        try:
            # Set player window - with proper type conversion
            if sys.platform.startswith('linux'):
                handle = self.video_frame.winId().__int__()
                if handle is not None:
                    self.media_player.set_xwindow(handle)
            elif sys.platform == "win32":
                self.media_player.set_hwnd(self.video_frame.winId().__int__())
            elif sys.platform == "darwin":
                self.media_player.set_nsobject(self.video_frame.winId().__int__())
            
            # Set hardware decoding to automatic
            if hasattr(self.media_player, 'set_hardware_decoding'):
                self.media_player.set_hardware_decoding(True)
            else:
                # Alternative method for older VLC Python bindings
                self.media_player.video_set_key_input(False)
                self.media_player.video_set_mouse_input(False)
            
            # Add a timer to check which hardware acceleration method is being used
            # This will check after playback starts
            self.hw_check_timer = QTimer()
            self.hw_check_timer.setSingleShot(True)
            self.hw_check_timer.timeout.connect(self.check_hardware_acceleration)
            self.hw_check_timer.start(5000)  # Check after 5 seconds of playback
                
            print("Debug: Hardware acceleration configured for VLC")
            
        except Exception as e:
            print(f"Warning: Could not configure hardware acceleration: {str(e)}")
            print("Continuing without hardware acceleration")
    
    def setup_paths(self):
        """Setup application paths for resources"""
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller bundle
            self.app_dir = Path(sys._MEIPASS)
        else:
            # Running in development
            self.app_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            
        # Ensure icons directory exists
        self.icons_dir = self.app_dir / 'icons'
        if not self.icons_dir.exists():
            print(f"Warning: Icons directory not found at {self.icons_dir}")
            # Try looking up one directory (in case we're in src/)
            self.icons_dir = self.app_dir.parent / 'icons'
            if not self.icons_dir.exists():
                # Try system icon directories
                system_icon_dirs = []
                if sys.platform.startswith('linux'):
                    system_icon_dirs = [
                        Path('/usr/share/icons/tvhplayer'),
                        Path('/usr/local/share/icons/tvhplayer'),
                        Path(os.path.expanduser('~/.local/share/icons/tvhplayer'))
                    ]
                elif sys.platform == 'darwin':
                    system_icon_dirs = [
                        Path('/System/Library/Icons'),
                        Path('/Library/Icons'),
                        Path(os.path.expanduser('~/Library/Icons'))
                    ]
                elif sys.platform == 'win32':
                    system_icon_dirs = [
                        Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / 'Icons',
                        Path(os.environ['SYSTEMROOT']) / 'System32' / 'icons'
                    ]
                
                for dir in system_icon_dirs:
                    if dir.exists():
                        self.icons_dir = dir
                        print(f"Using system icons directory: {self.icons_dir}")
                        break
                else:
                    raise RuntimeError(f"Icons directory not found in {self.app_dir}, parent directory, or system locations")
        
        print(f"Debug: Using icons directory: {self.icons_dir}")
        
    def get_icon(self, icon_name):
        """Get icon path and verify it exists"""
        # Use the already-resolved icons directory (handles the packaged/
        # installed-location fallbacks), not just app_dir/icons
        icon_path = Path(self.icons_dir) / icon_name
        if not icon_path.exists():
            print(f"Warning: Icon not found: {icon_path}")
            return None
        return str(icon_path)
    
    def apply_theme(self, theme_name, persist=True):
        """Apply the Dark or Light theme app-wide"""
        theme_name = theme_name if theme_name in ('dark', 'light') else 'dark'
        self.current_theme_name = theme_name
        self.theme = DARK_THEME if theme_name == 'dark' else LIGHT_THEME
        app = QApplication.instance()
        if app:
            app.setStyleSheet(build_stylesheet(self.theme))
        if persist:
            self.config['theme'] = theme_name
            self.save_config()
        # Keep menu checkmarks and toolbar toggle in sync if they already exist
        if hasattr(self, 'dark_theme_action'):
            self.dark_theme_action.setChecked(theme_name == 'dark')
        if hasattr(self, 'light_theme_action'):
            self.light_theme_action.setChecked(theme_name == 'light')
        # Repaint any open EPG grid so colors follow the new theme
        if hasattr(self, '_epg_grid_dialog') and self._epg_grid_dialog is not None:
            try:
                self._epg_grid_dialog.apply_theme(self.theme)
            except RuntimeError:
                pass  # dialog already closed

    def toggle_theme(self):
        """Flip between dark and light theme"""
        new_theme = 'light' if getattr(self, 'current_theme_name', 'dark') == 'dark' else 'dark'
        self.apply_theme(new_theme)

    def setup_ui(self):
        """Setup the UI elements"""

        # Create menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        channels_menu = menubar.addMenu("Channels")
        favorites_menu = menubar.addMenu("Favorites")
        view_menu = menubar.addMenu("View")
        playback_menu = menubar.addMenu("Playback")
        recording_menu = menubar.addMenu("Recording")
        epg_menu = menubar.addMenu("EPG")
        settings_menu = menubar.addMenu("Settings")
        help_menu = menubar.addMenu("Help")
        self.channels_menu = channels_menu
        self.favorites_menu = favorites_menu
        self.settings_menu = settings_menu

        # Add User Guide action to Help menu
        user_guide_action = QAction("User Guide", self)
        user_guide_action.triggered.connect(self.show_user_guide)
        help_menu.addAction(user_guide_action)
        
        # Add About action to Help menu
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        
        
        # Add Fullscreen action to View menu (key handling itself lives in
        # eventFilter below - no separate shortcut here to avoid the F key
        # firing twice and toggling fullscreen on/off in the same press)
        fullscreen_action = QAction("Fullscreen", self)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        view_menu.addSeparator()

        # Theme submenu (color scheme switch)
        theme_menu = view_menu.addMenu("Color Scheme")
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)

        self.dark_theme_action = QAction("Dark", self)
        self.dark_theme_action.setCheckable(True)
        self.dark_theme_action.setChecked(getattr(self, 'current_theme_name', 'dark') == 'dark')
        self.dark_theme_action.triggered.connect(lambda: self.apply_theme('dark'))
        theme_group.addAction(self.dark_theme_action)
        theme_menu.addAction(self.dark_theme_action)

        self.light_theme_action = QAction("Light", self)
        self.light_theme_action.setCheckable(True)
        self.light_theme_action.setChecked(getattr(self, 'current_theme_name', 'dark') == 'light')
        self.light_theme_action.triggered.connect(lambda: self.apply_theme('light'))
        theme_group.addAction(self.light_theme_action)
        theme_menu.addAction(self.light_theme_action)

        view_menu.addSeparator()
        show_channels_action = QAction("All Channels...", self)
        show_channels_action.triggered.connect(self.show_channel_dialog)
        view_menu.addAction(show_channels_action)

        # Playback menu (also mirrored as icon buttons in the toolbar below)
        play_action_menu = QAction("Play", self)
        play_action_menu.triggered.connect(lambda: self.play_btn.trigger())
        playback_menu.addAction(play_action_menu)
        stop_action_menu = QAction("Stop", self)
        stop_action_menu.triggered.connect(self.stop_playback)
        playback_menu.addAction(stop_action_menu)
        playback_menu.addSeparator()
        mute_action_menu = QAction("Toggle Mute", self)
        mute_action_menu.triggered.connect(self.toggle_mute)
        playback_menu.addAction(mute_action_menu)

        # Recording menu (server-side "instant record" is scheduled via
        # the EPG Guide instead - the old start/stop-now buttons never
        # worked reliably against Tvheadend, same as in the original app)
        start_local_rec_action_menu = QAction("Start Local Recording", self)
        start_local_rec_action_menu.triggered.connect(lambda: self.start_local_recording())
        recording_menu.addAction(start_local_rec_action_menu)
        stop_local_rec_action_menu = QAction("Stop Local Recording", self)
        stop_local_rec_action_menu.triggered.connect(self.stop_local_recording)
        recording_menu.addAction(stop_local_rec_action_menu)
        recording_menu.addSeparator()
        dvr_status_action_menu = QAction("Recording Status...", self)
        dvr_status_action_menu.triggered.connect(self.show_dvr_status)
        recording_menu.addAction(dvr_status_action_menu)

        # EPG menu
        epg_guide_action_menu = QAction("Program Guide (All Channels)...", self)
        epg_guide_action_menu.setShortcut("Ctrl+G")
        epg_guide_action_menu.triggered.connect(self.show_epg_grid)
        epg_menu.addAction(epg_guide_action_menu)

        # Settings menu: server management lives here now instead of the
        # old left-hand panel
        manage_servers_action = QAction("Manage Servers...", self)
        manage_servers_action.triggered.connect(self.manage_servers)
        settings_menu.addAction(manage_servers_action)
        self.server_menu = settings_menu.addMenu("Active Server")
        self.server_action_group = QActionGroup(self)
        self.server_action_group.setExclusive(True)
        
        # Create actions
        exit_action = QAction("Exit", self)
        if sys.platform == "darwin":  # macOS
            exit_action.setShortcut("Cmd+Q")
        else:  # Windows/Linux
            exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- Toolbar (icon toolbar below the menu bar) ---
        # This replaces the old left-hand button panels: play/stop,
        # server + local recording, mute/volume and fullscreen all live
        # here now as small icon-only controls.
        toolbar = QToolBar("Main Toolbar")
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(22, 22))
        toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.addToolBar(toolbar)

        self.play_btn = QAction(QIcon(self.get_icon('play.svg')), "Play", self)
        self.play_btn.setToolTip("Play selected channel")
        self.play_btn.triggered.connect(
            lambda: self.play_channel_by_data(
                self.channel_list.item(self.channel_list.currentRow(), 1).data(Qt.UserRole)
                if self.channel_list.currentRow() >= 0
                else (self.channel_list.item(0, 1).data(Qt.UserRole) if self.channel_list.rowCount() > 0 else None)
            )
        )
        toolbar.addAction(self.play_btn)

        self.stop_btn = QAction(QIcon(self.get_icon('stop.svg')), "Stop", self)
        self.stop_btn.setToolTip("Stop playback")
        self.stop_btn.triggered.connect(self.stop_playback)
        toolbar.addAction(self.stop_btn)

        toolbar.addSeparator()

        self.start_local_record_btn = QAction(QIcon(self.get_icon('reclocal.svg')), "Local Record", self)
        self.start_local_record_btn.setToolTip("Start local recording")
        self.start_local_record_btn.triggered.connect(lambda: self.start_local_recording())
        toolbar.addAction(self.start_local_record_btn)

        self.stop_local_record_btn = QAction(QIcon(self.get_icon('stopreclocal.svg')), "Stop Local Record", self)
        self.stop_local_record_btn.setToolTip("Stop local recording")
        self.stop_local_record_btn.triggered.connect(self.stop_local_recording)
        toolbar.addAction(self.stop_local_record_btn)

        toolbar.addSeparator()

        self.tb_epg_action = QAction(QIcon(self.get_icon('epg.svg')), "Guide", self)
        self.tb_epg_action.setToolTip("Program Guide (all channels)")
        self.tb_epg_action.triggered.connect(self.show_epg_grid)
        toolbar.addAction(self.tb_epg_action)

        toolbar.addSeparator()

        self.mute_btn = QAction(QIcon(self.get_icon('unmute.svg')), "Mute", self)
        self.mute_btn.setToolTip("Mute")
        self.mute_btn.setCheckable(True)
        self.mute_btn.triggered.connect(self.toggle_mute)
        toolbar.addAction(self.mute_btn)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(110)
        self.volume_slider.setToolTip("Volume")
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        toolbar.addWidget(self.volume_slider)
        # The slider was set above *before* connecting valueChanged, so no
        # signal fired - VLC was still at its own default even though the
        # slider itself could show a different value. Apply it explicitly
        # once so the slider position and actual volume match. Always
        # starts at 100% regardless of any previously saved value.
        self.on_volume_changed(self.volume_slider.value())

        toolbar.addSeparator()

        self.tb_fullscreen_action = QAction(QIcon(self.get_icon('fullscreen.svg')), "Fullscreen", self)
        self.tb_fullscreen_action.setToolTip("Toggle fullscreen")
        self.tb_fullscreen_action.triggered.connect(self.toggle_fullscreen)
        toolbar.addAction(self.tb_fullscreen_action)

        # Spacer pushes the theme toggle to the far right
        tb_spacer = QWidget()
        tb_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(tb_spacer)

        self.tb_theme_action = QAction(QIcon(self.get_icon('theme.svg')), "Toggle Theme", self)
        self.tb_theme_action.setToolTip("Switch between Dark and Light color scheme")
        self.tb_theme_action.triggered.connect(self.toggle_theme)
        toolbar.addAction(self.tb_theme_action)
        
        # Create main widget and layout
        main_widget = QWidget()
        main_widget.setObjectName("centralArea")
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- Channel list + server selector: no longer a visible left
        # column. They stay fully functional but live inside a separate
        # "All Channels" window opened from the Channels/View menu, so
        # the video gets the full width.
        self.channel_dialog = QDialog(self)
        self.channel_dialog.setWindowTitle("Channels")
        self.channel_dialog.resize(420, 640)
        channel_dialog_layout = QVBoxLayout(self.channel_dialog)

        server_layout = QHBoxLayout()
        self.server_combo = QComboBox()
        self.server_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for server in self.servers:
            self.server_combo.addItem(server['name'])
        self.server_combo.currentIndexChanged.connect(self.on_server_changed)

        manage_servers_btn = QToolButton()
        manage_servers_btn.clicked.connect(self.manage_servers)
        server_layout.addWidget(QLabel("Server:"))
        server_layout.addWidget(self.server_combo)
        manage_servers_btn.setText("\u2699")
        manage_servers_btn.setStyleSheet("font-size: 18px;")
        manage_servers_btn.setToolTip("Manage servers")
        server_layout.addWidget(manage_servers_btn)
        channel_dialog_layout.addLayout(server_layout)

        # Channel list
        self.channel_list = QTableWidget()
        self.channel_list.setObjectName("channelList")
        self.channel_list.setColumnCount(2)
        self.channel_list.setHorizontalHeaderLabels(['#', 'Channel Name'])
        self.channel_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.channel_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.channel_list.verticalHeader().setVisible(False)
        self.channel_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.channel_list.setSelectionMode(QTableWidget.SingleSelection)
        self.channel_list.setSortingEnabled(True)
        self.channel_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.channel_list.setAlternatingRowColors(True)
        self.channel_list.setShowGrid(False)

        # Connect double-click to play
        self.channel_list.itemDoubleClicked.connect(self.play_channel_from_table)

        # Connect context menu
        self.channel_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.channel_list.customContextMenuRequested.connect(self.show_channel_context_menu)

        channel_dialog_layout.addWidget(self.channel_list)

        # Right pane (the only thing visible in the main window now)
        right_pane = QFrame()
        right_pane.setFrameStyle(QFrame.NoFrame)
        right_layout = QVBoxLayout(right_pane)
        right_layout.setObjectName("right_layout")
        right_layout.setContentsMargins(0, 0, 0, 0)

        # VLC player widget
        self.video_frame = QWidget()
        self.video_frame.setStyleSheet("""
            background-color: black;
            background-image: url(icons/playerbg.svg);
            background-position: center;
            background-repeat: no-repeat;
        """)

        right_layout.addWidget(self.video_frame)
        layout.addWidget(right_pane)

        # Status bar setup
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # Create a container widget for status bar items
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(10)  # Space between indicator and text

        # Create recording indicator
        self.recording_indicator = QLabel()
        self.recording_indicator.setFixedSize(16, 16)
        self.recording_indicator.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 0, 0, 0.8);
                min-width: 16px;
                max-width: 16px;
                min-height: 16px;
                max-height: 16px;
                border-radius: 8px;
                margin: 2px;
            }
            QLabel[recording="false"] {
                background-color: transparent;
            }
        """)
        self.recording_indicator.setProperty("recording", False)

        # Create status message label
        self.status_label = QLabel("Ready")

        # Add widgets to horizontal layout
        status_layout.addWidget(self.recording_indicator)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()  # This pushes everything to the left

        # Add the container to the status bar
        self.statusbar.addWidget(status_container)

        # Override showMessage to update our custom label
        def custom_show_message(message, timeout=0):
            self.status_label.setText(message)
        self.statusbar.showMessage = custom_show_message

        # Playback format info (video/audio codec, resolution) is
        # shows this permanently in the status bar next to the channel name
        self.format_label = QLabel("")
        self.format_label.setObjectName("serverLabel")
        self.statusbar.addPermanentWidget(self.format_label)

        # Signal strength read from Tvheadend's input status API (only
        # meaningful for DVB/ATSC tuner inputs, blank for IPTV sources)
        self.signal_label = QLabel("")
        self.signal_label.setObjectName("serverLabel")
        self.statusbar.addPermanentWidget(self.signal_label)

        # Permanent clock widget on the right of the status bar
        self.clock_label = QLabel()
        self.clock_label.setObjectName("serverLabel")
        self.statusbar.addPermanentWidget(self.clock_label)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_status_clock_and_playback_info)
        self.clock_timer.start(1000)
        self.update_status_clock_and_playback_info()

        # Poll Tvheadend for tuner signal strength every few seconds
        self.signal_timer = QTimer(self)
        self.signal_timer.timeout.connect(self.update_signal_strength)
        self.signal_timer.start(4000)

        # Initialize
        self.fetch_channels()
        self.rebuild_server_menu()

        # Connect channel list double click to play
        
        # Add event filter to video frame for double-click
        self.video_frame.installEventFilter(self)
        
        # Add key event filter to main window
        self.installEventFilter(self)
        
        # Add Server Status to View menu
        server_status_action = view_menu.addAction("Server Status")
        server_status_action.triggered.connect(self.show_server_status)
        
        # Add DVR Status to View menu
        dvr_status_action = view_menu.addAction("DVR Status")
        dvr_status_action.triggered.connect(self.show_dvr_status)
        
        # Add search box before styling it
        search_layout = QHBoxLayout()
        search_icon = QLabel("🔍")  # Unicode search icon
        self.search_box = QLineEdit()
        
        # Style placeholder text
        placeholder_color = QColor(100, 100, 100)  # Dark gray color
        search_palette = self.search_box.palette()
        search_palette.setColor(QPalette.PlaceholderText, placeholder_color)
        self.search_box.setPalette(search_palette)
        
        self.search_box.setPlaceholderText("Press S to search channels...")
        self.search_box.textChanged.connect(self.filter_channels)
        self.search_box.setClearButtonEnabled(True)  # Add clear button inside search box
        
        # Add Ctrl+F shortcut for search box
        search_shortcut = QShortcut(QKeySequence(Qt.Key_S, Qt.NoModifier), self)
        search_shortcut.activated.connect(self.search_box.setFocus)
        
        # Create custom clear button action
        clear_action = QAction("⌫", self.search_box)
        self.search_box.addAction(clear_action, QLineEdit.TrailingPosition)
        
        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_box)
        channel_dialog_layout.insertLayout(1, search_layout)  # Insert above the channel list in the Channels dialog
        
        # Now style the search box with custom clear button styling
        
        
        # Add margins to search layout
        search_layout.setContentsMargins(0, 5, 0, 5)
        search_layout.setSpacing(5)
        
    def fetch_channels(self):
        """Fetch channel list from current TVHeadend server"""
        try:
            if not self.servers:
                print("Debug: No servers configured")
                self.statusbar.showMessage("No servers configured")
                return
                
            server = self.servers[self.server_combo.currentIndex()]
            print(f"Debug: Fetching channels from server: {server['url']}")
            
            # Initialize verification list
            channel_verification = []
            
            # Update status bar
            self.statusbar.showMessage("Connecting to server...")
            
            # Clean and format the URL properly
            url = server['url']
            if url.startswith('https://') or url.startswith('http://'):
                base_url = url
            else:
                base_url = f"http://{url}"
            
            api_url = f'{base_url}/api/channel/grid?limit=10000'
            print(f"Debug: Making request to: {api_url}")
            
            # Create auth tuple if credentials exist
            auth = None
            if server.get('username') or server.get('password'):
                auth = (server.get('username', ''), server.get('password', ''))
                print(f"Debug: Using authentication with username: {server.get('username', '')}")
            
            # Add timeout parameter (10 seconds)
            response = requests.get(api_url, auth=auth, timeout=10)
            
            channels = response.json()['entries']
            print(f"Debug: Found {len(channels)} channels")
            
            # First, disable sorting while adding items
            #self.channel_list.setSortingEnabled(False)
            
            # Clear existing items
            self.channel_list.setRowCount(0)
            
            # Create a list to store channel data for sorting
            channel_data = []
            
            # Process all channels first
            for channel in channels:
                try:
                    channel_name = channel.get('name', 'Unknown Channel')
                    channel_number = channel.get('number', 0)  # Use 0 as default for unnumbered channels
                    
                    # Store channel data for sorting
                    channel_data.append({
                        'number': channel_number,
                        'name': channel_name,
                        'data': channel
                    })
                    
                except Exception as e:
                    print(f"Debug: Error processing channel {channel.get('name', 'Unknown')}: {str(e)}")
                    continue
            
            # Sort channels by number, then name
            channel_data.sort(key=lambda x: (x['number'] or float('inf'), x['name'].lower()))

            # Keep a copy for other views (e.g. the all-channel EPG guide)
            self.channels = [c['data'] for c in channel_data]
            self.rebuild_channels_menu()
            
            # Now add sorted channels to the table
            for idx, channel in enumerate(channel_data):
                try:
                    print(f"Debug: Adding channel {idx + 1}/{len(channel_data)}: {channel['name']}")
                    
                    row = self.channel_list.rowCount()
                    self.channel_list.insertRow(row)
                    
                    # Create and add number item
                    number_item = QTableWidgetItem()
                    number_item.setData(Qt.DisplayRole, channel['number'])
                    self.channel_list.setItem(row, 0, number_item)
                    
                    # Create and add name item
                    name_item = QTableWidgetItem(channel['name'])
                    name_item.setData(Qt.UserRole, channel['data'])
                    self.channel_list.setItem(row, 1, name_item)
                    
                    # Add to verification list
                    channel_verification.append({
                        'row': row,
                        'name': channel['name'],
                        'number': channel['number']
                    })
                    
                    print(f"Debug: Added channel to row {row}: {channel['name']}")
                    
                except Exception as e:
                    print(f"Debug: Error adding channel to table: {str(e)}")
                    continue
            
            # Re-enable sorting but don't trigger an automatic sort
            self.channel_list.setSortingEnabled(True)
            
            # Verify the final table contents
            print("\nDebug: Channel Verification:")
            print(f"Original channel count: {len(channels)}")
            print(f"Added channel count: {len(channel_verification)}")
            print(f"Table row count: {self.channel_list.rowCount()}")
            
            print("\nDebug: Final Table Contents:")
            for row in range(self.channel_list.rowCount()):
                number_item = self.channel_list.item(row, 0)
                name_item = self.channel_list.item(row, 1)
                if number_item and name_item:
                    number = number_item.data(Qt.DisplayRole)
                    name = name_item.text()
                    print(f"Row {row}: #{number} - {name}")
                else:
                    print(f"Row {row}: Missing items")
            
            self.statusbar.showMessage("Channels loaded successfully")
            
        except Exception as e:
            print(f"Debug: Error in fetch_channels: {str(e)}")
            print(f"Debug: Error type: {type(e)}")
            import traceback
            print(f"Debug: Traceback: {traceback.format_exc()}")
            
            # Show error dialog
            dialog = ConnectionErrorDialog(
                server['name'], 
                f"Unexpected error: {str(e)}", 
                self
            )
            if dialog.exec_() == QDialog.Accepted:
                print("Debug: Retrying connection...")
                self.fetch_channels()
            else:
                print("Debug: Connection attempt aborted by user")
                self.statusbar.showMessage("Connection aborted")
                self.channel_list.clear()
        

    def get_recording_channel_name(self):
        """Best-guess channel name to record: whatever's selected in the
        channel table, falling back to whatever is currently playing."""
        current_item = self.channel_list.currentItem()
        if current_item:
            return current_item.text()
        if self.current_channel_data:
            return self.current_channel_data.get('name')
        return None

    def start_recording(self):
        print("Debug: Starting recording")
        try:
            # Get selected channel (falls back to whatever is currently playing)
            channel_name = self.get_recording_channel_name()
            if not channel_name:
                print("Debug: No channel selected for recording")
                self.statusbar.showMessage("Please select a channel to record")
                return

            # Show duration dialog
            duration_dialog = RecordingDurationDialog(self)
            if duration_dialog.exec_() != QDialog.Accepted:
                print("Debug: Recording cancelled by user")
                return
            
            duration = duration_dialog.get_duration()
            print(f"Debug: Selected recording duration: {duration} seconds")

            print(f"Debug: Attempting to record channel: {channel_name}")
            
            # Get current server
            server = self.servers[self.server_combo.currentIndex()]
            print(f"Debug: Using server: {server['url']}")
            
            # Create auth if needed
            auth = None
            if server.get('username') or server.get('password'):
                auth = (server.get('username', ''), server.get('password', ''))
                print(f"Debug: Using authentication with username: {server.get('username', '')}")
            
            # First, get channel UUID
            api_url = f'{server["url"]}/api/channel/grid?limit=10000'
            print(f"Debug: Getting channel UUID from: {api_url}")
            
            response = requests.get(api_url, auth=auth)
            print(f"Debug: Channel list response status: {response.status_code}")
            
            channels = response.json()['entries']
            channel_uuid = None
            for channel in channels:
                if channel['name'] == channel_name:
                    channel_uuid = channel['uuid']
                    print(f"Debug: Found channel UUID: {channel_uuid}")
                    break
                
            if not channel_uuid:
                print(f"Debug: Channel UUID not found for: {channel_name}")
                self.statusbar.showMessage("Channel not found")
                return
            
            # Prepare recording request
            now = int(datetime.now().timestamp())
            stop_time = now + duration
            
            # Format exactly as in the working curl command
            conf_data = {
                "start": now,
                "stop": stop_time,
                "channel": channel_uuid,
                "title": {"eng": "Instant Recording"},
                "subtitle": {"eng": "Recorded via TVHplayer"}
            }
            
            # Convert to string format as expected by the API
            data = {'conf': json.dumps(conf_data)}
            print(f"Debug: Recording data: {data}")
            
            # Make recording request
            record_url = f'{server["url"]}/api/dvr/entry/create'
            print(f"Debug: Sending recording request to: {record_url}")
            
            response = requests.post(record_url, data=data, auth=auth)
            print(f"Debug: Recording response status: {response.status_code}")
            print(f"Debug: Recording response: {response.text}")
            
            if response.status_code == 200:
                duration_minutes = duration // 60
                self.statusbar.showMessage(
                    f"Recording started for: {channel_name} ({duration_minutes} minutes)"
                )
                print("Debug: Recording started successfully")
                self.start_recording_indicator()  # Start the recording indicator
            else:
                self.statusbar.showMessage("Failed to start recording")
                print(f"Debug: Recording failed with status {response.status_code}")
                
        except Exception as e:
            print(f"Debug: Recording error: {str(e)}")
            print(f"Debug: Error type: {type(e)}")
            import traceback
            print(f"Debug: Traceback: {traceback.format_exc()}")
            self.statusbar.showMessage(f"Recording error: {str(e)}")
            
    def stop_playback(self):
        print("Debug: Stopping playback")
        """Stop current playback"""
        self.media_player.stop()
        self.statusbar.showMessage("Playback stopped")

                # Create a new fullscreen window
    def toggle_fullscreen(self):
        """Toggle fullscreen mode for the whole window.

        This intentionally does NOT reparent video_frame into a separate
        frameless top-level window (the previous approach). Frameless
        windows are not reliably given keyboard focus by many Linux
        window managers (GNOME/Mutter included), which is why F/Escape
        stopped working once entering fullscreen. Using Qt's own
        showFullScreen()/showNormal() on the main window keeps the video
        widget's native window handle stable throughout (no set_xwindow
        churn) and lets the window manager treat it as a normal
        fullscreen window, so keyboard input keeps working normally.
        """
        now_ts = time.time()
        if getattr(self, '_last_fullscreen_toggle', 0) and now_ts - self._last_fullscreen_toggle < 0.35:
            print("Debug: Ignoring duplicate fullscreen toggle")
            return
        self._last_fullscreen_toggle = now_ts

        print(f"Debug: Toggling fullscreen. Current state: {self.is_fullscreen}")

        try:
            if not self.is_fullscreen:
                # Hide the chrome and go fullscreen, remembering what was
                # visible so we can restore it exactly afterwards
                self._chrome_toolbars = self.findChildren(QToolBar)
                self._menubar_was_visible = self.menuBar().isVisible()
                self._statusbar_was_visible = self.statusbar.isVisible()
                self._toolbar_visibility = {tb: tb.isVisible() for tb in self._chrome_toolbars}

                self.menuBar().setVisible(False)
                self.statusbar.setVisible(False)
                for tb in self._chrome_toolbars:
                    tb.setVisible(False)

                self.showFullScreen()
                self.setFocus(Qt.OtherFocusReason)
            else:
                self.showNormal()

                if getattr(self, '_menubar_was_visible', True):
                    self.menuBar().setVisible(True)
                if getattr(self, '_statusbar_was_visible', True):
                    self.statusbar.setVisible(True)
                for tb, was_visible in getattr(self, '_toolbar_visibility', {}).items():
                    try:
                        tb.setVisible(was_visible)
                    except RuntimeError:
                        pass  # toolbar was deleted in the meantime

            self.is_fullscreen = not self.is_fullscreen
            print(f"Debug: New fullscreen state: {self.is_fullscreen}")

        except Exception as e:
            print(f"Debug: Error in toggle_fullscreen: {str(e)}")
            print(f"Debug: Traceback: {traceback.format_exc()}")

    def load_servers(self):
        """Load TVHeadend server configurations"""
        try:
            with open('servers.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Return empty list if no config file exists
            return []
        except json.JSONDecodeError:
            # Return default server if config file is invalid
            return [{
                'name': 'Default Server',
                'url': '127.0.0.1:9981'
            }]

    def manage_servers(self):
        print("Debug: Opening server management dialog")
        dialog = ServerDialog(self)
        dialog.load_servers(self.servers)
        print(f"Debug: Loaded {len(self.servers)} servers into dialog")
        if dialog.exec_() == QDialog.Accepted:
            self.servers = dialog.servers
            print(f"Debug: Updated servers list, now has {len(self.servers)} servers")
            self.save_config()
            
            # Update server combo
            self.server_combo.clear()
            for server in self.servers:
                print(f"Debug: Adding server to combo: {server['name']}")
                self.server_combo.addItem(server['name'])
            self.rebuild_server_menu()
            
            # Refresh channels
            self.fetch_channels()

    def save_config(self):
        """Save current configuration"""
        try:
            # Update window geometry in config
            if not self.is_fullscreen:
                self.config['window_geometry'] = {
                    'x': self.x(),
                    'y': self.y(),
                    'width': self.width(),
                    'height': self.height()
                }
            
            # Update servers in config
            self.config['servers'] = self.servers
            
            # Update last server
            self.config['last_server'] = self.server_combo.currentIndex()
            
            # Save to file
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            print("Debug: Configuration saved successfully")
        except Exception as e:
            print(f"Debug: Error saving config: {str(e)}")

    def play_channel(self, item):
        """Play the selected channel"""
        try:
            # Get the current row
            current_row = self.channel_list.currentRow()
            if current_row < 0:
                print("Debug: No channel selected")
                self.statusbar.showMessage("Please select a channel to play")
                return
            
            # Get channel data directly from the table
            name_item = self.channel_list.item(current_row, 1)  # Get the name column item
            if not name_item:
                print("Debug: No channel item found")
                return
            
            # Get the channel data stored in UserRole
            channel_data = name_item.data(Qt.UserRole)
            if not channel_data:
                print("Debug: No channel data found in item")
                return
            
            print(f"Debug: Playing channel: {channel_data.get('name', 'Unknown')}")
            
            # Get current server
            server = self.servers[self.server_combo.currentIndex()]
            
            # Construct proper URL
            base_url = server['url']
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"http://{base_url}"
            
            url = f"{base_url}/stream/channel/{channel_data['uuid']}"
            print(f"Debug: Playing URL: {url}")
            
            # Rest of the play logic...
        except Exception as e:
            print(f"Debug: Error in play_channel: {str(e)}")
            print(f"Debug: Traceback: {traceback.format_exc()}")

    def on_server_changed(self, index):
        """
        Handle when user switches to a different TVHeadend server in the dropdown.
        Updates the config file with the newly selected server index and refreshes channel list.
        
        Args:
            index (int): Index of the newly selected server in self.servers list
        """
        print(f"Debug: Server changed to index {index}")
        if index >= 0:  # Valid index selected
            print(f"Debug: Switching to server: {self.servers[index]['name']}")
            
            # Update config with new server selection
            self.config['last_server'] = index
            
            # Save updated config to file
            try:
                with open(self.config_file, 'w') as f:
                    json.dump(self.config, f)
                print(f"Debug: Saved server index {index} to config")
            except Exception as e:
                print(f"Debug: Error saving config: {e}")
                
            # Load channels from newly selected server
            self.fetch_channels()

    def on_volume_changed(self, value):
        print(f"Debug: Volume changed to {value}")
        self.media_player.audio_set_volume(value)

    def eventFilter(self, obj, event):
        """Handle double-click and key events"""
        if obj == self.video_frame:
            if event.type() == event.MouseButtonDblClick:
                self.toggle_fullscreen()
                return True
            
        # Handle key events for both main window and fullscreen window
        if event.type() == event.KeyPress:
            if event.isAutoRepeat():
                return True
            if event.key() == Qt.Key_Escape and self.is_fullscreen:
                self.toggle_fullscreen()
                return True
            elif event.key() == Qt.Key_F:
                self.toggle_fullscreen()
                return True
            elif event.key() == Qt.Key_Q and (event.modifiers() & Qt.ControlModifier):
                self.close()
                return True
            
        return super().eventFilter(obj, event)

    def toggle_mute(self):
        """Toggle audio mute state"""
        print("Debug: Toggling mute")
        is_muted = self.media_player.audio_get_mute()
        self.media_player.audio_set_mute(not is_muted)
        
        if not is_muted:  # Switching to muted
            self.mute_btn.setIcon(QIcon(f"{self.icons_dir}/mute.svg"))
            self.mute_btn.setToolTip("Unmute")
            print("Debug: Audio muted")
        else:  # Switching to unmuted
            self.mute_btn.setIcon(QIcon(f"{self.icons_dir}/unmute.svg"))
            self.mute_btn.setToolTip("Mute")
            print("Debug: Audio unmuted")

    def show_about(self):
        """Show the about dialog"""
        print("Debug: Showing about dialog")
        about_text = (
            "<div style='text-align: center;'>"
            "<h2>TVHviewer</h2>"
            "<p>Version 1.0</p>"
            "<p>A more modern desktop client for Tvheadend. Watch and record live TV.</p>"
            "<p style='margin-top: 20px;'><b>Fork maintained by:</b><br>"
            "honeyx \u2014 <a href='https://github.com/honeyx/tvhviewer'>github.com/honeyx/tvhviewer</a></p>"
            "<p style='margin-top: 20px;'><b>Originally created by:</b><br>"
            "mFat \u2014 <a href='https://github.com/mfat/tvhplayer'>github.com/mfat/tvhplayer</a><br>"
            "TVHviewer is a fork of the original TVHplayer project. "
            "All credit for the original application design and functionality "
            "belongs to mFat and the TVHplayer contributors.</p>"
            "<p style='margin-top: 20px;'><b>Built with:</b><br>"
            "Python, PyQt5, and VLC</p>"
            "<p style='margin-top: 20px; font-size: 11px;'>"
            "This program is free software: you can redistribute it and/or modify "
            "it under the terms of the GNU General Public License as published by "
            "the Free Software Foundation, either version 3 of the License, or "
            "(at your option) any later version.<br><br>"
            "This program is distributed in the hope that it will be useful, "
            "but WITHOUT ANY WARRANTY; without even the implied warranty of "
            "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the "
            "GNU General Public License for more details.<br><br>"
            "You should have received a copy of the GNU General Public License "
            "along with this program. If not, see "
            "<a href='https://www.gnu.org/licenses/'>https://www.gnu.org/licenses/</a>."
            "</p>"
            "</div>"
        )
        msg = QMessageBox()
        msg.setWindowTitle("About TVHviewer")
        msg.setText(about_text)
        msg.setTextFormat(Qt.RichText)
        msg.setMinimumWidth(400)  # Make dialog wider to prevent text wrapping
        msg.exec_()

    def show_user_guide(self):
        """Open the user guide documentation"""
        print("Debug: Opening user guide")
        try:
            # Open the GitHub wiki URL in the default web browser
            url = "https://github.com/mfat/tvhplayer/wiki/User-Guide"
            
            # Open URL in the default web browser based on platform
            if platform.system() == "Linux":
                subprocess.Popen(["xdg-open", url])
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", url])
            elif platform.system() == "Windows":
                os.startfile(url)
            else:
                # Fallback using webbrowser module
                import webbrowser
                webbrowser.open(url)
                
            print(f"Opened user guide URL: {url}")
            
        except Exception as e:
            print(f"Error opening user guide URL: {str(e)}")
            QMessageBox.critical(
                self, 
                "Error",
                f"Failed to open user guide: {str(e)}",
                QMessageBox.Ok
            )

    def toggle_recording(self):
        """Toggle between starting and stopping recording"""
        if self.record_btn.isChecked():
            self.start_recording()
        else:
            self.stop_recording()

    def stop_recording(self):
        """Stop active recordings"""
        print("Debug: Attempting to stop recordings")
        try:
            # Get current server
            server = self.servers[self.server_combo.currentIndex()]
            print(f"Debug: Using server: {server['url']}")
            
            # Create auth if needed
            auth = None
            if server.get('username') or server.get('password'):
                auth = (server.get('username', ''), server.get('password', ''))
                print(f"Debug: Using authentication with username: {server.get('username', '')}")
            
            # Get list of active recordings
            api_url = f'{server["url"]}/api/dvr/entry/grid'
            print(f"Debug: Getting recordings from: {api_url}")
            
            response = requests.get(api_url, auth=auth)
            print(f"Debug: Recording list response status: {response.status_code}")
            
            recordings = response.json()['entries']
            print(f"Debug: Total recordings found: {len(recordings)}")
            
            # Print all recordings and their statuses for debugging
            for recording in recordings:
                print(f"Debug: Recording '{recording.get('disp_title', 'Unknown')}' - Status: {recording.get('status', 'unknown')}")
            
            # Look for recordings with status 'Running' (this seems to be the actual status used by TVHeadend)
            active_recordings = [r for r in recordings if r['status'] in ['Running', 'recording']]
            if not active_recordings:
                print("Debug: No active recordings found")
                self.statusbar.showMessage("No active recordings to stop")
                self.stop_recording_indicator()  # Make sure to hide indicator
                return
                
            print(f"Debug: Found {len(active_recordings)} active recordings")
            
            # Stop each active recording
            for recording in active_recordings:
                stop_url = f'{server["url"]}/api/dvr/entry/stop'
                data = {'uuid': recording['uuid']}
                
                print(f"Debug: Stopping recording: {recording.get('disp_title', 'Unknown')} ({recording['uuid']})")
                stop_response = requests.post(stop_url, data=data, auth=auth)
                
                if stop_response.status_code == 200:
                    print(f"Debug: Successfully stopped recording: {recording['uuid']}")
                else:
                    print(f"Debug: Failed to stop recording: {recording['uuid']}")
                    print(f"Debug: Response: {stop_response.text}")
            
            self.stop_recording_indicator()  # Hide the indicator after stopping recordings
            self.statusbar.showMessage(f"Stopped {len(active_recordings)} recording(s)")
            
        except Exception as e:
            print(f"Debug: Error stopping recordings: {str(e)}")
            print(f"Debug: Error type: {type(e)}")
            import traceback
            print(f"Debug: Traceback: {traceback.format_exc()}")
            self.statusbar.showMessage(f"Error stopping recordings: {str(e)}")
            self.stop_recording_indicator()  # Make sure to hide indicator even on error

    def start_recording_indicator(self):
        """Start the recording indicator with smooth pulsing animation"""
        print("Debug: Starting recording indicator")
        self.is_recording = True
        self.recording_indicator.setProperty("recording", True)
        self.recording_indicator.style().polish(self.recording_indicator)
        
        # Create opacity effect
        self.opacity_effect = QGraphicsOpacityEffect(self.recording_indicator)
        self.recording_indicator.setGraphicsEffect(self.opacity_effect)
        
        # Create and configure the animation
        self.recording_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.recording_animation.setDuration(1000)  # 1 second per pulse
        self.recording_animation.setStartValue(1.0)
        self.recording_animation.setEndValue(0.3)
        self.recording_animation.setEasingCurve(QEasingCurve.InOutSine)
        self.recording_animation.setLoopCount(-1)  # Infinite loop
        
        # Start the animation
        self.recording_animation.start()

    def stop_recording_indicator(self):
        """Stop the recording indicator and its animation"""
        print("Debug: Stopping recording indicator")
        self.is_recording = False
        if self.recording_animation:
            self.recording_animation.stop()
            self.recording_animation = None
        if hasattr(self, 'opacity_effect'):
            self.recording_indicator.setGraphicsEffect(None)
            self.opacity_effect = None
        self.recording_indicator.setProperty("recording", False)
        self.recording_indicator.style().polish(self.recording_indicator)

    def show_dvr_status(self):
        """Show DVR status dialog"""
        try:
            print("\nDebug: Opening DVR Status Dialog")
            server = self.servers[self.server_combo.currentIndex()]
            print(f"Debug: Using server: {server}")

            # Test connection first
            test_url = f"{server['url']}/api/status/connections"
            auth = None
            if server.get('username') or server.get('password'):
                auth = (server.get('username', ''), server.get('password', ''))
                print(f"Debug: Using authentication with username: {server.get('username', '')}")

            print(f"Debug: Testing connection to: {test_url}")
            try:
                test_response = requests.get(test_url, auth=auth, timeout=5)
                print(f"Debug: Connection test response: {test_response.status_code}")
                if test_response.status_code == 200:
                    print("Debug: Server connection successful")
                else:
                    print(f"Debug: Server connection failed with status {test_response.status_code}")
                    self.statusbar.showMessage("Failed to connect to server")
                    return
            except Exception as conn_err:
                print(f"Debug: Connection test failed: {str(conn_err)}")
                self.statusbar.showMessage("Failed to connect to server")
                return

            # Now try to get DVR data
            dvr_url = f"{server['url']}/api/dvr/entry/grid"
            print(f"Debug: Fetching DVR data from: {dvr_url}")
            try:
                dvr_response = requests.get(dvr_url, auth=auth, timeout=5)
                print(f"Debug: DVR data response: {dvr_response.status_code}")
                if dvr_response.status_code == 200:
                    dvr_data = dvr_response.json()
                    print(f"Debug: DVR data received: {len(dvr_data.get('entries', []))} entries")
                    # Print first entry as sample if available
                    if dvr_data.get('entries'):
                        print("Debug: Sample DVR entry:")
                        print(dvr_data['entries'][0])
                else:
                    print(f"Debug: Failed to get DVR data: {dvr_response.text}")
                    self.statusbar.showMessage("Failed to get DVR data")
                    return
            except Exception as dvr_err:
                print(f"Debug: DVR data fetch failed: {str(dvr_err)}")
                self.statusbar.showMessage("Failed to get DVR data")
                return

            # If we got here, show the dialog
            dialog = DVRStatusDialog(server, self)
            dialog.show()
            
        except Exception as e:
            print(f"Debug: Error showing DVR status: {str(e)}")
            print(f"Debug: Traceback: {traceback.format_exc()}")
            self.statusbar.showMessage("Error showing DVR status")

    def play_url(self, url):
        """Play media from URL"""
        try:
            media = self.instance.media_new(url)
            self.media_player.set_media(media)
            self.media_player.play()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to play media: {str(e)}")

    def start_local_recording(self, channel_name=None):
        """Record channel stream to local disk using ffmpeg"""
        try:
            if not channel_name:
                channel_name = self.get_recording_channel_name()
            if not channel_name:
                print("Debug: No channel selected for recording")
                self.statusbar.showMessage("Please select a channel to record")
                return

            print(f"Debug: Starting local recording for channel: {channel_name}")
            
            # Show file save dialog, defaulting to wherever the last
            # recording was saved (falls back to the home directory)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"recording_{channel_name}_{timestamp}.ts"  # Using .ts format initially
            default_dir = self.config.get('recording_path', str(Path.home()))
            if not default_dir or not os.path.isdir(default_dir):
                default_dir = str(Path.home())
            default_path = os.path.join(default_dir, default_filename)

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Recording As",
                default_path,
                "TS Files (*.ts);;MP4 Files (*.mp4);;All Files (*.*)",
                options=QFileDialog.DontUseNativeDialog
            )
            
            if not file_path:  # User cancelled
                print("Debug: Recording cancelled - no file selected")
                return

            # Remember this location for next time
            self.config['recording_path'] = os.path.dirname(file_path)
            self.save_config()
                
            # Get current server and auth info
            server = self.servers[self.server_combo.currentIndex()]
            
            # Get channel UUID
            api_url = f'{server["url"]}/api/channel/grid?limit=10000'
            auth = None
            if server.get('username') or server.get('password'):
                auth = (server.get('username', ''), server.get('password', ''))
            
            print(f"Debug: Fetching channel list from: {api_url}")
            response = requests.get(api_url, auth=auth)
            channels = response.json()['entries']
            
            channel_uuid = None
            for channel in channels:
                if channel['name'] == channel_name:
                    channel_uuid = channel['uuid']
                    break
                    
            if not channel_uuid:
                print(f"Debug: Channel UUID not found for: {channel_name}")
                self.statusbar.showMessage("Channel not found")
                return
                
            # Create stream URL
            server_url = server['url'].rstrip('/')
            if not server_url.startswith(('http://', 'https://')):
                server_url = f'http://{server_url}'
            
            stream_url = f'{server_url}/stream/channel/{channel_uuid}'
            
            # Prefer a bundled ffmpeg (shipped next to the app in the
            # Windows build) over relying purely on PATH
            ffmpeg_exe = 'ffmpeg'
            if getattr(sys, 'frozen', False):
                bundled_name = 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'
                bundled_path = os.path.join(os.path.dirname(sys.executable), bundled_name)
                if os.path.isfile(bundled_path):
                    ffmpeg_exe = bundled_path

            # Build ffmpeg command
            ffmpeg_cmd = [
                ffmpeg_exe,
                '-hide_banner',
                '-loglevel', 'warning',
                '-nostats',
                '-y'  # Overwrite output
            ]
            
            # Add auth headers if needed
            if auth:
                import base64
                auth_string = f"{auth[0]}:{auth[1]}"
                auth_bytes = auth_string.encode('ascii')
                base64_bytes = base64.b64encode(auth_bytes)
                base64_auth = base64_bytes.decode('ascii')
                ffmpeg_cmd.extend([
                    '-headers', f'Authorization: Basic {base64_auth}\r\n'
                ])
            
            # Add input options
            ffmpeg_cmd.extend([
                '-i', stream_url,
                '-analyzeduration', '10M',  # Increase analyze duration
                '-probesize', '10M'         # Increase probe size
            ])

            # Add output options based on file extension
            if file_path.lower().endswith('.mp4'):
                ffmpeg_cmd.extend([
                    '-c:v', 'copy',
                    '-c:a', 'aac',          # Transcode audio to AAC
                    '-b:a', '192k',         # Audio bitrate
                    '-movflags', '+faststart',
                    '-f', 'mp4'
                ])
            else:  # Default to .ts
                ffmpeg_cmd.extend([
                    '-c', 'copy',           # Copy both streams without transcoding
                    '-f', 'mpegts'          # Force MPEG-TS format
                ])
            
            # Add output file
            ffmpeg_cmd.append(file_path)
            
            print("Debug: Starting ffmpeg with command:")
            # Print command with hidden auth if present
            safe_cmd = ' '.join(ffmpeg_cmd)
            if auth:
                safe_cmd = safe_cmd.replace(base64_auth, "***")
            print(f"Debug: {safe_cmd}")
            
            # Start ffmpeg process
            popen_kwargs = dict(
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8
            )
            if sys.platform == 'win32':
                # ffmpeg.exe is a console app - without this Windows pops
                # up a distracting (and, since we pipe its output, empty)
                # console window every time a recording starts.
                popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            self.ffmpeg_process = subprocess.Popen(ffmpeg_cmd, **popen_kwargs)
            
            # Start monitoring process
            self.recording_monitor = QTimer()
            self.recording_monitor.timeout.connect(
                lambda: self.check_recording_status(file_path))  # Close parenthesis here
            self.recording_monitor.start(2000)  # Check every 2 seconds
            
            self.statusbar.showMessage(f"Local recording started: {file_path}")
            self.start_recording_indicator()
            
            # After starting ffmpeg process successfully:
            self.recording_status_dialog = RecordingStatusDialog(channel_name, file_path, self)
            self.recording_status_dialog.finished.connect(self.stop_local_recording)
            self.recording_status_dialog.show()
            
        except FileNotFoundError:
            msg = ("Local recording needs ffmpeg, which isn't installed (or not on PATH). "
                   "Install it from https://ffmpeg.org/download.html and try again.")
            print(f"Debug: Local recording error: ffmpeg not found")
            self.statusbar.showMessage(msg)
            QMessageBox.warning(self, "ffmpeg not found", msg)
        except Exception as e:
            print(f"Debug: Local recording error: {str(e)}")
            print(f"Debug: Error type: {type(e)}")
            import traceback
            print(f"Debug: Traceback: {traceback.format_exc()}")
            self.statusbar.showMessage(f"Local recording error: {str(e)}")

    def check_recording_status(self, file_path):
        """Check if the recording is actually working"""
        try:
            import os
            # Add start time tracking if not exists
            if not hasattr(self, 'recording_start_time'):
                self.recording_start_time = time.time()

            # Calculate elapsed time
            elapsed_time = time.time() - self.recording_start_time
            
            if not os.path.exists(file_path):
                print("Debug: Recording file does not exist")
                # Only show warning if more than 10 seconds have passed
                if elapsed_time > 10:
                    # Grab ffmpeg's diagnostic output *before* closing the
                    # status dialog - closing it triggers stop_local_recording()
                    # via a signal connection, which clears self.ffmpeg_process
                    stderr_text = ''
                    proc = getattr(self, 'ffmpeg_process', None)
                    if proc is not None and proc.poll() is not None:
                        _, stderr = proc.communicate()
                        stderr_text = stderr.decode(errors='replace').strip() if stderr else ''
                        if len(stderr_text) > 2000:
                            stderr_text = '...\n' + stderr_text[-2000:]
                    if hasattr(self, 'recording_status_dialog'):
                        self.recording_status_dialog.close()
                    msg = "Recording file was never created - ffmpeg likely failed to start the stream."
                    if stderr_text:
                        msg += f"\n\n{stderr_text}"
                    QMessageBox.warning(self, "Local Recording Status", msg)
                    return
                else:
                    print(f"Debug: Waiting for file creation ({int(elapsed_time)} seconds elapsed)")
                    return
            
            file_size = os.path.getsize(file_path)
            print(f"Debug: Current recording file size: {file_size} bytes")
            
            # Update status dialog if it exists
            if hasattr(self, 'recording_status_dialog'):
                is_stalled = False
                if hasattr(self, 'last_file_size') and file_size == self.last_file_size:
                    is_stalled = True
                self.recording_status_dialog.update_status(file_size, is_stalled)
            
            if hasattr(self, 'ffmpeg_process'):
                return_code = self.ffmpeg_process.poll()
                if return_code is not None:
                    # Process has ended
                    _, stderr = self.ffmpeg_process.communicate()
                    print(f"Debug: FFmpeg process ended with return code: {return_code}")
                    if stderr:
                        print(f"Debug: FFmpeg error output: {stderr.decode()}")
                    
                    if file_size == 0 or return_code != 0:
                        print("Debug: Recording failed - stopping processes")
                        self.stop_local_recording()
                        stderr_text = stderr.decode(errors='replace').strip() if stderr else ''
                        if len(stderr_text) > 2000:  # keep the dialog readable
                            stderr_text = '...\n' + stderr_text[-2000:]
                        error_msg = f"Recording failed (ffmpeg exit code {return_code})."
                        if stderr_text:
                            error_msg += f"\n\n{stderr_text}"
                        QMessageBox.critical(self, "Recording Error", error_msg)
                        return
                    
                # Check if file is growing
                if hasattr(self, 'last_file_size'):
                    if file_size == self.last_file_size:
                        print("Debug: File size not increasing - potential stall")
                        self.stall_count = getattr(self, 'stall_count', 0) + 1
                        if self.stall_count > 5:  # After 10 seconds of no growth
                            print("Debug: Recording stalled - restarting")
                            stall_msg = "Recording stalled - attempting restart"
                            QMessageBox.warning(self, "Recording Status", stall_msg)
                            self.stop_local_recording()
                            self.start_local_recording()
                            return
                    else:
                        self.stall_count = 0
                
                self.last_file_size = file_size
            
        except Exception as e:
            error_msg = f"Debug: Error checking recording status: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Recording Error", error_msg)

    def stop_local_recording(self):
        """Stop local recording"""
        try:
            # Close status dialog if it exists
            if hasattr(self, 'recording_status_dialog'):
                self.recording_status_dialog.close()
                delattr(self, 'recording_status_dialog')
            
            print("Debug: Stopping local recording")
            
            # Stop monitoring
            if hasattr(self, 'recording_monitor') and self.recording_monitor is not None:
                self.recording_monitor.stop()
                self.recording_monitor = None
            
            # Stop ffmpeg process
            if hasattr(self, 'ffmpeg_process') and self.ffmpeg_process is not None:
                print("Debug: Stopping ffmpeg process")
                self.ffmpeg_process.terminate()
                try:
                    self.ffmpeg_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.ffmpeg_process.kill()
                self.ffmpeg_process = None
            
            # Clear stall detection variables
            if hasattr(self, 'last_file_size'):
                del self.last_file_size
            if hasattr(self, 'stall_count'):
                del self.stall_count
            if hasattr(self, 'recording_start_time'):
                del self.recording_start_time
            
            self.statusbar.showMessage("Local recording stopped")
            self.stop_recording_indicator()
            
        except Exception as e:
            print(f"Debug: Error stopping local recording: {str(e)}")
            self.statusbar.showMessage(f"Error stopping local recording: {str(e)}")
            self.stop_recording_indicator()

    def load_config(self):
        """Load application configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                # Return default configuration
                return {
                    'volume': 100,
                    'last_server': 0,
                    'recording_path': str(Path.home()),
                    'theme': 'dark',
                    'window_geometry': {
                        'x': 100,
                        'y': 100,
                        'width': 1200,
                        'height': 700
                    },
                }
        except Exception as e:
            print(f"Debug: Error loading config: {str(e)}")
            return self.get_default_config()

    def get_default_config(self):
        """Return default configuration"""
        return {
            'volume': 100,
            'last_server': 0,
            'recording_path': str(Path.home()),
            'theme': 'dark',
            'window_geometry': {
                'x': 100,
                'y': 100,
                'width': 1200,
                'height': 700
            },
        }

    def closeEvent(self, event):
        """Save configuration when closing the application"""
        self.save_config()
        super().closeEvent(event)

    def show_channel_context_menu(self, position):
        """Show context menu for channel list items"""
        menu = QMenu()
        
        # Get the item at the position
        row = self.channel_list.rowAt(position.y())
        if row >= 0:
            channel_item = self.channel_list.item(row, 1)  # Get name column item
            channel_data = channel_item.data(Qt.UserRole)
            
            # Add menu actions
            play_action = menu.addAction("Play")
            play_action.triggered.connect(lambda: self.play_channel_by_data(channel_data))
            record_action = menu.addAction("Record")
            record_action.triggered.connect(lambda: self.start_recording())
            local_record_action = menu.addAction("Record Locally")
            local_record_action.triggered.connect(
                lambda: self.start_local_recording(channel_data['name']))
            
            # Add EPG action
            epg_action = menu.addAction("Show EPG (this channel)")
            epg_action.triggered.connect(lambda: self.show_channel_epg(channel_data['name']))

            full_guide_action = menu.addAction("Program Guide (all channels)...")
            full_guide_action.triggered.connect(self.show_epg_grid)

            menu.addSeparator()
            if channel_data.get('name') in self.config.get('favorites', []):
                fav_action = menu.addAction("Remove from Favorites")
                fav_action.triggered.connect(lambda: self.remove_favorite(channel_data.get('name')))
            else:
                fav_action = menu.addAction("Add to Favorites")
                fav_action.triggered.connect(lambda: self.add_favorite(channel_data.get('name')))
            
            # Show the menu at the cursor position
            menu.exec_(self.channel_list.viewport().mapToGlobal(position))

    def show_channel_epg(self, channel_name):
        """Fetch and show EPG data for the selected channel"""
        try:
            print(f"Debug: Fetching EPG for channel: {channel_name}")
            
            # Get current server
            server = self.servers[self.server_combo.currentIndex()]
            print(f"Debug: Using server: {server['url']}")
            
            # Create auth if needed
            auth = None
            if server.get('username') or server.get('password'):
                auth = (server.get('username', ''), server.get('password', ''))
                print(f"Debug: Using authentication with username: {server.get('username', '')}")
            
            # First get channel UUID
            api_url = f'{server["url"]}/api/channel/grid?limit=10000'
            print(f"Debug: Getting channel UUID from: {api_url}")
            
            response = requests.get(api_url, auth=auth)
            print(f"Debug: Channel list response status: {response.status_code}")
            
            channels = response.json()['entries']
            print(f"Debug: Found {len(channels)} channels in response")
            
            channel_uuid = None
            for channel in channels:
                if channel['name'] == channel_name:
                    channel_uuid = channel['uuid']
                    print(f"Debug: Found channel UUID: {channel_uuid}")
                    break
            
            if not channel_uuid:
                print(f"Debug: Channel UUID not found for: {channel_name}")
                self.statusbar.showMessage("Channel not found")
                return
            
            # Get EPG data for the channel
            epg_url = f'{server["url"]}/api/epg/events/grid'
            params = {
                'channel': channel_uuid,
                'limit': 24  # Get next 24 events
            }
            print(f"Debug: Fetching EPG data from: {epg_url}")
            print(f"Debug: With parameters: {params}")
            
            response = requests.get(epg_url, params=params, auth=auth)
            print(f"Debug: EPG response status: {response.status_code}")
            
            if response.status_code == 200:
                epg_data = response.json()['entries']
                if epg_data:
                    dialog = EPGDialog(channel_name, epg_data, server, self)
                    dialog.show()
                else:
                    self.statusbar.showMessage("No EPG data available")
            else:
                self.statusbar.showMessage("Failed to fetch EPG data")
                
        except Exception as e:
            print(f"Debug: Error fetching EPG: {str(e)}")
            self.statusbar.showMessage(f"Error fetching EPG: {str(e)}")

    def show_channel_dialog(self):
        """Show the 'All Channels' window (channel list + server picker)"""
        self.channel_dialog.show()
        self.channel_dialog.raise_()
        self.channel_dialog.activateWindow()

    def rebuild_server_menu(self):
        """Rebuild the Settings -> Active Server checkable list"""
        self.server_menu.clear()
        for action in self.server_action_group.actions():
            self.server_action_group.removeAction(action)
        for i, server in enumerate(self.servers):
            action = QAction(server['name'], self)
            action.setCheckable(True)
            action.setChecked(i == self.server_combo.currentIndex())
            action.triggered.connect(lambda checked, idx=i: self.server_combo.setCurrentIndex(idx))
            self.server_action_group.addAction(action)
            self.server_menu.addAction(action)

    def rebuild_channels_menu(self):
        """Channels menu: a proper scrollable dropdown list of channels
        (like the original combo-box style), not a giant flat menu that
        can end up taller than the screen."""
        self.channels_menu.clear()
        if not self.channels:
            empty_action = QAction("(No channels loaded)", self)
            empty_action.setEnabled(False)
            self.channels_menu.addAction(empty_action)
        else:
            list_widget = QListWidget()
            list_widget.setMaximumHeight(420)
            list_widget.setMinimumWidth(260)
            list_widget.setAlternatingRowColors(True)
            for channel_data in self.channels:
                number = channel_data.get('number')
                label = f"{number}  {channel_data.get('name', '')}" if number else channel_data.get('name', '')
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, channel_data)
                list_widget.addItem(item)
            list_widget.itemClicked.connect(self._play_from_channels_menu_list)
            self._channels_menu_list = list_widget  # keep a reference alive
            widget_action = QWidgetAction(self.channels_menu)
            widget_action.setDefaultWidget(list_widget)
            self.channels_menu.addAction(widget_action)
        self.channels_menu.addSeparator()
        all_channels_action = QAction("Open Channel Browser (search)...", self)
        all_channels_action.triggered.connect(self.show_channel_dialog)
        self.channels_menu.addAction(all_channels_action)
        self.rebuild_favorites_menu()

    def _play_from_channels_menu_list(self, item):
        channel_data = item.data(Qt.UserRole)
        if channel_data:
            self.play_channel_by_data(channel_data)
        self.channels_menu.close()

    def rebuild_favorites_menu(self):
        """Favorites menu: favorite channels, click to play, plus management"""
        self.favorites_menu.clear()
        favorites = self.config.get('favorites', [])
        by_name = {c.get('name'): c for c in self.channels}
        added = False
        for fav_name in favorites:
            channel_data = by_name.get(fav_name)
            if not channel_data:
                continue
            action = QAction(fav_name, self)
            action.triggered.connect(lambda checked, cd=channel_data: self.play_channel_by_data(cd))
            self.favorites_menu.addAction(action)
            added = True
        if not added:
            empty_action = QAction("(No favorites yet)", self)
            empty_action.setEnabled(False)
            self.favorites_menu.addAction(empty_action)
        self.favorites_menu.addSeparator()
        add_current_action = QAction("Add Current Channel to Favorites", self)
        add_current_action.triggered.connect(
            lambda: self.add_favorite(self.current_channel_data.get('name'))
            if self.current_channel_data else None)
        add_current_action.setEnabled(self.current_channel_data is not None)
        self.favorites_menu.addAction(add_current_action)
        manage_favorites_action = QAction("Manage Favorites...", self)
        manage_favorites_action.triggered.connect(self.manage_favorites)
        self.favorites_menu.addAction(manage_favorites_action)

    def add_favorite(self, channel_name):
        if not channel_name:
            return
        favorites = self.config.get('favorites', [])
        if channel_name not in favorites:
            favorites.append(channel_name)
            self.config['favorites'] = favorites
            self.save_config()
            self.rebuild_favorites_menu()

    def remove_favorite(self, channel_name):
        favorites = self.config.get('favorites', [])
        if channel_name in favorites:
            favorites.remove(channel_name)
            self.config['favorites'] = favorites
            self.save_config()
            self.rebuild_favorites_menu()

    def manage_favorites(self):
        """Small dialog to check/uncheck favorite channels"""
        if not self.channels:
            QMessageBox.information(self, "No channels loaded",
                                     "Open 'All Channels...' first so the channel list can load from the server.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Favorites")
        dialog.resize(340, 480)
        layout = QVBoxLayout(dialog)
        list_widget = QListWidget()
        favorites = set(self.config.get('favorites', []))
        for channel in self.channels:
            item = QListWidgetItem(channel.get('name', ''))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if channel.get('name') in favorites else Qt.Unchecked)
            list_widget.addItem(item)
        layout.addWidget(list_widget)
        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        if dialog.exec_() == QDialog.Accepted:
            new_favorites = []
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item.checkState() == Qt.Checked:
                    new_favorites.append(item.text())
            self.config['favorites'] = new_favorites
            self.save_config()
            self.rebuild_favorites_menu()

    def update_status_clock_and_playback_info(self):
        """Update the status bar clock and current video/audio format info"""
        self.clock_label.setText(datetime.now().strftime('%a %d.%m.%Y  %H:%M:%S'))
        try:
            if self.media_player is not None and self.media_player.is_playing():
                size = self.media_player.video_get_size(0)
                fps = self.media_player.get_fps()
                parts = []
                if size and size[0] and size[1]:
                    parts.append(f"{size[0]}x{size[1]}")
                if fps:
                    parts.append(f"{fps:.2f} fps")
                media = self.media_player.get_media()
                if media is not None:
                    tracks = media.tracks_get() if hasattr(media, 'tracks_get') else None
                    if tracks:
                        def fourcc_to_str(codec):
                            try:
                                return codec.to_bytes(4, 'little').decode('ascii', errors='ignore').strip().upper()
                            except Exception:
                                return ''
                        for track in tracks:
                            ttype = getattr(track, 'type', None)
                            if ttype == vlc.TrackType.video:
                                codec_str = fourcc_to_str(track.codec)
                                if codec_str:
                                    parts.append(f"Video: {codec_str}")
                            elif ttype == vlc.TrackType.audio:
                                codec_str = fourcc_to_str(track.codec)
                                if codec_str:
                                    parts.append(f"Audio: {codec_str}")
                self.format_label.setText("  \u2022  ".join(parts))
            else:
                self.format_label.setText("")
        except Exception:
            # Format probing is best-effort - never let it break the clock
            self.format_label.setText("")

    def update_signal_strength(self):
        """Poll Tvheadend's input status for tuner signal strength"""
        try:
            if not self.servers or not hasattr(self, 'server_combo'):
                return
            if self.media_player is None or not self.media_player.is_playing():
                self.signal_label.setText("")
                return
            server = self.servers[self.server_combo.currentIndex()]
            auth = None
            if server.get('username') or server.get('password'):
                auth = (server.get('username', ''), server.get('password', ''))
            base_url = server['url']
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"http://{base_url}"
            response = requests.get(f'{base_url}/api/status/inputs', auth=auth, timeout=3)
            if response.status_code != 200:
                self.signal_label.setText("")
                return
            entries = response.json().get('entries', [])
            active = [e for e in entries if e.get('signal') or e.get('snr')]
            if not active:
                self.signal_label.setText("")
                return
            entry = active[0]
            signal = entry.get('signal')
            snr = entry.get('snr')
            parts = []
            if signal is not None:
                # Tvheadend reports signal in 1/65535 units on some inputs, percent on others
                pct = signal / 655.35 if signal > 100 else signal
                parts.append(f"Signal {pct:.0f}%")
            if snr is not None:
                parts.append(f"SNR {snr}")
            self.signal_label.setText("  \u2022  ".join(parts))
        except Exception:
            self.signal_label.setText("")

    def show_epg_grid(self):
        """Open the program guide: all channels + a scrollable timeline"""
        if not self.servers:
            self.statusbar.showMessage("No servers configured")
            return
        server = self.servers[self.server_combo.currentIndex()]

        # Reuse an already-open guide window instead of stacking duplicates
        if self._epg_grid_dialog is not None:
            try:
                self._epg_grid_dialog.close()
            except RuntimeError:
                pass
            self._epg_grid_dialog = None

        dialog = EPGGridDialog(server, self.theme, self)
        self._epg_grid_dialog = dialog
        dialog.finished.connect(lambda _: setattr(self, '_epg_grid_dialog', None))
        dialog.show()
        dialog.load_data()

    def play_channel_from_table(self, item):
        """Play channel from table selection"""
        row = item.row()
        channel_item = self.channel_list.item(row, 1)  # Get name column item
        channel_data = channel_item.data(Qt.UserRole)  # Original data is stored here
        self.play_channel_by_data(channel_data)

    def play_channel_by_data(self, channel_data):
        """Play channel using channel data"""
        try:
            self.current_channel_data = channel_data
            server = self.servers[self.server_combo.currentIndex()]
            server_url = server['url']
            print(f"Debug: Playing channel from server: {server_url}")
            
            # Create auth string if credentials exist
            auth_string = ''
            auth = None
            if server.get('username') or server.get('password'):
                auth = (server.get('username', ''), server.get('password', ''))
                auth_string = f"{server.get('username', '')}:{server.get('password', '')}@"
            
            # Use channel UUID directly from stored data
            channel_uuid = channel_data['uuid']
            
            if channel_uuid:
                # Create media URL with auth if needed
                if auth_string:
                    # Ensure server_url starts with http:// or https://
                    if not server_url.startswith(('http://', 'https://')):
                        server_url = f'http://{server_url}'
                    
                    # Insert auth string after http:// or https://
                    stream_url = server_url.replace('://', f'://{auth_string}')
                    stream_url = f'{stream_url}/stream/channel/{channel_uuid}'

                else:
                    if not server_url.startswith(('http://', 'https://')):
                        server_url = f'http://{server_url}'
                    stream_url = f'{server_url}/stream/channel/{channel_uuid}'
                print(f"Debug: Stream URL: {stream_url}")
                
                media = self.instance.media_new(stream_url)
                self.media_player.set_media(media)
                self.media_player.play()
                print(f"Debug: Started playback")
                self.statusbar.showMessage(f"Playing: {channel_data['name']}")
                if hasattr(self, 'favorites_menu'):
                    self.rebuild_favorites_menu()
            else:
                print(f"Debug: Channel not found: {channel_data['name']}")
                self.statusbar.showMessage("Channel not found")
                
        except Exception as e:
            print(f"Debug: Error in play_channel: {str(e)}")
            self.statusbar.showMessage(f"Playback error: {str(e)}")

    def show_server_status(self):
        """Show server status dialog"""
        try:
            server = self.servers[self.server_combo.currentIndex()]
            dialog = ServerStatusDialog(server, self)
            dialog.show()
        except Exception as e:
            print(f"Debug: Error showing server status: {str(e)}")
            self.statusbar.showMessage("Error showing server status")

    def filter_channels(self, search_text):
        """Filter channel list based on search text"""
        search_text = search_text.lower()
        for row in range(self.channel_list.rowCount()):
            item = self.channel_list.item(row, 1)  # Get name column item
            if item:
                channel_name = item.text().lower()
                self.channel_list.setRowHidden(row, search_text not in channel_name)

    def check_hardware_acceleration(self):
        """Check and print which hardware acceleration method is being used"""
        if not self.media_player:
            return
            
        # This only works if a media is playing
        if not self.media_player.is_playing():
            return
            
        try:
            # Get media statistics - handle different VLC Python binding versions
            media = self.media_player.get_media()
            if not media:
                print("No media currently playing")
                return
                
            # Different versions of python-vlc have different APIs for get_stats
            try:
                # Newer versions (direct call)
                stats = media.get_stats()
                print("VLC Playback Statistics:")
                print(f"Decoded video blocks: {stats.decoded_video}")
                print(f"Displayed pictures: {stats.displayed_pictures}")
                print(f"Lost pictures: {stats.lost_pictures}")
            except TypeError:
                # Older versions (requiring a stats object parameter)
                stats = vlc.MediaStats()
                media.get_stats(stats)
                print("VLC Playback Statistics:")
                print(f"Decoded video blocks: {stats.decoded_video}")
                print(f"Displayed pictures: {stats.displayed_pictures}")
                print(f"Lost pictures: {stats.lost_pictures}")
            
            # Check if hardware decoding is enabled
            if hasattr(self.media_player, 'get_role'):
                print(f"Media player role: {self.media_player.get_role()}")
            
            # Try to get more detailed hardware acceleration info
            print("Hardware acceleration is active if you see 'Using ... for hardware decoding' in the logs above")
            print("For more details, run VLC with the same content and use:")
            print("Tools -> Messages -> Info to see which decoder is being used")
            
        except Exception as e:
            print(f"Error checking hardware acceleration: {e}")
            print(f"Traceback: {traceback.format_exc()}")



def _epg_text(value, fallback=''):
    """TVHeadend EPG text fields come either as a plain string or as
    {'eng': '...'} language dicts - normalize to a plain string."""
    if isinstance(value, dict):
        if value:
            return next(iter(value.values()))
        return fallback
    if value:
        return str(value)
    return fallback


# Layout constants for the all-channel EPG timeline grid
EPG_PX_PER_MIN = 4
EPG_ROW_HEIGHT = 44
EPG_CHANNEL_COL_WIDTH = 190
EPG_HEADER_HEIGHT = 36
EPG_WINDOW_HOURS = 48
EPG_NEWSPAPER_SLOT_MINUTES = 30


class SyncedScrollArea(QScrollArea):
    """A QScrollArea that forwards its own wheel events to another scroll
    area, so the channel column and the time ruler scroll together with
    the main program grid as if it were a single widget."""
    def __init__(self, sync_target_getter, parent=None):
        super().__init__(parent)
        self._sync_target_getter = sync_target_getter

    def wheelEvent(self, event):
        target = self._sync_target_getter()
        if target is not None:
            QApplication.sendEvent(target.viewport(), event)
        else:
            super().wheelEvent(event)


class EPGRulerWidget(QWidget):
    """Draws the hour/day timeline header above the program grid"""
    def __init__(self, window_start, total_minutes, theme, parent=None):
        super().__init__(parent)
        self.window_start = window_start
        self.total_minutes = total_minutes
        self.theme = theme
        self.setFixedHeight(EPG_HEADER_HEIGHT)
        self.setMinimumWidth(int(total_minutes * EPG_PX_PER_MIN))

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    def set_window(self, window_start, total_minutes):
        self.window_start = window_start
        self.total_minutes = total_minutes
        self.setMinimumWidth(int(total_minutes * EPG_PX_PER_MIN))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(self.theme['header_bg']))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)

        current = self.window_start.replace(minute=0, second=0, microsecond=0)
        end_time = self.window_start + timedelta(minutes=self.total_minutes)
        last_day = None
        while current <= end_time:
            x = (current - self.window_start).total_seconds() / 60 * EPG_PX_PER_MIN
            painter.setPen(QPen(QColor(self.theme['border'])))
            painter.drawLine(int(x), 0, int(x), EPG_HEADER_HEIGHT)
            painter.setPen(QColor(self.theme['text']))
            painter.drawText(int(x) + 4, EPG_HEADER_HEIGHT - 6, current.strftime('%H:%M'))
            if current.day != last_day:
                painter.setPen(QColor(self.theme['accent']))
                painter.drawText(int(x) + 4, 13, current.strftime('%a %d.%m'))
                last_day = current.day
            current += timedelta(hours=1)
        painter.end()


class EPGChannelColumn(QWidget):
    """Left column listing channel names/numbers, one row per channel,
    kept in vertical sync with the program grid."""
    def __init__(self, channels, theme, parent=None):
        super().__init__(parent)
        self.channels = channels
        self.theme = theme
        self.setFixedWidth(EPG_CHANNEL_COL_WIDTH)
        self.setMinimumHeight(max(1, len(channels)) * EPG_ROW_HEIGHT)

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(self.theme['panel_bg']))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        for i, ch in enumerate(self.channels):
            y = i * EPG_ROW_HEIGHT
            bg = QColor(self.theme['alt_row']) if i % 2 else QColor(self.theme['panel_bg'])
            painter.fillRect(0, y, self.width(), EPG_ROW_HEIGHT, bg)
            painter.setPen(QPen(QColor(self.theme['border'])))
            painter.drawLine(0, y + EPG_ROW_HEIGHT, self.width(), y + EPG_ROW_HEIGHT)
            painter.setPen(QColor(self.theme['text']))
            number = ch.get('number')
            label = f"{number}  {ch.get('name', '')}" if number else ch.get('name', '')
            elided = metrics.elidedText(label, Qt.ElideRight, self.width() - 12)
            painter.drawText(8, y + EPG_ROW_HEIGHT // 2 + 4, elided)
        painter.end()


class EPGGridCanvas(QWidget):
    """Paints the actual program blocks: one row per channel, positioned
    and sized proportionally to their start/stop time along a shared
    timeline - the multi-channel EPG grid."""
    programClicked = pyqtSignal(dict, dict)  # event data, channel data

    def __init__(self, channels, events_by_channel, window_start, total_minutes, theme, parent=None):
        super().__init__(parent)
        self.channels = channels
        self.events_by_channel = events_by_channel
        self.window_start = window_start
        self.total_minutes = total_minutes
        self.theme = theme
        self.setMinimumSize(int(total_minutes * EPG_PX_PER_MIN), max(1, len(channels)) * EPG_ROW_HEIGHT)
        self._blocks = []  # (QRectF, event, channel) for hit-testing clicks

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    def set_window(self, window_start, total_minutes):
        self.window_start = window_start
        self.total_minutes = total_minutes
        self.setMinimumSize(int(total_minutes * EPG_PX_PER_MIN), max(1, len(self.channels)) * EPG_ROW_HEIGHT)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(self.theme['panel_bg']))
        self._blocks = []

        now = datetime.now()
        window_end = self.window_start + timedelta(minutes=self.total_minutes)

        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        metrics = QFontMetrics(font)

        for row, channel in enumerate(self.channels):
            y = row * EPG_ROW_HEIGHT
            bg = QColor(self.theme['alt_row']) if row % 2 else QColor(self.theme['panel_bg'])
            painter.fillRect(0, y, self.width(), EPG_ROW_HEIGHT, bg)
            painter.setPen(QPen(QColor(self.theme['border'])))
            painter.drawLine(0, y + EPG_ROW_HEIGHT, self.width(), y + EPG_ROW_HEIGHT)

            events = self.events_by_channel.get(channel.get('uuid'), [])
            for ev in events:
                try:
                    ev_start = datetime.fromtimestamp(ev['start'])
                    ev_stop = datetime.fromtimestamp(ev['stop'])
                except (KeyError, TypeError, ValueError, OSError):
                    continue
                if ev_stop <= self.window_start or ev_start >= window_end:
                    continue
                clip_start = max(ev_start, self.window_start)
                clip_stop = min(ev_stop, window_end)
                x1 = (clip_start - self.window_start).total_seconds() / 60 * EPG_PX_PER_MIN
                x2 = (clip_stop - self.window_start).total_seconds() / 60 * EPG_PX_PER_MIN
                width = max(2, x2 - x1)
                rect = QRectF(x1, y + 2, width, EPG_ROW_HEIGHT - 4)

                is_now = ev_start <= now <= ev_stop
                block_color = QColor(self.theme['epg_now']) if is_now else QColor(self.theme['epg_future'])
                painter.setPen(QPen(QColor(self.theme['epg_border'])))
                painter.setBrush(QBrush(block_color))
                painter.drawRoundedRect(rect, 3, 3)

                title = _epg_text(ev.get('title'), 'No title')
                text_rect = rect.adjusted(6, 0, -6, 0)
                painter.setPen(QColor(self.theme['text']))
                elided = metrics.elidedText(title, Qt.ElideRight, max(0, int(text_rect.width())))
                painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)

                self._blocks.append((rect, ev, channel))

        if self.window_start <= now <= window_end:
            now_x = (now - self.window_start).total_seconds() / 60 * EPG_PX_PER_MIN
            painter.setPen(QPen(QColor(self.theme['now_line']), 2))
            painter.drawLine(int(now_x), 0, int(now_x), self.height())

        painter.end()

    def mousePressEvent(self, event):
        pos = event.pos()
        for rect, ev, channel in self._blocks:
            if rect.contains(pos):
                self.programClicked.emit(ev, channel)
                return
        super().mousePressEvent(event)


class ProgramInfoDialog(QDialog):
    """Popup shown when clicking a program block: details + quick actions"""
    def __init__(self, event_data, channel, server, main_window, parent=None):
        super().__init__(parent)
        self.event_data = event_data
        self.channel = channel
        self.server = server
        self.main_window = main_window
        self.setWindowTitle(_epg_text(event_data.get('title'), 'Program'))
        self.setModal(True)
        self.resize(420, 260)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        title = _epg_text(self.event_data.get('title'), 'Unknown title')
        subtitle = _epg_text(self.event_data.get('subtitle'), '')
        description = _epg_text(
            self.event_data.get('description'),
            _epg_text(self.event_data.get('summary'), ''))

        start_time = datetime.fromtimestamp(self.event_data['start']).strftime('%a %d.%m.  %H:%M')
        stop_time = datetime.fromtimestamp(self.event_data['stop']).strftime('%H:%M')

        title_label = QLabel(f"<b>{title}</b>")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        if subtitle:
            sub_label = QLabel(subtitle)
            sub_label.setWordWrap(True)
            layout.addWidget(sub_label)

        channel_label = QLabel(f"{self.channel.get('name', '')}  \u2022  {start_time} - {stop_time}")
        channel_label.setObjectName("serverLabel")
        layout.addWidget(channel_label)

        desc_label = QLabel(description or "No description available")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignTop)
        layout.addWidget(desc_label, stretch=1)

        btn_layout = QHBoxLayout()
        play_btn = QPushButton("Play Channel")
        play_btn.clicked.connect(self.play_channel)
        record_btn = QPushButton("Schedule Recording")
        record_btn.clicked.connect(self.schedule_recording)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(play_btn)
        btn_layout.addWidget(record_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def play_channel(self):
        if self.main_window is not None:
            self.main_window.play_channel_by_data(self.channel)
        self.accept()

    def schedule_recording(self):
        try:
            auth = None
            if self.server.get('username') or self.server.get('password'):
                auth = (self.server.get('username', ''), self.server.get('password', ''))
            title = _epg_text(self.event_data.get('title'), 'Scheduled Recording')
            description = _epg_text(self.event_data.get('description'), '')
            conf_data = {
                "start": self.event_data['start'],
                "stop": self.event_data['stop'],
                "channel": self.event_data.get('channelUuid', self.channel.get('uuid')),
                "title": {"eng": title},
                "description": {"eng": description},
                "comment": "Scheduled via TVHplayer",
            }
            base_url = self.server['url']
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"http://{base_url}"
            data = {'conf': json.dumps(conf_data)}
            response = requests.post(f'{base_url}/api/dvr/entry/create', data=data, auth=auth)
            if response.status_code == 200:
                QMessageBox.information(self, "Success", f"Recording scheduled for {title}")
            else:
                QMessageBox.warning(self, "Error", f"Failed to schedule recording: {response.text}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to schedule recording: {e}")


class EPGGridDialog(QDialog):
    """Program guide: all channels as rows against one
    shared, scrollable timeline (instead of one dialog per channel)."""
    def __init__(self, server, theme, main_window=None):
        super().__init__(main_window)
        self.server = server
        self.theme = theme
        self.main_window = main_window
        self.setWindowTitle(f"Program Guide - {server.get('name', '')}")
        self.setModal(False)
        self.resize(1050, 620)
        self.channels = []
        self.events_by_channel = {}
        self.window_start = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        self.total_minutes = EPG_WINDOW_HOURS * 60
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        toolbar_layout = QHBoxLayout()
        self.prev_btn = QPushButton("\u25c0 6h")
        self.prev_btn.clicked.connect(lambda: self.scroll_by_hours(-6))
        self.now_btn = QPushButton("Now")
        self.now_btn.clicked.connect(self.jump_to_now)
        self.next_btn = QPushButton("6h \u25b6")
        self.next_btn.clicked.connect(lambda: self.scroll_by_hours(6))
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_data)

        # View toggle: Timeline (channels as rows) vs. Newspaper (channels
        # as columns, time running down the rows - the classic TV-guide page)
        self.view_toggle_group = QActionGroup(self)
        self.timeline_view_btn = QPushButton("Timeline")
        self.timeline_view_btn.setCheckable(True)
        self.timeline_view_btn.setChecked(True)
        self.timeline_view_btn.clicked.connect(lambda: self.set_view_mode('timeline'))
        self.newspaper_view_btn = QPushButton("Guide (Columns)")
        self.newspaper_view_btn.setCheckable(True)
        self.newspaper_view_btn.clicked.connect(lambda: self.set_view_mode('newspaper'))

        self.info_label = QLabel("Loading program guide...")
        self.info_label.setObjectName("serverLabel")

        toolbar_layout.addWidget(self.prev_btn)
        toolbar_layout.addWidget(self.now_btn)
        toolbar_layout.addWidget(self.next_btn)
        toolbar_layout.addWidget(self.refresh_btn)
        toolbar_layout.addSpacing(12)
        toolbar_layout.addWidget(self.timeline_view_btn)
        toolbar_layout.addWidget(self.newspaper_view_btn)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.info_label)
        layout.addLayout(toolbar_layout)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # --- Page 1: Timeline view (channels as rows) ---
        timeline_page = QWidget()
        grid_layout = QGridLayout(timeline_page)
        grid_layout.setSpacing(0)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        corner = QWidget()
        corner.setFixedSize(EPG_CHANNEL_COL_WIDTH, EPG_HEADER_HEIGHT)
        grid_layout.addWidget(corner, 0, 0)

        self.ruler = EPGRulerWidget(self.window_start, self.total_minutes, self.theme)
        self.ruler_scroll = SyncedScrollArea(lambda: self.grid_scroll, parent=self)
        self.ruler_scroll.setWidget(self.ruler)
        self.ruler_scroll.setFixedHeight(EPG_HEADER_HEIGHT)
        self.ruler_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ruler_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ruler_scroll.setWidgetResizable(False)
        self.ruler_scroll.setFrameShape(QFrame.NoFrame)
        grid_layout.addWidget(self.ruler_scroll, 0, 1)

        self.channel_column = EPGChannelColumn([], self.theme)
        self.channel_scroll = SyncedScrollArea(lambda: self.grid_scroll, parent=self)
        self.channel_scroll.setWidget(self.channel_column)
        self.channel_scroll.setFixedWidth(EPG_CHANNEL_COL_WIDTH)
        self.channel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.channel_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.channel_scroll.setWidgetResizable(False)
        self.channel_scroll.setFrameShape(QFrame.NoFrame)
        grid_layout.addWidget(self.channel_scroll, 1, 0)

        self.canvas = EPGGridCanvas([], {}, self.window_start, self.total_minutes, self.theme)
        self.canvas.programClicked.connect(self.on_program_clicked)
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidget(self.canvas)
        self.grid_scroll.setWidgetResizable(False)
        self.grid_scroll.setFrameShape(QFrame.NoFrame)
        grid_layout.addWidget(self.grid_scroll, 1, 1)

        grid_layout.setColumnStretch(1, 1)
        grid_layout.setRowStretch(1, 1)

        self.grid_scroll.horizontalScrollBar().valueChanged.connect(
            self.ruler_scroll.horizontalScrollBar().setValue)
        self.grid_scroll.verticalScrollBar().valueChanged.connect(
            self.channel_scroll.verticalScrollBar().setValue)

        self.stack.addWidget(timeline_page)

        # --- Page 2: Newspaper view (channels as columns, time as rows) ---
        self.newspaper_table = QTableWidget()
        self.newspaper_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.newspaper_table.setSelectionMode(QTableWidget.NoSelection)
        self.newspaper_table.setWordWrap(True)
        self.newspaper_table.verticalHeader().setDefaultSectionSize(30)
        self.newspaper_table.horizontalHeader().setDefaultSectionSize(170)
        # Pixel-based scrolling so our time->offset math (used for "Now"
        # and the 6h prev/next buttons) lines up with the actual scrollbar
        self.newspaper_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.newspaper_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.newspaper_table.cellClicked.connect(self._on_newspaper_cell_clicked)
        self._newspaper_cell_events = {}
        self.stack.addWidget(self.newspaper_table)

    def set_view_mode(self, mode):
        self.timeline_view_btn.setChecked(mode == 'timeline')
        self.newspaper_view_btn.setChecked(mode == 'newspaper')
        self.stack.setCurrentIndex(0 if mode == 'timeline' else 1)

    def apply_theme(self, theme):
        self.theme = theme
        self.ruler.set_theme(theme)
        self.channel_column.set_theme(theme)
        self.canvas.set_theme(theme)
        self.refresh_newspaper_table()

    def load_data(self):
        self.info_label.setText("Loading program guide...")
        QApplication.processEvents()
        try:
            auth = None
            if self.server.get('username') or self.server.get('password'):
                auth = (self.server.get('username', ''), self.server.get('password', ''))
            base_url = self.server['url']
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"http://{base_url}"

            # All channels
            ch_resp = requests.get(f'{base_url}/api/channel/grid?limit=10000', auth=auth, timeout=10)
            ch_entries = ch_resp.json().get('entries', [])
            self.channels = sorted(
                ch_entries,
                key=lambda c: (c.get('number') or float('inf'), (c.get('name') or '').lower())
            )

            # EPG events for ALL channels in a single request (this is the
            # part that replaces the old per-channel "Show EPG" popup)
            epg_resp = requests.get(
                f'{base_url}/api/epg/events/grid',
                params={'limit': 5000},
                auth=auth, timeout=15
            )
            events = epg_resp.json().get('entries', [])

            events_by_channel = {}
            for ev in events:
                uuid = ev.get('channelUuid')
                if not uuid:
                    continue
                events_by_channel.setdefault(uuid, []).append(ev)
            for uuid in events_by_channel:
                events_by_channel[uuid].sort(key=lambda e: e.get('start', 0))
            self.events_by_channel = events_by_channel

            self.channel_column.channels = self.channels
            self.channel_column.setMinimumHeight(max(1, len(self.channels)) * EPG_ROW_HEIGHT)
            self.canvas.channels = self.channels
            self.canvas.events_by_channel = events_by_channel
            self.canvas.setMinimumSize(
                int(self.total_minutes * EPG_PX_PER_MIN), max(1, len(self.channels)) * EPG_ROW_HEIGHT
            )
            self.channel_column.update()
            self.canvas.update()
            self.refresh_newspaper_table()
            self.info_label.setText(f"{len(self.channels)} channels \u2022 {len(events)} programs")
            self.jump_to_now()
        except Exception as e:
            self.info_label.setText(f"Error loading guide: {e}")

    def refresh_newspaper_table(self):
        """Fill the newspaper-style grid: channels as columns, half-hour
        time slots as rows, programs spanning multiple rows via cell merge."""
        table = self.newspaper_table
        table.clearContents()
        table.setColumnCount(len(self.channels))
        table.setHorizontalHeaderLabels([c.get('name', '') for c in self.channels])

        num_slots = max(1, int(self.total_minutes // EPG_NEWSPAPER_SLOT_MINUTES))
        table.setRowCount(num_slots)
        row_labels = []
        last_day = None
        for i in range(num_slots):
            slot_time = self.window_start + timedelta(minutes=i * EPG_NEWSPAPER_SLOT_MINUTES)
            if slot_time.day != last_day:
                row_labels.append(slot_time.strftime('%a %H:%M'))
                last_day = slot_time.day
            else:
                row_labels.append(slot_time.strftime('%H:%M'))
        table.setVerticalHeaderLabels(row_labels)

        self._newspaper_cell_events = {}
        window_end = self.window_start + timedelta(minutes=self.total_minutes)

        for col, channel in enumerate(self.channels):
            events = self.events_by_channel.get(channel.get('uuid'), [])
            for ev in events:
                try:
                    ev_start = datetime.fromtimestamp(ev['start'])
                    ev_stop = datetime.fromtimestamp(ev['stop'])
                except (KeyError, TypeError, ValueError, OSError):
                    continue
                if ev_stop <= self.window_start or ev_start >= window_end:
                    continue
                clip_start = max(ev_start, self.window_start)
                clip_stop = min(ev_stop, window_end)
                start_row = int((clip_start - self.window_start).total_seconds() // 60 // EPG_NEWSPAPER_SLOT_MINUTES)
                minutes_span = (clip_stop - clip_start).total_seconds() / 60
                span = max(1, -(-int(minutes_span) // EPG_NEWSPAPER_SLOT_MINUTES))
                if start_row < 0 or start_row >= num_slots:
                    continue
                span = min(span, num_slots - start_row)

                title = _epg_text(ev.get('title'), 'No title')
                item = QTableWidgetItem(title)
                item.setToolTip(title)
                is_now = ev_start <= datetime.now() <= ev_stop
                bg = self.theme['epg_now'] if is_now else self.theme['epg_future']
                item.setBackground(QBrush(QColor(bg)))
                item.setForeground(QBrush(QColor(self.theme['text'])))
                table.setItem(start_row, col, item)
                if span > 1:
                    table.setSpan(start_row, col, span, 1)
                self._newspaper_cell_events[(start_row, col)] = (ev, channel)

    def _on_newspaper_cell_clicked(self, row, col):
        data = self._newspaper_cell_events.get((row, col))
        if data:
            event_data, channel = data
            self.on_program_clicked(event_data, channel)

    def jump_to_now(self):
        now = datetime.now()
        x = (now - self.window_start).total_seconds() / 60 * EPG_PX_PER_MIN
        target = max(0, int(x - 100))
        self.grid_scroll.horizontalScrollBar().setValue(target)

        row_height = self.newspaper_table.verticalHeader().defaultSectionSize()
        minutes_since_start = (now - self.window_start).total_seconds() / 60
        y = minutes_since_start / EPG_NEWSPAPER_SLOT_MINUTES * row_height
        self.newspaper_table.verticalScrollBar().setValue(max(0, int(y - row_height * 3)))

    def scroll_by_hours(self, hours):
        bar = self.grid_scroll.horizontalScrollBar()
        bar.setValue(bar.value() + int(hours * 60 * EPG_PX_PER_MIN))
        v_bar = self.newspaper_table.verticalScrollBar()
        rows = int(hours * 60 / EPG_NEWSPAPER_SLOT_MINUTES)
        v_bar.setValue(v_bar.value() + rows * self.newspaper_table.verticalHeader().defaultSectionSize())

    def on_program_clicked(self, event_data, channel):
        popup = ProgramInfoDialog(event_data, channel, self.server, self.main_window, self)
        popup.exec_()


class EPGDialog(QDialog):
    def __init__(self, channel_name, epg_data, server, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"EPG Guide - {channel_name}")
        self.setModal(False)
        self.resize(800, 500)
        self.server = server
        self.channel_name = channel_name
        self.setup_ui(epg_data)
        
    def setup_ui(self, epg_data):
        layout = QVBoxLayout(self)
        
        # Create list widget for EPG entries
        self.epg_list = QListWidget()
        layout.addWidget(self.epg_list)
        
        # Add EPG entries to list with record buttons
        for entry in epg_data:
            # Create widget to hold program info and record button
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 2, 5, 2)
            # Get start and stop times
            start_time = datetime.fromtimestamp(entry['start']).strftime('%H:%M')
            stop_time = datetime.fromtimestamp(entry['stop']).strftime('%H:%M')
            
            # Get title and description
            if isinstance(entry.get('title'), dict):
                title = entry['title'].get('eng', 'No title')
            else:
                title = str(entry.get('title', 'No title'))
                
            if isinstance(entry.get('description'), dict):
                description = entry['description'].get('eng', 'No description')
            else:
                description = str(entry.get('description', 'No description'))
                
                # Create label for program info
                info_text = f"{start_time} - {stop_time}: {title}"
                info_label = QLabel(info_text)
                info_label.setToolTip(description)
                item_layout.addWidget(info_label, stretch=1)
                
                # Create record button with unicode icon
                record_btn = QPushButton("⏺")  # Unicode record symbol
                record_btn.setFixedWidth(32)  # Make button smaller since it's just an icon
                record_btn.setFixedHeight(32)  # Make it square
                record_btn.setStyleSheet("""
                    QPushButton {
                        color: red;
                        font-size: 16px;
                        border: 1px solid #ccc;
                        border-radius: 16px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #f0f0f0;
                    }
                    QPushButton:pressed {
                        background-color: #e0e0e0;
                    }
                """)
                record_btn.setToolTip("Schedule Recording")
                record_btn.clicked.connect(
                    lambda checked, e=entry: self.schedule_recording(e))
                item_layout.addWidget(record_btn)
                
                # Create list item and set custom widget
                list_item = QListWidgetItem(self.epg_list)
                list_item.setSizeHint(item_widget.sizeHint())
                self.epg_list.addItem(list_item)
                self.epg_list.setItemWidget(list_item, item_widget)
                try:
                    self.epg_list.addItem(list_item)
                    self.epg_list.setItemWidget(list_item, item_widget)
                except Exception as e:
                    print(f"Debug: Error processing EPG entry: {str(e)}")
                    print(f"Debug: Problematic entry: {entry}")
                    continue

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
    def schedule_recording(self, entry):
        """Schedule a recording for the selected EPG entry"""
        try:
            print(f"Debug: Scheduling recording for: {entry.get('title', 'Unknown')}")
            
            # Create auth if needed
            auth = None
            if self.server.get('username') or self.server.get('password'):
                auth = (self.server.get('username', ''), self.server.get('password', ''))
            
            # Prepare recording request with proper language object structure
            conf_data = {
                "start": entry['start'],
                "stop": entry['stop'],
                "channel": entry['channelUuid'],
                "title": {
                    "eng": entry.get('title', 'Scheduled Recording')
                },
                "description": {
                    "eng": entry.get('description', '')
                },
                "comment": "Scheduled via TVHplayer"
            }
            
            # Convert to string format as expected by the API
            data = {'conf': json.dumps(conf_data)}
            print(f"Debug: Recording data: {data}")
            
            # Make recording request
            record_url = f'{self.server["url"]}/api/dvr/entry/create'
            print(f"Debug: Sending recording request to: {record_url}")
            
            response = requests.post(record_url, data=data, auth=auth)
            print(f"Debug: Recording response status: {response.status_code}")
            print(f"Debug: Recording response: {response.text}")
            
            if response.status_code == 200:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Recording scheduled successfully for {entry.get('title', 'Unknown')}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to schedule recording: {response.text}"
                )
                
        except Exception as e:
            print(f"Debug: Error scheduling recording: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to schedule recording: {str(e)}"
            )

class RecordingStatusDialog(QDialog):
    def __init__(self, channel_name, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recording Status")
        self.setModal(False)  # Allow interaction with main window
        self.resize(400, 200)
        self.setup_ui(channel_name, file_path)
        
    def setup_ui(self, channel_name, file_path):
        layout = QVBoxLayout(self)
        
        # Channel name
        channel_label = QLabel(f"Recording: {channel_name}")
        channel_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(channel_label)
        
        # File path
        path_label = QLabel(f"Saving to: {file_path}")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)
        
        # Duration
        self.duration_label = QLabel("Duration: 00:00:00")
        layout.addWidget(self.duration_label)
        
        # File size
        self.size_label = QLabel("File size: 0 MB")
        layout.addWidget(self.size_label)
        
        # Status message
        self.status_label = QLabel("Status: Recording")
        self.status_label.setStyleSheet("color: green;")
        layout.addWidget(self.status_label)
        
        # Stop button
        stop_btn = QPushButton("Stop Recording")
        stop_btn.clicked.connect(self.stop_requested)
        layout.addWidget(stop_btn)
        
        # Start time for duration calculation
        self.start_time = time.time()
        
    def update_status(self, file_size, is_stalled=False):
        """Update the dialog with current recording status"""
        # Update duration
        duration = int(time.time() - self.start_time)
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        self.duration_label.setText(f"Duration: {hours:02d}:{minutes:02d}:{seconds:02d}")
        
        # Update file size
        size_mb = file_size / (1024 * 1024)  # Convert to MB
        self.size_label.setText(f"File size: {size_mb:.2f} MB")
        
        # Update status message
        if is_stalled:
            self.status_label.setText("Status: Stalled - Attempting recovery")
            self.status_label.setStyleSheet("color: orange;")
        else:
            self.status_label.setText("Status: Recording")
            self.status_label.setStyleSheet("color: green;")
    
    def stop_requested(self):
        """Signal that user wants to stop recording"""
        self.accept()

def main():
    """Main entry point for the application"""
    try:
        # Force XCB instead of Wayland on Linux - this helps VLC's video
        # embedding work correctly there. Windows/macOS have no XCB
        # plugin at all, so setting this unconditionally broke every
        # Windows build ("Could not find the Qt platform plugin 'xcb'").
        if sys.platform.startswith('linux'):
            QCoreApplication.setAttribute(Qt.AA_X11InitThreads, True)
            os.environ["QT_QPA_PLATFORM"] = "xcb"
        
        app = QApplication(sys.argv)
        player = TVHeadendClient()
        player.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error starting application: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == '__main__':
    main()