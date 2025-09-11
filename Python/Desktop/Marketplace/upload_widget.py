import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                              QLineEdit, QPushButton, QLabel, QTextEdit,
                              QFileDialog, QMessageBox, QProgressBar, QFrame,
                              QComboBox, QGroupBox)
from PySide6.QtCore import Qt,  QThread, Signal
from PySide6.QtGui import QFont, QPalette, QColor, QDragEnterEvent, QDropEvent

# Import your API client
# from makros_api_client import MakrosAPIClient


class UploadThread(QThread):
    """Thread for uploading makros"""
    progress = Signal(int)
    finished = Signal(str)  # Success message
    error = Signal(str)
    
    def __init__(self, api_client, file_path: str, name: str, desc: str = None, usecase: str = None):
        super().__init__()
        self.api_client = api_client
        self.file_path = file_path
        self.name = name
        self.desc = desc
        self.usecase = usecase
    
    def run(self):
        try:
            if not self.api_client:
                # Simulate upload for testing
                import time
                for i in range(101):
                    time.sleep(0.02)
                    self.progress.emit(i)
                self.finished.emit(f"Successfully uploaded '{self.name}' to marketplace")
                return
            
            # Real upload
            result = self.api_client.upload_makro(
                file_path=self.file_path,
                name=self.name,
                desc=self.desc,
                usecase=self.usecase
            )
            
            makro_name = result.get('makro', {}).get('name', self.name)
            self.finished.emit(f"Successfully uploaded '{makro_name}' to marketplace")
            
        except Exception as e:
            self.error.emit(f"Upload failed: {str(e)}")


