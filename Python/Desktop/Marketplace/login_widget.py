import sys
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                              QLineEdit, QPushButton, QLabel, QTabWidget, 
                              QMessageBox, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPalette, QColor

# Import your API client
from marketService import MakrosAPIClient


class LoginWidget(QWidget):
    """
    Login and registration widget with orange/black aesthetic
    """
    login_successful = Signal(dict)  # Emits user data on successful login
    
    def __init__(self, api_client=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client or MakrosAPIClient()
        #self.api_client = api_client  # For testing without API
        self.session_file = Path("session.json")
        
        self.setWindowTitle("Makros - Login")
        self.setMinimumSize(600, 500)  # Increased size for better visibility
        self.init_ui()
        self.apply_styles()
        
        # Check for existing session
        self.check_existing_session()
    
    def init_ui(self):
        """Initialize the user interface"""
        # Create a main container widget with dark background
        container = QWidget()
        container.setObjectName("loginContainer")
        
        # Main layout for the widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)
        
        # Container layout
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Center area for content
        center_widget = QWidget()
        center_widget.setObjectName("centerWidget")
        center_layout = QVBoxLayout(center_widget)
        center_layout.setSpacing(20)
        
        # Title
        title = QLabel("MAKROS")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("title")
        center_layout.addWidget(title)
        
        # Tab widget for Login/Register
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("tabWidget")
        
        # Login tab
        login_tab = QWidget()
        login_layout = QVBoxLayout()
        login_layout.setSpacing(15)
        
        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Username")
        self.login_username.setObjectName("inputField")
        
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Password")
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_password.setObjectName("inputField")
        
        self.login_button = QPushButton("LOGIN")
        self.login_button.setObjectName("primaryButton")
        self.login_button.clicked.connect(self.handle_login)
        
        login_layout.addWidget(self.login_username)
        login_layout.addWidget(self.login_password)
        login_layout.addWidget(self.login_button)
        login_layout.addStretch()
        
        login_tab.setLayout(login_layout)
        self.tab_widget.addTab(login_tab, "Login")
        
        # Register tab
        register_tab = QWidget()
        register_layout = QVBoxLayout()
        register_layout.setSpacing(15)
        
        self.register_username = QLineEdit()
        self.register_username.setPlaceholderText("Username")
        self.register_username.setObjectName("inputField")
        
        self.register_password = QLineEdit()
        self.register_password.setPlaceholderText("Password")
        self.register_password.setEchoMode(QLineEdit.Password)
        self.register_password.setObjectName("inputField")
        
        self.register_confirm = QLineEdit()
        self.register_confirm.setPlaceholderText("Confirm Password")
        self.register_confirm.setEchoMode(QLineEdit.Password)
        self.register_confirm.setObjectName("inputField")
        
        self.register_button = QPushButton("REGISTER")
        self.register_button.setObjectName("primaryButton")
        self.register_button.clicked.connect(self.handle_register)
        
        register_layout.addWidget(self.register_username)
        register_layout.addWidget(self.register_password)
        register_layout.addWidget(self.register_confirm)
        register_layout.addWidget(self.register_button)
        register_layout.addStretch()
        
        register_tab.setLayout(register_layout)
        self.tab_widget.addTab(register_tab, "Register")
        
        center_layout.addWidget(self.tab_widget)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("statusLabel")
        center_layout.addWidget(self.status_label)
        
        # Add the center widget to the main layout with stretches for centering
        layout.addStretch(1)
        layout.addWidget(center_widget)
        layout.addStretch(1)
    
    def apply_styles(self):
        """Apply the orange/black color scheme"""
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                color: #f2f2f2;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            #loginContainer {
                background-color: #0a0a0a;
            }
            
            #centerWidget {
                background-color: #111111;
                border-radius: 12px;
                max-width: 400px;
                padding: 20px;
            }
            
            #title {
                font-size: 32px;
                font-weight: bold;
                color: #FFB238;
                margin-bottom: 20px;
                letter-spacing: 2px;
            }
            
            #tabWidget {
                background-color: transparent;
            }
            
            #tabWidget::pane {
                border: none;
                background-color: transparent;
            }
            
            #tabWidget::tab-bar {
                alignment: center;
            }
            
            QTabBar::tab {
                background-color: #2b2b2b;
                color: #a9abb0;
                padding: 12px 30px;
                margin: 2px;
                border-radius: 6px;
                font-size: 14px;
            }
            
            QTabBar::tab:selected {
                background-color: #FFB238;
                color: #0a0a0a;
                font-weight: bold;
            }
            
            QTabBar::tab:hover {
                background-color: #ffc24d;
                color: #0a0a0a;
            }
            
            #inputField {
                padding: 14px;
                border: 2px solid #2b2b2b;
                border-radius: 8px;
                background-color: #1a1a1a;
                color: #ffffff;
                font-size: 14px;
                margin-bottom: 5px;
            }
            
            #inputField:focus {
                border-color: #FFB238;
                background-color: #202020;
                color: #ffffff;
            }
            
            #inputField::placeholder {
                color: #666666;
            }
            
            #primaryButton {
                background-color: #FFB238;
                color: #0a0a0a;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            
            #primaryButton:hover {
                background-color: #ffc24d;
            }
            
            #primaryButton:pressed {
                background-color: #e5a831;
            }
            
            #statusLabel {
                color: #9ea0a4;
                font-size: 12px;
            }
        """)
    
    def handle_login(self):
        """Handle login button click"""
        username = self.login_username.text().strip()
        password = self.login_password.text().strip()
        
        if not username or not password:
            self.show_message("Please fill in all fields", "error")
            return
        
        try:
            # For testing without API
            if not self.api_client:
                # Simulate successful login
                user_data = {"id": 1, "name": username}
                self.save_session(user_data)
                self.login_successful.emit(user_data)
                self.show_message("Login successful!", "success")
                return
            
            # Real API call
            result = self.api_client.login(username, password)
            user_data = result.get('account', {})
            
            self.save_session(user_data)
            self.login_successful.emit(user_data)
            self.show_message("Login successful!", "success")
            
        except Exception as e:
            self.show_message(f"Login failed: {str(e)}", "error")
    
    def handle_register(self):
        """Handle register button click"""
        username = self.register_username.text().strip()
        password = self.register_password.text().strip()
        confirm = self.register_confirm.text().strip()
        
        if not username or not password or not confirm:
            self.show_message("Please fill in all fields", "error")
            return
        
        if password != confirm:
            self.show_message("Passwords do not match", "error")
            return
        
        if len(password) < 6:
            self.show_message("Password must be at least 6 characters", "error")
            return
        
        try:
            # For testing without API
            if not self.api_client:
                self.show_message("Registration successful! Please login.", "success")
                self.switch_tab("login")  # Switch to login tab
                return
            
            # Real API call
            result = self.api_client.register(username, password)
            self.show_message("Registration successful! Please login.", "success")
            self.tab_widget.setCurrentIndex(0)  # Switch to login tab
            
        except Exception as e:
            self.show_message(f"Registration failed: {str(e)}", "error")
    
    def save_session(self, user_data: Dict[str, Any]):
        """Save user session to temporary file"""
        try:
            with open(self.session_file, 'w') as f:
                json.dump(user_data, f)
        except Exception as e:
            print(f"Failed to save session: {e}")
    
    def check_existing_session(self):
        """Check if there's an existing session"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    user_data = json.load(f)
                    self.login_successful.emit(user_data)
                    self.show_message(f"Welcome back, {user_data.get('name', 'User')}!", "success")
            except Exception as e:
                # Remove corrupted session file
                self.session_file.unlink(missing_ok=True)
    
    def logout(self):
        """Logout and clear session"""
        try:
            if self.api_client:
                self.api_client.logout()
        except:
            pass
        
        self.session_file.unlink(missing_ok=True)
        self.status_label.setText("Logged out successfully")
        
        # Clear input fields
        self.login_username.clear()
        self.login_password.clear()
        self.register_username.clear()
        self.register_password.clear()
        self.register_confirm.clear()
    
    def show_message(self, message: str, msg_type: str = "info"):
        """Show status message"""
        if msg_type == "error":
            self.status_label.setStyleSheet("color: #ff6b6b;")
        elif msg_type == "success":
            self.status_label.setStyleSheet("color: #51cf66;")
        else:
            self.status_label.setStyleSheet("color: #9ea0a4;")
        
        self.status_label.setText(message)


def main():
    """Test the login widget"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    widget = LoginWidget()
    
    def on_login_success(user_data):
        print(f"Login successful: {user_data}")
        # In a real app, you would switch to the main interface here
    
    widget.login_successful.connect(on_login_success)
    widget.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()