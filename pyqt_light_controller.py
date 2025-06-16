#!/usr/bin/env python3
import sys
import socket
import threading
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QPushButton, QLabel, 
                            QLineEdit, QTextEdit, QGroupBox, QFrame, QMessageBox,
                            QStatusBar, QSplitter, QCheckBox, QSlider, QComboBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QPixmap, QPainter

class LightControlThread(QThread):
    """Thread for handling TCP communication"""
    status_updated = pyqtSignal(str, bool)  # light_name, state
    connection_changed = pyqtSignal(bool)   # connected
    message_received = pyqtSignal(str)      # message
    
    def __init__(self):
        super().__init__()
        self.socket = None
        self.connected = False
        self.host = ""
        self.port = 8080
        self.running = False
        
    def connect_to_esp32(self, host, port):
        self.host = host
        self.port = port
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((host, port))
            self.connected = True
            self.running = True
            self.connection_changed.emit(True)
            
            # Read welcome message
            welcome = self.socket.recv(1024).decode('utf-8')
            self.message_received.emit(f"Connected: {welcome}")
            
            # Start listening thread
            self.start()
            return True
            
        except Exception as e:
            self.message_received.emit(f"Connection failed: {e}")
            self.connection_changed.emit(False)
            return False
    
    def disconnect(self):
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.connection_changed.emit(False)
        self.message_received.emit("Disconnected")
    
    def send_command(self, command):
        if not self.connected or not self.socket:
            return False
        
        try:
            self.socket.send((command + '\n').encode('utf-8'))
            self.message_received.emit(f"Sent: {command}")
            return True
        except Exception as e:
            self.message_received.emit(f"Send error: {e}")
            self.connected = False
            self.connection_changed.emit(False)
            return False
    
    def run(self):
        """Listen for responses from ESP32"""
        while self.running and self.connected:
            try:
                if self.socket:
                    self.socket.settimeout(1.0)
                    data = self.socket.recv(1024).decode('utf-8')
                    if data:
                        self.message_received.emit(f"Received: {data.strip()}")
                        # Parse status updates
                        self.parse_status_response(data)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.message_received.emit(f"Receive error: {e}")
                    self.connected = False
                    self.connection_changed.emit(False)
                break
    
    def parse_status_response(self, data):
        """Parse status response and emit signals"""
        lines = data.strip().split('\n')
        for line in lines:
            if ':' in line and ('ON' in line or 'OFF' in line):
                parts = line.split(':')
                if len(parts) >= 2:
                    light_info = parts[0].strip()
                    status = parts[1].strip()
                    
                    # Extract light name
                    if '(' in light_info:
                        light_name = light_info.split('(')[0].strip()
                    else:
                        light_name = light_info
                    
                    is_on = 'ON' in status
                    self.status_updated.emit(light_name, is_on)