class DropZone(QFrame):
    """Drag and drop file zone"""
    file_dropped = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.init_ui()
        self.apply_styles()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)
        
        self.drop_icon = QLabel("📦")
        self.drop_icon.setAlignment(Qt.AlignCenter)
        self.drop_icon.setObjectName("dropIcon")
        
        self.drop_text = QLabel("Drag & Drop ZIP file here\nor click to browse")
        self.drop_text.setAlignment(Qt.AlignCenter)
        self.drop_text.setObjectName("dropText")
        
        self.file_label = QLabel("No file selected")
        self.file_label.setAlignment(Qt.AlignCenter)
        self.file_label.setObjectName("fileLabel")
        
        layout.addWidget(self.drop_icon)
        layout.addWidget(self.drop_text)
        layout.addWidget(self.file_label)
        
        self.setLayout(layout)
        self.setMinimumHeight(150)
    
    def apply_styles(self):
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #2b2b2b;
                border-radius: 8px;
                background-color: #111111;
            }
            
            DropZone:hover {
                border-color: #FFB238;
                background-color: #151515;
            }
            
            #dropIcon {
                font-size: 48px;
            }
            
            #dropText {
                color: #a9abb0;
                font-size: 14px;
                line-height: 1.4;
            }
            
            #fileLabel {
                color: #FFB238;
                font-size: 12px;
                font-weight: bold;
            }
        """)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].toLocalFile().endswith('.zip'):
                event.acceptProposedAction()
                self.setStyleSheet(self.styleSheet().replace('#2b2b2b', '#FFB238'))
    
    def dragLeaveEvent(self, event):
        self.apply_styles()
    
    def dropEvent(self, event: QDropEvent):
        self.apply_styles()
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.endswith('.zip'):
                self.set_file(file_path)
                self.file_dropped.emit(file_path)
            else:
                QMessageBox.warning(self, "Invalid File", "Please select a ZIP file.")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.browse_file()
    
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Makro ZIP File",
            str(Path.home()),
            "ZIP Files (*.zip)"
        )
        
        if file_path:
            self.set_file(file_path)
            self.file_dropped.emit(file_path)
    
    def set_file(self, file_path: str):
        """Set the selected file"""
        filename = Path(file_path).name
        self.file_label.setText(f"Selected: {filename}")
        self.drop_text.setText("File selected! Ready to upload.")


class UploadWidget(QWidget):
    """Widget for uploading makros to the marketplace"""
    upload_successful = Signal(dict)  # Emits makro data on successful upload
    
    def __init__(self, api_client=None, parent=None):
        super().__init__(parent)
        # self.api_client = api_client or MakrosAPIClient()
        self.api_client = api_client  # For testing without API
        self.selected_file = None
        
        self.setWindowTitle("Upload Makro")
        self.setFixedSize(500, 650)
        self.init_ui()
        self.apply_styles()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header = QLabel("UPLOAD MAKRO")
        header.setAlignment(Qt.AlignCenter)
        header.setObjectName("header")
        layout.addWidget(header)
        
        # File selection group
        file_group = QGroupBox("Select File")
        file_group.setObjectName("groupBox")
        file_layout = QVBoxLayout()
        
        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self.file_selected)
        file_layout.addWidget(self.drop_zone)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Makro details group
        details_group = QGroupBox("Makro Details")
        details_group.setObjectName("groupBox")
        details_layout = QVBoxLayout()
        details_layout.setSpacing(15)
        
        # Name field
        name_label = QLabel("Name *")
        name_label.setObjectName("fieldLabel")
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter makro name...")
        self.name_input.setObjectName("inputField")
        
        # Description field
        desc_label = QLabel("Description")
        desc_label.setObjectName("fieldLabel")
        
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Enter makro description (optional)...")
        self.desc_input.setObjectName("textField")
        self.desc_input.setMaximumHeight(80)
        
        # Use case field
        usecase_label = QLabel("Category")
        usecase_label.setObjectName("fieldLabel")
        
        self.usecase_combo = QComboBox()
        self.usecase_combo.setObjectName("comboField")
        self.usecase_combo.addItems([
            "Productivity",
            "Development", 
            "Gaming",
            "Testing",
            "Automation",
            "Utility",
            "Other"
        ])
        
        details_layout.addWidget(name_label)
        details_layout.addWidget(self.name_input)
        details_layout.addWidget(desc_label)
        details_layout.addWidget(self.desc_input)
        details_layout.addWidget(usecase_label)
        details_layout.addWidget(self.usecase_combo)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Upload button
        self.upload_button = QPushButton("UPLOAD TO MARKETPLACE")
        self.upload_button.setObjectName("uploadButton")
        self.upload_button.clicked.connect(self.handle_upload)
        self.upload_button.setEnabled(False)
        layout.addWidget(self.upload_button)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Select a ZIP file to begin")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Clear button
        self.clear_button = QPushButton("CLEAR FORM")
        self.clear_button.setObjectName("clearButton")
        self.clear_button.clicked.connect(self.clear_form)
        layout.addWidget(self.clear_button)
        
        self.setLayout(layout)
    
    def apply_styles(self):
        """Apply the orange/black color scheme"""
        self.setStyleSheet("""
            QWidget {
                background-color: #0a0a0a;
                color: #f2f2f2;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            #header {
                font-size: 24px;
                font-weight: bold;
                color: #FFB238;
                margin-bottom: 10px;
            }
            
            #groupBox {
                font-weight: bold;
                color: #a9abb0;
                border: 2px solid #2b2b2b;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            
            #groupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #FFB238;
            }
            
            #fieldLabel {
                color: #a9abb0;
                font-weight: bold;
                font-size: 14px;
            }
            
            #inputField {
                padding: 12px;
                border: 2px solid #2b2b2b;
                border-radius: 6px;
                background-color: #151515;
                color: #f2f2f2;
                font-size: 14px;
            }
            
            #inputField:focus {
                border-color: #FFB238;
                background-color: #111111;
            }
            
            #textField {
                padding: 12px;
                border: 2px solid #2b2b2b;
                border-radius: 6px;
                background-color: #151515;
                color: #f2f2f2;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            #textField:focus {
                border-color: #FFB238;
                background-color: #111111;
            }
            
            #comboField {
                padding: 12px;
                border: 2px solid #2b2b2b;
                border-radius: 6px;
                background-color: #151515;
                color: #f2f2f2;
                font-size: 14px;
            }
            
            #comboField:focus {
                border-color: #FFB238;
            }
            
            #comboField QAbstractItemView {
                background-color: #151515;
                border: 1px solid #2b2b2b;
                selection-background-color: #FFB238;
                selection-color: #0a0a0a;
            }
            
            #uploadButton {
                background-color: #FFB238;
                color: #0a0a0a;
                border: none;
                padding: 15px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            
            #uploadButton:hover {
                background-color: #ffc24d;
            }
            
            #uploadButton:pressed {
                background-color: #e5a831;
            }
            
            #uploadButton:disabled {
                background-color: #2b2b2b;
                color: #555555;
            }
            
            #clearButton {
                background-color: #2b2b2b;
                color: #a9abb0;
                border: 1px solid #555555;
                padding: 10px;
                border-radius: 6px;
                font-size: 14px;
            }
            
            #clearButton:hover {
                background-color: #555555;
                color: #f2f2f2;
            }
            
            #progressBar {
                border: 2px solid #2b2b2b;
                border-radius: 4px;
                text-align: center;
                background-color: #151515;
            }
            
            #progressBar::chunk {
                background-color: #FFB238;
                border-radius: 2px;
            }
            
            #statusLabel {
                color: #9ea0a4;
                font-size: 12px;
            }
        """)
    
    def file_selected(self, file_path: str):
        """Handle file selection"""
        self.selected_file = file_path
        self.upload_button.setEnabled(True)
        
        # Auto-fill name from filename if empty
        if not self.name_input.text():
            filename = Path(file_path).stem
            # Clean up filename for display
            clean_name = filename.replace('_', ' ').replace('-', ' ').title()
            self.name_input.setText(clean_name)
        
        file_size = Path(file_path).stat().st_size
        size_mb = file_size / (1024 * 1024)
        self.status_label.setText(f"File selected: {Path(file_path).name} ({size_mb:.1f} MB)")
    
    def handle_upload(self):
        """Handle upload button click"""
        if not self.selected_file:
            QMessageBox.warning(self, "No File Selected", "Please select a ZIP file to upload.")
            return
        
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Information", "Please enter a name for the makro.")
            self.name_input.setFocus()
            return
        
        desc = self.desc_input.toPlainText().strip() or None
        usecase = self.usecase_combo.currentText()
        
        # Validate file exists and is accessible
        if not Path(self.selected_file).exists():
            QMessageBox.critical(self, "File Error", "The selected file no longer exists.")
            return
        
        # Start upload
        self.upload_thread = UploadThread(
            self.api_client,
            self.selected_file,
            name,
            desc,
            usecase
        )
        
        self.upload_thread.progress.connect(self.update_progress)
        self.upload_thread.finished.connect(self.upload_finished)
        self.upload_thread.error.connect(self.upload_error)
        
        # Update UI for upload state
        self.upload_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Uploading {name}...")
        
        self.upload_thread.start()
    
    def update_progress(self, value: int):
        """Update upload progress"""
        self.progress_bar.setValue(value)
    
    def upload_finished(self, message: str):
        """Handle upload completion"""
        self.progress_bar.setVisible(False)
        self.upload_button.setEnabled(True)
        self.status_label.setText(message)
        
        QMessageBox.information(self, "Upload Successful", message)
        
        # Emit success signal with makro data
        makro_data = {
            'name': self.name_input.text(),
            'desc': self.desc_input.toPlainText(),
            'usecase': self.usecase_combo.currentText()
        }
        self.upload_successful.emit(makro_data)
        
        # Ask if user wants to upload another
        reply = QMessageBox.question(
            self,
            "Upload Another?",
            "Would you like to upload another makro?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.clear_form()
        else:
            self.close()
    
    def upload_error(self, error_msg: str):
        """Handle upload error"""
        self.progress_bar.setVisible(False)
        self.upload_button.setEnabled(True)
        self.status_label.setText(f"Upload failed: {error_msg}")
        
        QMessageBox.critical(self, "Upload Error", error_msg)
    
    def clear_form(self):
        """Clear all form fields"""
        self.selected_file = None
        self.name_input.clear()
        self.desc_input.clear()
        self.usecase_combo.setCurrentIndex(0)
        self.upload_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        # Reset drop zone
        self.drop_zone.file_label.setText("No file selected")
        self.drop_zone.drop_text.setText("Drag & Drop ZIP file here\nor click to browse")
        
        self.status_label.setText("Select a ZIP file to begin")
    
    def closeEvent(self, event):
        """Handle window close event"""
        if hasattr(self, 'upload_thread') and self.upload_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Upload in Progress",
                "An upload is currently in progress. Are you sure you want to close?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
            
            self.upload_thread.terminate()
            self.upload_thread.wait()
        
        event.accept()


def main():
    """Test the upload widget"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    widget = UploadWidget()
    
    def on_upload_success(makro_data):
        print(f"Upload successful: {makro_data}")
    
    widget.upload_successful.connect(on_upload_success)
    widget.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()