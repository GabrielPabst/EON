import sys
import json
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QPushButton, QLabel, QStackedWidget,
                              QFrame, QMenuBar, QStatusBar)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QAction

# Import your widgets
from login_widget import LoginWidget
from marketplace_widget import MarketplaceWidget
from upload_widget import UploadWidget
from my_makros_widget import MyMakrosWidget

# Import your API client
from marketService import MakrosAPIClient


class NavigationBar(QFrame):
    """Custom navigation bar"""
    page_requested = Signal(str)
    logout_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user = None
        self.init_ui()
        self.apply_styles()
    
    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(15)
        
        # Logo/Title
        self.logo = QLabel("MAKROS")
        self.logo.setObjectName("logo")
        layout.addWidget(self.logo)
        
        layout.addStretch()
        
        # Navigation buttons
        self.marketplace_btn = QPushButton("MARKETPLACE")
        self.marketplace_btn.setObjectName("navButton")
        self.marketplace_btn.clicked.connect(lambda: self.page_requested.emit("marketplace"))
        
        self.upload_btn = QPushButton("UPLOAD")
        self.upload_btn.setObjectName("navButton")
        self.upload_btn.clicked.connect(lambda: self.page_requested.emit("upload"))
        
        self.my_makros_btn = QPushButton("MY MAKROS")
        self.my_makros_btn.setObjectName("navButton")
        self.my_makros_btn.clicked.connect(lambda: self.page_requested.emit("my_makros"))
        
        layout.addWidget(self.marketplace_btn)
        layout.addWidget(self.upload_btn)
        layout.addWidget(self.my_makros_btn)
        
        layout.addStretch()
        
        # User info and logout
        self.user_label = QLabel("Not logged in")
        self.user_label.setObjectName("userLabel")
        
        self.logout_btn = QPushButton("LOGOUT")
        self.logout_btn.setObjectName("logoutButton")
        self.logout_btn.clicked.connect(self.logout_requested.emit)
        self.logout_btn.setVisible(False)
        
        layout.addWidget(self.user_label)
        layout.addWidget(self.logout_btn)
        
        self.setLayout(layout)
    
    def apply_styles(self):
        self.setStyleSheet("""
            NavigationBar {
                background-color: #111111;
                border-bottom: 2px solid #2b2b2b;
            }
            
            #logo {
                font-size: 20px;
                font-weight: bold;
                color: #FFB238;
            }
            
            #navButton {
                background-color: #2b2b2b;
                color: #a9abb0;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
            }
            
            #navButton:hover {
                background-color: #FFB238;
                color: #0a0a0a;
            }
            
            #navButton:pressed, #navButton:checked {
                background-color: #e5a831;
                color: #0a0a0a;
            }
            
            #userLabel {
                color: #a9abb0;
                font-size: 12px;
                margin-right: 10px;
            }
            
            #logoutButton {
                background-color: #d63447;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            
            #logoutButton:hover {
                background-color: #c92a3d;
            }
        """)
    
    def set_user(self, user_data):
        """Set current user info"""
        self.current_user = user_data
        username = user_data.get('name', 'User')
        self.user_label.setText(f"Welcome, {username}")
        self.logout_btn.setVisible(True)
    
    def clear_user(self):
        """Clear user info"""
        self.current_user = None
        self.user_label.setText("Not logged in")
        self.logout_btn.setVisible(False)


class MakrosMainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.api_client = MakrosAPIClient()
        #self.api_client = None  # For testing without API
        self.current_user = None
        
        self.setWindowTitle("Makros Marketplace")
        self.setMinimumSize(1000, 700)
        self.init_ui()
        self.apply_styles()
    
    def init_ui(self):
        """Initialize the main UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Navigation bar
        self.nav_bar = NavigationBar()
        self.nav_bar.page_requested.connect(self.switch_page)
        self.nav_bar.logout_requested.connect(self.handle_logout)
        layout.addWidget(self.nav_bar)
        
        # Stacked widget for different pages
        self.stacked_widget = QStackedWidget()
        
        # Login widget
        self.login_widget = LoginWidget(self.api_client)
        self.login_widget.login_successful.connect(self.handle_login_success)
        
        # Main application widgets
        self.marketplace_widget = MarketplaceWidget(self.api_client)
        self.upload_widget = UploadWidget(self.api_client)
        self.upload_widget.upload_successful.connect(self.handle_upload_success)
        self.my_makros_widget = MyMakrosWidget(self.api_client)
        
        # Add widgets to stack
        self.stacked_widget.addWidget(self.login_widget)  # Index 0
        self.stacked_widget.addWidget(self.marketplace_widget)  # Index 1
        self.stacked_widget.addWidget(self.upload_widget)  # Index 2
        self.stacked_widget.addWidget(self.my_makros_widget)  # Index 3
        
        layout.addWidget(self.stacked_widget)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("statusBar")
        self.status_bar.showMessage("Ready")
        self.setStatusBar(self.status_bar)
        
        central_widget.setLayout(layout)
        
        # Start with login page
        self.show_login_page()
    
    def apply_styles(self):
        """Apply application-wide styles"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0a0a;
                color: #f2f2f2;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            #statusBar {
                background-color: #111111;
                color: #9ea0a4;
                border-top: 1px solid #2b2b2b;
                font-size: 12px;
            }
            
            #statusBar::item {
                border: none;
            }
        """)
    
    def show_login_page(self):
        """Show the login page"""
        self.stacked_widget.setCurrentIndex(0)
        self.nav_bar.setVisible(False)
        self.status_bar.showMessage("Please login to continue")
    
    def show_main_interface(self):
        """Show the main application interface"""
        self.nav_bar.setVisible(True)
        self.switch_page("marketplace")  # Default to marketplace
        self.status_bar.showMessage("Ready")
    
    def switch_page(self, page_name: str):
        """Switch to a specific page"""
        if not self.current_user and page_name != "login":
            self.show_login_page()
            return
        
        page_mapping = {
            "marketplace": 1,
            "upload": 2,
            "my_makros": 3
        }
        
        if page_name in page_mapping:
            self.stacked_widget.setCurrentIndex(page_mapping[page_name])
            
            # Update status bar
            status_messages = {
                "marketplace": "Browsing marketplace",
                "upload": "Upload a new makro",
                "my_makros": "Managing your makros"
            }
            self.status_bar.showMessage(status_messages.get(page_name, "Ready"))
    
    def handle_login_success(self, user_data):
        """Handle successful login"""
        self.current_user = user_data
        self.nav_bar.set_user(user_data)
        self.show_main_interface()
        
        username = user_data.get('name', 'User')
        self.status_bar.showMessage(f"Welcome, {username}!")
        
        # Refresh widgets that need user data
        if hasattr(self.marketplace_widget, 'load_makros'):
            self.marketplace_widget.load_makros()
        if hasattr(self.my_makros_widget, 'load_my_makros'):
            self.my_makros_widget.load_my_makros()
    
    def handle_logout(self):
        """Handle logout request"""
        # Clear session
        self.login_widget.logout()
        
        # Reset state
        self.current_user = None
        self.nav_bar.clear_user()
        
        # Show login page
        self.show_login_page()
    
    def handle_upload_success(self, makro_data):
        """Handle successful upload"""
        self.status_bar.showMessage(f"Successfully uploaded '{makro_data.get('name')}'")
        
        # Refresh marketplace and my makros
        if hasattr(self.marketplace_widget, 'load_makros'):
            self.marketplace_widget.load_makros()
        if hasattr(self.my_makros_widget, 'load_my_makros'):
            self.my_makros_widget.load_my_makros()
    
    def closeEvent(self, event):
        """Handle application close"""
        # Clean up any ongoing operations
        if hasattr(self.upload_widget, 'upload_thread') and self.upload_widget.upload_thread.isRunning():
            self.upload_widget.upload_thread.terminate()
            self.upload_widget.upload_thread.wait()
        
        # Clear session file
        session_file = Path("session.json")
        session_file.unlink(missing_ok=True)
        
        event.accept()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Makros Marketplace")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Makros")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MakrosMainWindow()
    window.show()
    
    # Handle application exit
    sys.exit(app.exec())


if __name__ == "__main__":
    main()