class LightControlWidget(QFrame):
    """Individual light control widget with XP styling"""
    
    def __init__(self, light_name, display_name, parent=None):
        super().__init__(parent)
        self.light_name = light_name
        self.display_name = display_name
        self.is_on = False
        self.parent_window = parent
        
        self.setup_ui()
        self.apply_xp_style()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Light name label
        self.name_label = QLabel(self.display_name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setFont(QFont("Tahoma", 9, QFont.Bold))
        
        # Status indicator
        self.status_label = QLabel("OFF")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Tahoma", 12, QFont.Bold))
        self.status_label.setMinimumHeight(30)
        
        # Control buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(4)
        
        self.on_button = QPushButton("ON")
        self.off_button = QPushButton("OFF")
        self.toggle_button = QPushButton("Toggle")
        
        for btn in [self.on_button, self.off_button, self.toggle_button]:
            btn.setFont(QFont("Tahoma", 8))
            btn.setMinimumHeight(25)
        
        button_layout.addWidget(self.on_button)
        button_layout.addWidget(self.off_button)
        button_layout.addWidget(self.toggle_button)
        
        # Connect signals
        self.on_button.clicked.connect(lambda: self.send_command("ON"))
        self.off_button.clicked.connect(lambda: self.send_command("OFF"))
        self.toggle_button.clicked.connect(lambda: self.send_command("TOGGLE"))
        
        layout.addWidget(self.name_label)
        layout.addWidget(self.status_label)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setFixedSize(140, 120)
    
    def apply_xp_style(self):
        """Apply Windows XP-like styling"""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(1)
        
        # XP-style colors
        self.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border: 2px outset #d4d0c8;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #e1e1e1;
                border: 1px outset #d4d0c8;
                border-radius: 2px;
                padding: 2px 6px;
                font-family: Tahoma;
                font-size: 8pt;
            }
            QPushButton:hover {
                background-color: #e5f3ff;
                border: 1px outset #316ac5;
            }
            QPushButton:pressed {
                background-color: #cce4ff;
                border: 1px inset #316ac5;
            }
            QLabel {
                background-color: transparent;
                color: #000000;
            }
        """)
        
        # Remove this line that causes recursion:
        # self.update_status_display()
    
    def send_command(self, action):
        if self.parent_window and hasattr(self.parent_window, 'comm_thread'):
            command = f"{action} {self.light_name}"
            self.parent_window.comm_thread.send_command(command)
    
    def update_status(self, is_on):
        self.is_on = is_on
        self.update_status_display()
    
    def update_status_display(self):
        if self.is_on:
            self.status_label.setText("ON")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #90EE90;
                    color: #006400;
                    border: 1px inset #d4d0c8;
                    border-radius: 2px;
                    font-weight: bold;
                }
            """)
            # Highlight the frame when on
            self.setStyleSheet("""
            QFrame {
                background-color: #fffacd;
                border: 2px outset #ffd700;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #e1e1e1;
                border: 1px outset #d4d0c8;
                border-radius: 2px;
                padding: 2px 6px;
                font-family: Tahoma;
                font-size: 8pt;
            }
            QPushButton:hover {
                background-color: #e5f3ff;
                border: 1px outset #316ac5;
            }
            QPushButton:pressed {
                background-color: #cce4ff;
                border: 1px inset #316ac5;
            }
            QLabel {
                background-color: transparent;
                color: #000000;
            }
        """)
        else:
            self.status_label.setText("OFF")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #ffcccb;
                    color: #8b0000;
                    border: 1px inset #d4d0c8;
                    border-radius: 2px;
                    font-weight: bold;
                }
            """)
            # Reset frame style when off
            self.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border: 2px outset #d4d0c8;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #e1e1e1;
                border: 1px outset #d4d0c8;
                border-radius: 2px;
                padding: 2px 6px;
                font-family: Tahoma;
                font-size: 8pt;
            }
            QPushButton:hover {
                background-color: #e5f3ff;
                border: 1px outset #316ac5;
            }
            QPushButton:pressed {
                background-color: #cce4ff;
                border: 1px inset #316ac5;
            }
            QLabel {
                background-color: transparent;
                color: #000000;
            }
        """)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.comm_thread = LightControlThread()
        self.light_widgets = {}
        self.setup_ui()
        self.apply_xp_theme()
        self.connect_signals()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_status)
        
    def setup_ui(self):
        self.setWindowTitle("ESP32 Light Controller - Windows XP Style")
        self.setFixedSize(800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Connection group
        conn_group = QGroupBox("Connection Settings")
        conn_group.setFont(QFont("Tahoma", 9, QFont.Bold))
        conn_layout = QHBoxLayout()
        
        self.host_input = QLineEdit("192.168.1.100")
        self.host_input.setPlaceholderText("ESP32 IP Address")
        self.host_input.setFont(QFont("Tahoma", 9))
        
        self.port_input = QLineEdit("8080")
        self.port_input.setPlaceholderText("Port")
        self.port_input.setFixedWidth(60)
        self.port_input.setFont(QFont("Tahoma", 9))
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.setFont(QFont("Tahoma", 9, QFont.Bold))
        self.connect_button.clicked.connect(self.toggle_connection)
        
        self.status_label = QLabel("Disconnected")
        self.status_label.setFont(QFont("Tahoma", 9))
        
        conn_layout.addWidget(QLabel("Host:"))
        conn_layout.addWidget(self.host_input)
        conn_layout.addWidget(QLabel("Port:"))
        conn_layout.addWidget(self.port_input)
        conn_layout.addWidget(self.connect_button)
        conn_layout.addWidget(self.status_label)
        conn_layout.addStretch()
        
        conn_group.setLayout(conn_layout)
        
        # Splitter for lights and console
        splitter = QSplitter(Qt.Vertical)
        
        # Lights control area
        lights_widget = QWidget()
        lights_layout = QVBoxLayout()
        
        # Global controls
        global_group = QGroupBox("Global Controls")
        global_group.setFont(QFont("Tahoma", 9, QFont.Bold))
        global_layout = QHBoxLayout()
        
        self.all_on_button = QPushButton("All Lights ON")
        self.all_off_button = QPushButton("All Lights OFF")
        self.refresh_button = QPushButton("Refresh Status")
        self.auto_refresh_cb = QCheckBox("Auto Refresh (5s)")
        
        for btn in [self.all_on_button, self.all_off_button, self.refresh_button]:
            btn.setFont(QFont("Tahoma", 9))
            btn.setMinimumHeight(30)
        
        self.all_on_button.clicked.connect(lambda: self.send_command("ALL_ON"))
        self.all_off_button.clicked.connect(lambda: self.send_command("ALL_OFF"))
        self.refresh_button.clicked.connect(self.refresh_status)
        self.auto_refresh_cb.toggled.connect(self.toggle_auto_refresh)
        
        global_layout.addWidget(self.all_on_button)
        global_layout.addWidget(self.all_off_button)
        global_layout.addWidget(self.refresh_button)
        global_layout.addWidget(self.auto_refresh_cb)
        global_layout.addStretch()
        
        global_group.setLayout(global_layout)
        
        # Individual light controls
        lights_group = QGroupBox("Light Controls")
        lights_group.setFont(QFont("Tahoma", 9, QFont.Bold))
        lights_grid = QGridLayout()
        lights_grid.setSpacing(10)
        
        # Create light control widgets
        lights_config = [
            ("builtin", "Built-in LED"),
            ("light1", "Light 1"),
            ("light2", "Light 2"),
            ("light3", "Light 3"),
            ("light4", "Light 4")
        ]
        
        row, col = 0, 0
        for light_name, display_name in lights_config:
            widget = LightControlWidget(light_name, display_name, self)
            self.light_widgets[light_name] = widget
            lights_grid.addWidget(widget, row, col)
            
            col += 1
            if col >= 4:  # 4 columns max
                col = 0
                row += 1
        
        lights_group.setLayout(lights_grid)
        
        lights_layout.addWidget(global_group)
        lights_layout.addWidget(lights_group)
        lights_widget.setLayout(lights_layout)
        
        # Console area
        console_group = QGroupBox("Console Output")
        console_group.setFont(QFont("Tahoma", 9, QFont.Bold))
        console_layout = QVBoxLayout()
        
        self.console = QTextEdit()
        self.console.setFont(QFont("Consolas", 9))
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(150)
        
        console_layout.addWidget(self.console)
        console_group.setLayout(console_layout)
        
        # Add to splitter
        splitter.addWidget(lights_widget)
        splitter.addWidget(console_group)
        splitter.setSizes([400, 150])
        
        # Add to main layout
        main_layout.addWidget(conn_group)
        main_layout.addWidget(splitter)
        
        central_widget.setLayout(main_layout)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        self.statusBar().setFont(QFont("Tahoma", 8))
        
        # Initially disable controls
        self.set_controls_enabled(False)
    
    def apply_xp_theme(self):
        """Apply Windows XP theme styling"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
                font-family: Tahoma;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px groove #d4d0c8;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 5px;
                background-color: #f0f0f0;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #000080;
            }
            
            QPushButton {
                background-color: #e1e1e1;
                border: 2px outset #d4d0c8;
                border-radius: 3px;
                padding: 4px 8px;
                font-family: Tahoma;
                font-size: 9pt;
                min-width: 60px;
            }
            
            QPushButton:hover {
                background-color: #e5f3ff;
                border: 2px outset #316ac5;
            }
            
            QPushButton:pressed {
                background-color: #cce4ff;
                border: 2px inset #316ac5;
            }
            
            QPushButton:disabled {
                background-color: #d4d0c8;
                color: #808080;
                border: 2px outset #d4d0c8;
            }
            
            QLineEdit {
                background-color: white;
                border: 2px inset #d4d0c8;
                border-radius: 2px;
                padding: 2px 4px;
                font-family: Tahoma;
                font-size: 9pt;
            }
            
            QLineEdit:focus {
                border: 2px inset #316ac5;
            }
            
            QTextEdit {
                background-color: white;
                border: 2px inset #d4d0c8;
                font-family: Consolas;
                font-size: 9pt;
            }
            
            QLabel {
                color: #000000;
                font-family: Tahoma;
            }
            
            QCheckBox {
                font-family: Tahoma;
                font-size: 9pt;
            }
            
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
                border: 1px solid #d4d0c8;
                background-color: white;
            }
            
            QCheckBox::indicator:checked {
                background-color: #316ac5;
                border: 1px solid #316ac5;
            }
            
            QStatusBar {
                background-color: #f0f0f0;
                border-top: 1px solid #d4d0c8;
                font-family: Tahoma;
                font-size: 8pt;
            }
        """)
    
    def connect_signals(self):
        """Connect communication thread signals"""
        self.comm_thread.connection_changed.connect(self.on_connection_changed)
        self.comm_thread.message_received.connect(self.on_message_received)
        self.comm_thread.status_updated.connect(self.on_status_updated)
    
    @pyqtSlot(bool)
    def on_connection_changed(self, connected):
        if connected:
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.connect_button.setText("Disconnect")
            self.set_controls_enabled(True)
            self.statusBar().showMessage("Connected to ESP32")
        else:
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.connect_button.setText("Connect")
            self.set_controls_enabled(False)
            self.statusBar().showMessage("Disconnected")
            self.refresh_timer.stop()
    
    @pyqtSlot(str)
    def on_message_received(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.console.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    @pyqtSlot(str, bool)
    def on_status_updated(self, light_name, is_on):
        if light_name in self.light_widgets:
            self.light_widgets[light_name].update_status(is_on)
    
    def toggle_connection(self):
        if self.comm_thread.connected:
            self.comm_thread.disconnect()
        else:
            host = self.host_input.text().strip()
            port = int(self.port_input.text().strip() or "8080")
            
            if not host:
                QMessageBox.warning(self, "Error", "Please enter ESP32 IP address")
                return
            
            self.comm_thread.connect_to_esp32(host, port)
    
    def send_command(self, command):
        if self.comm_thread.connected:
            self.comm_thread.send_command(command)
        else:
            QMessageBox.warning(self, "Error", "Not connected to ESP32")
    
    def refresh_status(self):
        self.send_command("STATUS")
    
    def toggle_auto_refresh(self, enabled):
        if enabled and self.comm_thread.connected:
            self.refresh_timer.start(5000)  # 5 seconds
        else:
            self.refresh_timer.stop()
    
    def set_controls_enabled(self, enabled):
        """Enable/disable control widgets"""
        self.all_on_button.setEnabled(enabled)
        self.all_off_button.setEnabled(enabled)
        self.refresh_button.setEnabled(enabled)
        self.auto_refresh_cb.setEnabled(enabled)
        
        for widget in self.light_widgets.values():
            widget.setEnabled(enabled)
    
    def closeEvent(self, event):
        """Handle application close"""
        if self.comm_thread.connected:
            self.comm_thread.disconnect()
        self.comm_thread.quit()
        self.comm_thread.wait()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("ESP32 Light Controller")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("ESP32 Tools")
    
    # Apply Windows XP style
    app.setStyle('Windows')
    
    # Set XP-like palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.Button, QColor(225, 225, 225))
    palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(0, 0, 255))
    palette.setColor(QPalette.Highlight, QColor(49, 106, 197))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Center window on screen
    screen = app.desktop().screenGeometry()
    size = window.geometry()
    window.move((screen.width() - size.width()) // 2,
                (screen.height() - size.height()) // 2)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
