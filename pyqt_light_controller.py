# Trion Esp32 Example
import sys
import socket
import threading
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QPushButton, QLabel, 
                            QLineEdit, QTextEdit, QGroupBox, QFrame, QMessageBox,
                            QStatusBar, QSplitter, QCheckBox, QScrollArea,
                            QSizePolicy, QSpacerItem)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot, QSize
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QResizeEvent

class ResponsiveGridLayout(QGridLayout):
    """Custom grid layout that adapts to container width"""
    
    def __init__(self, min_item_width=140, spacing=10):
        super().__init__()
        self.min_item_width = min_item_width
        self.setSpacing(spacing)
        self.items_list = []
        
    def addResponsiveWidget(self, widget):
        """Add widget that will be repositioned based on available width"""
        self.items_list.append(widget)
        self.repositionItems()
    
    def repositionItems(self):
        """Reposition items based on current width"""
        # Clear current layout
        for i in reversed(range(self.count())):
            self.itemAt(i).widget().setParent(None)
        
        if not self.items_list:
            return
            
        # Calculate columns based on parent width
        parent = self.parent()
        if parent:
            available_width = parent.width() - 40  # Account for margins
            cols = max(1, available_width // (self.min_item_width + self.spacing()))
        else:
            cols = 4  # Default
        
        # Add items to grid
        for i, widget in enumerate(self.items_list):
            row = i // cols
            col = i % cols
            self.addWidget(widget, row, col)

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
                    
                    if '(' in light_info:
                        light_name = light_info.split('(')[0].strip()
                    else:
                        light_name = light_info
                    
                    is_on = 'ON' in status
                    self.status_updated.emit(light_name, is_on)

class ResponsiveLightWidget(QFrame):
    """Responsive light control widget that adapts to different sizes"""
    
    def __init__(self, light_name, display_name, parent=None):
        super().__init__(parent)
        self.light_name = light_name
        self.display_name = display_name
        self.is_on = False
        self.parent_window = parent
        self.compact_mode = False
        
        self.setup_ui()
        self.apply_responsive_style()
        
        # Set size policies
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumSize(120, 100)
        self.setMaximumSize(200, 150)
    
    def setup_ui(self):
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(6)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        
        # Light name label
        self.name_label = QLabel(self.display_name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setFont(QFont("Tahoma", 9, QFont.Bold))
        self.name_label.setWordWrap(True)
        
        # Status indicator
        self.status_label = QLabel("OFF")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Tahoma", 11, QFont.Bold))
        self.status_label.setMinimumHeight(25)
        
        # Control buttons container
        self.button_container = QWidget()
        self.button_layout = QHBoxLayout(self.button_container)
        self.button_layout.setSpacing(3)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create buttons
        self.on_button = QPushButton("ON")
        self.off_button = QPushButton("OFF")
        self.toggle_button = QPushButton("⟲")  # Toggle symbol
        
        # Set button properties
        for btn in [self.on_button, self.off_button, self.toggle_button]:
            btn.setFont(QFont("Tahoma", 8))
            btn.setMinimumHeight(22)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Special styling for toggle button
        self.toggle_button.setMaximumWidth(30)
        self.toggle_button.setToolTip("Toggle Light")
        
        # Add buttons to layout
        self.button_layout.addWidget(self.on_button)
        self.button_layout.addWidget(self.off_button)
        self.button_layout.addWidget(self.toggle_button)
        
        # Connect signals
        self.on_button.clicked.connect(lambda: self.send_command("ON"))
        self.off_button.clicked.connect(lambda: self.send_command("OFF"))
        self.toggle_button.clicked.connect(lambda: self.send_command("TOGGLE"))
        
        # Add to main layout
        self.main_layout.addWidget(self.name_label)
        self.main_layout.addWidget(self.status_label)
        self.main_layout.addWidget(self.button_container)
        
        self.setLayout(self.main_layout)
    
    def apply_responsive_style(self):
        """Apply responsive XP-style styling"""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(1)
        
        base_style = """
            QFrame {
                background-color: #f0f0f0;
                border: 2px outset #d4d0c8;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #e1e1e1;
                border: 1px outset #d4d0c8;
                border-radius: 2px;
                padding: 2px 4px;
                font-family: Tahoma;
                font-size: 8pt;
                min-width: 20px;
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
        """
        self.setStyleSheet(base_style)
    
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
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)
            # Highlight frame when on
            self.setStyleSheet("""
                QFrame {
                    background-color: #fffacd;
                    border: 2px outset #ffd700;
                    border-radius: 4px;
                }
                QPushButton {
                    background-color: #e1e1e1;
                    border: 1px outset #d4d0c8;
                    border-radius: 2px;
                    padding: 2px 4px;
                    font-family: Tahoma;
                    font-size: 8pt;
                    min-width: 20px;
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
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)
            self.apply_responsive_style()
    
    def set_compact_mode(self, compact):
        """Switch between compact and normal mode"""
        self.compact_mode = compact
        if compact:
            self.name_label.setFont(QFont("Tahoma", 8))
            self.status_label.setFont(QFont("Tahoma", 9, QFont.Bold))
            self.status_label.setMinimumHeight(20)
            for btn in [self.on_button, self.off_button, self.toggle_button]:
                btn.setFont(QFont("Tahoma", 7))
                btn.setMinimumHeight(18)
            self.main_layout.setSpacing(4)
            self.setMinimumSize(100, 80)
        else:
            self.name_label.setFont(QFont("Tahoma", 9, QFont.Bold))
            self.status_label.setFont(QFont("Tahoma", 11, QFont.Bold))
            self.status_label.setMinimumHeight(25)
            for btn in [self.on_button, self.off_button, self.toggle_button]:
                btn.setFont(QFont("Tahoma", 8))
                btn.setMinimumHeight(22)
            self.main_layout.setSpacing(6)
            self.setMinimumSize(120, 100)

class ResponsiveMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.comm_thread = LightControlThread()
        self.light_widgets = {}
        self.is_compact_mode = False
        
        self.setup_ui()
        self.apply_responsive_theme()
        self.connect_signals()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_status)
        
        # Resize timer to debounce resize events
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.handle_resize_complete)
        
    def setup_ui(self):
        self.setWindowTitle("ESP32 Light Controller")
        self.setMinimumSize(600, 400)
        self.resize(900, 650)
        
        # Central widget with scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.central_widget = QWidget()
        self.scroll_area.setWidget(self.central_widget)
        self.setCentralWidget(self.scroll_area)
        
        # Main layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Connection group (responsive)
        self.setup_connection_group()
        
        # Splitter for lights and console (responsive)
        self.setup_main_content()
        
        self.central_widget.setLayout(self.main_layout)
        
        # Status bar
        self.statusBar().showMessage("Ready - Resize window to see responsive layout")
        self.statusBar().setFont(QFont("Tahoma", 8))
        
        # Initially disable controls
        self.set_controls_enabled(False)
    
    def setup_connection_group(self):
        """Setup responsive connection group"""
        self.conn_group = QGroupBox("Connection Settings")
        self.conn_group.setFont(QFont("Tahoma", 9, QFont.Bold))
        
        # Use vertical layout for small screens, horizontal for large
        self.conn_layout = QVBoxLayout()
        
        # First row: Host and Port
        host_row = QHBoxLayout()
        host_row.addWidget(QLabel("Host:"))
        
        self.host_input = QLineEdit("192.168.1.100")
        self.host_input.setPlaceholderText("ESP32 IP Address")
        self.host_input.setFont(QFont("Tahoma", 9))
        self.host_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        host_row.addWidget(self.host_input)
        
        host_row.addWidget(QLabel("Port:"))
        self.port_input = QLineEdit("8080")
        self.port_input.setPlaceholderText("Port")
        self.port_input.setFixedWidth(60)
        self.port_input.setFont(QFont("Tahoma", 9))
        host_row.addWidget(self.port_input)
        
        # Second row: Connect button and status
        control_row = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.setFont(QFont("Tahoma", 9, QFont.Bold))
        self.connect_button.clicked.connect(self.toggle_connection)
        self.connect_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        control_row.addWidget(self.connect_button)
        
        self.status_label = QLabel("Disconnected")
        self.status_label.setFont(QFont("Tahoma", 9))
        control_row.addWidget(self.status_label)
        control_row.addStretch()
        
        self.conn_layout.addLayout(host_row)
        self.conn_layout.addLayout(control_row)
        self.conn_group.setLayout(self.conn_layout)
        self.main_layout.addWidget(self.conn_group)
    
    def setup_main_content(self):
        """Setup main content with responsive splitter"""
        self.splitter = QSplitter(Qt.Vertical)
        
        # Lights control area
        self.lights_widget = QWidget()
        self.lights_layout = QVBoxLayout()
        self.lights_layout.setSpacing(10)
        
        # Global controls (responsive)
        self.setup_global_controls()
        
        # Individual light controls (responsive grid)
        self.setup_light_controls()
        
        self.lights_widget.setLayout(self.lights_layout)
        
        # Console area
        self.setup_console()
        
        # Add to splitter
        self.splitter.addWidget(self.lights_widget)
        self.splitter.addWidget(self.console_group)
        self.splitter.setSizes([400, 150])
        
        self.main_layout.addWidget(self.splitter)
    
    def setup_global_controls(self):
        """Setup responsive global controls"""
        self.global_group = QGroupBox("Global Controls")
        self.global_group.setFont(QFont("Tahoma", 9, QFont.Bold))
        
        # Use flow layout for buttons
        self.global_layout = QVBoxLayout()
        
        # First row of buttons
        button_row1 = QHBoxLayout()
        self.all_on_button = QPushButton("All Lights ON")
        self.all_off_button = QPushButton("All Lights OFF")
        
        for btn in [self.all_on_button, self.all_off_button]:
            btn.setFont(QFont("Tahoma", 9))
            btn.setMinimumHeight(30)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        button_row1.addWidget(self.all_on_button)
        button_row1.addWidget(self.all_off_button)
        
        # Second row of controls
        control_row = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh Status")
        self.refresh_button.setFont(QFont("Tahoma", 9))
        self.refresh_button.setMinimumHeight(30)
        self.refresh_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.auto_refresh_cb = QCheckBox("Auto Refresh (5s)")
        self.auto_refresh_cb.setFont(QFont("Tahoma", 9))
        
        control_row.addWidget(self.refresh_button)
        control_row.addWidget(self.auto_refresh_cb)
        control_row.addStretch()
        
        # Connect signals
        self.all_on_button.clicked.connect(lambda: self.send_command("ALL_ON"))
        self.all_off_button.clicked.connect(lambda: self.send_command("ALL_OFF"))
        self.refresh_button.clicked.connect(self.refresh_status)
        self.auto_refresh_cb.toggled.connect(self.toggle_auto_refresh)
        
        self.global_layout.addLayout(button_row1)
        self.global_layout.addLayout(control_row)
        self.global_group.setLayout(self.global_layout)
        self.lights_layout.addWidget(self.global_group)
    
    def setup_light_controls(self):
        """Setup responsive light controls grid"""
        self.lights_group = QGroupBox("Light Controls")
        self.lights_group.setFont(QFont("Tahoma", 9, QFont.Bold))
        
        # Container for responsive grid
        self.lights_container = QWidget()
        self.lights_grid = QGridLayout(self.lights_container)
        self.lights_grid.setSpacing(8)
        
        # Create light control widgets
        self.lights_config = [
            ("builtin", "Built-in LED"),
            ("light1", "Light 1"),
            ("light2", "Light 2"),
            ("light3", "Light 3"),
            ("light4", "Light 4")
        ]
        
        for light_name, display_name in self.lights_config:
            widget = ResponsiveLightWidget(light_name, display_name, self)
            self.light_widgets[light_name] = widget
        
        # Initial layout
        self.update_light_grid()
        
        # Scroll area for lights if needed
        lights_scroll = QScrollArea()
        lights_scroll.setWidget(self.lights_container)
        lights_scroll.setWidgetResizable(True)
        lights_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        lights_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        lights_scroll.setMaximumHeight(300)
        
        lights_group_layout = QVBoxLayout()
        lights_group_layout.addWidget(lights_scroll)
        self.lights_group.setLayout(lights_group_layout)
        
        self.lights_layout.addWidget(self.lights_group)
    
    def setup_console(self):
        """Setup responsive console"""
        self.console_group = QGroupBox("Console Output")
        self.console_group.setFont(QFont("Tahoma", 9, QFont.Bold))
        console_layout = QVBoxLayout()
        
        self.console = QTextEdit()
        self.console.setFont(QFont("Consolas", 9))
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(100)
        
        console_layout.addWidget(self.console)
        self.console_group.setLayout(console_layout)
    
    def update_light_grid(self):
        """Update light grid based on current window width"""
        # Clear existing layout
        for i in reversed(range(self.lights_grid.count())):
            item = self.lights_grid.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    self.lights_grid.removeWidget(widget)
        
        # Calculate optimal columns
        available_width = self.lights_container.width() - 40
        widget_width = 140 if not self.is_compact_mode else 120
        cols = max(1, available_width // (widget_width + 10))
        
        # Determine if we should use compact mode
        should_be_compact = cols > len(self.light_widgets) or available_width < 600
        
        if should_be_compact != self.is_compact_mode:
            self.is_compact_mode = should_be_compact
            for widget in self.light_widgets.values():
                widget.set_compact_mode(self.is_compact_mode)
        
        # Add widgets to grid
        for i, (light_name, _) in enumerate(self.lights_config):
            if light_name in self.light_widgets:
                row = i // cols
                col = i % cols
                self.lights_grid.addWidget(self.light_widgets[light_name], row, col)
        
        # Add stretch to fill remaining space
        self.lights_grid.setRowStretch(self.lights_grid.rowCount(), 1)
        self.lights_grid.setColumnStretch(cols, 1)
    
    def resizeEvent(self, event: QResizeEvent):
        """Handle window resize events"""
        super().resizeEvent(event)
        
        # Debounce resize events
        self.resize_timer.start(100)
        
        # Update status bar with current size
        size = event.size()
        self.statusBar().showMessage(f"Window: {size.width()}x{size.height()} - "
                                   f"Mode: {'Compact' if self.is_compact_mode else 'Normal'}")
    
    def handle_resize_complete(self):
        """Handle resize completion (debounced)"""
        self.update_light_grid()
        
        # Adjust splitter orientation for very narrow windows
        if self.width() < 500:
            if self.splitter.orientation() == Qt.Vertical:
                self.splitter.setOrientation(Qt.Horizontal)
        else:
            if self.splitter.orientation() == Qt.Horizontal:
                self.splitter.setOrientation(Qt.Vertical)
    
    def apply_responsive_theme(self):
        """Apply responsive XP theme styling"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
                font-family: Tahoma;
            }
            
            QScrollArea {
                border: none;
                background-color: #f0f0f0;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px groove #d4d0c8;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 8px;
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
                min-width: 50px;
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
                padding: 4px 6px;
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
            
            QSplitter::handle {
                background-color: #d4d0c8;
                border: 1px solid #a0a0a0;
            }
            
            QSplitter::handle:horizontal {
                width: 3px;
            }
            
            QSplitter::handle:vertical {
                height: 3px;
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
    app.setApplicationName("ESP32 Light Controller - Responsive")
    app.setApplicationVersion("2.0")
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
    window = ResponsiveMainWindow()
    window.show()
    
    # Center window on screen
    screen = app.desktop().screenGeometry()
    size = window.geometry()
    window.move((screen.width() - size.width()) // 2,
                (screen.height() - size.height()) // 2)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
