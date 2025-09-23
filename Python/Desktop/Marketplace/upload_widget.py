import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QTextEdit,
    QFileDialog, QMessageBox, QProgressBar, QFrame,
    QComboBox, QGroupBox, QSizePolicy, QScrollArea, QSpacerItem
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent

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
        self.setObjectName("dropZone")
        self.init_ui()
        self._create_styles()
        self.apply_default_style()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        self.drop_icon = QLabel("📦")
        self.drop_icon.setAlignment(Qt.AlignCenter)
        self.drop_icon.setObjectName("dropIcon")
        font = QFont()
        font.setPointSize(36)
        self.drop_icon.setFont(font)

        self.drop_text = QLabel("Drag & Drop ZIP file here\nor click to browse")
        self.drop_text.setAlignment(Qt.AlignCenter)
        self.drop_text.setObjectName("dropText")
        self.drop_text.setWordWrap(True)

        self.file_label = QLabel("No file selected")
        self.file_label.setAlignment(Qt.AlignCenter)
        self.file_label.setObjectName("fileLabel")

        layout.addWidget(self.drop_icon)
        layout.addWidget(self.drop_text)
        layout.addWidget(self.file_label)

        self.setLayout(layout)
        # allow the drop zone to expand horizontally
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumHeight(140)

    def _create_styles(self):
        # default and active styles for easy switching
        base = """
            #dropZone {
                border: 2px dashed #2b2b2b;
                border-radius: 8px;
                background-color: #111111;
            }
            #dropIcon { font-size: 48px; }
            #dropText {
                color: #a9abb0;
                font-size: 13px;
                line-height: 1.3;
            }
            #fileLabel {
                color: #FFB238;
                font-size: 12px;
                font-weight: bold;
            }
        """
        active = """
            #dropZone {
                border: 2px dashed #FFB238;
                border-radius: 8px;
                background-color: #151515;
            }
            #dropIcon { font-size: 48px; }
            #dropText {
                color: #a9abb0;
                font-size: 13px;
                line-height: 1.3;
            }
            #fileLabel {
                color: #FFB238;
                font-size: 12px;
                font-weight: bold;
            }
        """
        self._default_style = base
        self._active_style = active

    def apply_default_style(self):
        self.setStyleSheet(self._default_style)

    def apply_active_style(self):
        self.setStyleSheet(self._active_style)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) >= 1 and urls[0].toLocalFile().lower().endswith('.zip'):
                event.acceptProposedAction()
                self.apply_active_style()
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.apply_default_style()

    def dropEvent(self, event: QDropEvent):
        self.apply_default_style()
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith('.zip'):
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
        # Set more reasonable minimum and default sizes
        self.setMinimumSize(480, 400)  # Reduced minimum size
        self.resize(600, 580)  # More compact default size

        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)  # Remove spacing as the scroll area will handle it
        main_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins as the scroll area will handle it

        # Put everything into a scroll area so small screens can scroll
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(12)  # Reduced spacing
        content_layout.setContentsMargins(16, 16, 16, 16)  # Add padding inside scroll area

        # Header
        header = QLabel("UPLOAD MAKRO")
        header.setAlignment(Qt.AlignCenter)
        header.setObjectName("header")
        header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        content_layout.addWidget(header)

        # File selection group
        file_group = QGroupBox("Select File")
        file_group.setObjectName("fileGroup")
        file_layout = QVBoxLayout()
        file_layout.setContentsMargins(8, 8, 8, 8)

        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self.file_selected)
        file_layout.addWidget(self.drop_zone)

        file_group.setLayout(file_layout)
        file_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        content_layout.addWidget(file_group)

        # Makro details group
        details_group = QGroupBox("Makro Details")
        details_group.setObjectName("detailsGroup")
        details_layout = QVBoxLayout()
        details_layout.setSpacing(8)  # Slightly reduced spacing
        details_layout.setContentsMargins(12, 12, 12, 12)  # Slightly increased margins for better spacing

        # Name field
        name_label = QLabel("Name *")
        name_label.setObjectName("fieldLabel")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter makro name...")
        self.name_input.setObjectName("inputField")
        self.name_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Description field
        desc_label = QLabel("Description")
        desc_label.setObjectName("fieldLabel")
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Enter makro description (optional)...")
        self.desc_input.setObjectName("textField")
        self.desc_input.setMinimumHeight(60)
        self.desc_input.setMaximumHeight(120)  # Reduced maximum height
        self.desc_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # Changed to Preferred

        # Use case field
        usecase_label = QLabel("Category")
        usecase_label.setObjectName("fieldLabel")
        self.usecase_combo = QComboBox()
        self.usecase_combo.setObjectName("comboField")
        self.usecase_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
        details_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_layout.addWidget(details_group)

        # Buttons row
        # Buttons container with proper spacing
        buttons_container = QFrame()
        buttons_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        buttons_container.setObjectName("buttonsContainer")
        
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(10)
        buttons_row.setContentsMargins(0, 0, 0, 0)

        self.upload_button = QPushButton("UPLOAD TO MARKETPLACE")
        self.upload_button.setObjectName("uploadButton")
        self.upload_button.clicked.connect(self.handle_upload)
        self.upload_button.setEnabled(False)
        self.upload_button.setFixedHeight(36)  # Fixed height for better appearance
        self.upload_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.clear_button = QPushButton("CLEAR FORM")
        self.clear_button.setObjectName("clearButton")
        self.clear_button.clicked.connect(self.clear_form)
        self.clear_button.setFixedHeight(36)  # Fixed height for better appearance
        self.clear_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.clear_button.setMinimumWidth(120)  # Set minimum width for clear button

        buttons_row.addWidget(self.upload_button)
        buttons_row.addWidget(self.clear_button)
        
        buttons_container.setLayout(buttons_row)
        content_layout.addWidget(buttons_container)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setVisible(False)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        content_layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Select a ZIP file to begin")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        content_layout.addWidget(self.status_label)

        # spacer to push content to top on tall windows
        content_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        content.setLayout(content_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Prevent horizontal scrolling
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)     # Show vertical scrollbar only when needed

        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def apply_styles(self):
        """Apply the orange/black color scheme"""
        # Note: objectNames used in stylesheet must match setObjectName calls above
        self.setStyleSheet("""
            QWidget {
                background-color: #0a0a0a;
                color: #f2f2f2;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            QScrollArea {
                border: none;
                background-color: #0a0a0a;
            }
            
            QScrollArea > QWidget > QWidget {
                background-color: #0a0a0a;
            }

            QLabel#header {
                font-size: 20px;
                font-weight: bold;
                color: #FFB238;
                margin: 4px 0;
            }

            QGroupBox#fileGroup, QGroupBox#detailsGroup {
                font-weight: bold;
                color: #a9abb0;
                border: 2px solid #2b2b2b;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 10px;
            }

            QGroupBox#fileGroup::title, QGroupBox#detailsGroup::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px;
                color: #FFB238;
                font-size: 13px;
            }
            
            #buttonsContainer {
                background-color: transparent;
                margin-top: 4px;
            }

            QLabel#fieldLabel {
                color: #a9abb0;
                font-weight: bold;
                font-size: 13px;
                margin-bottom: 4px;
            }

            QLineEdit#inputField {
                padding: 10px;
                border: 2px solid #2b2b2b;
                border-radius: 6px;
                background-color: #151515;
                color: #f2f2f2;
                font-size: 14px;
            }

            QLineEdit#inputField:focus {
                border-color: #FFB238;
                background-color: #111111;
            }

            QTextEdit#textField {
                padding: 10px;
                border: 2px solid #2b2b2b;
                border-radius: 6px;
                background-color: #151515;
                color: #f2f2f2;
                font-size: 14px;
            }

            QTextEdit#textField:focus {
                border-color: #FFB238;
                background-color: #111111;
            }

            QComboBox#comboField {
                padding: 10px;
                border: 2px solid #2b2b2b;
                border-radius: 6px;
                background-color: #151515;
                color: #f2f2f2;
                font-size: 14px;
            }

            QComboBox#comboField:focus {
                border-color: #FFB238;
            }

            QComboBox#comboField QAbstractItemView {
                background-color: #151515;
                border: 1px solid #2b2b2b;
                selection-background-color: #FFB238;
                selection-color: #0a0a0a;
            }

            QPushButton#uploadButton {
                background-color: #FFB238;
                color: #0a0a0a;
                border: none;
                padding: 12px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }

            QPushButton#uploadButton:hover {
                background-color: #ffc24d;
            }

            QPushButton#uploadButton:pressed {
                background-color: #e5a831;
            }

            QPushButton#uploadButton:disabled {
                background-color: #2b2b2b;
                color: #555555;
            }

            QPushButton#clearButton {
                background-color: #2b2b2b;
                color: #a9abb0;
                border: 1px solid #555555;
                padding: 10px;
                border-radius: 6px;
                font-size: 13px;
            }

            QPushButton#clearButton:hover {
                background-color: #555555;
                color: #f2f2f2;
            }

            QProgressBar#progressBar {
                border: 2px solid #2b2b2b;
                border-radius: 4px;
                text-align: center;
                background-color: #151515;
            }

            QProgressBar#progressBar::chunk {
                background-color: #FFB238;
                border-radius: 2px;
            }

            QLabel#statusLabel {
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

        try:
            file_size = Path(file_path).stat().st_size
            size_mb = file_size / (1024 * 1024)
            self.status_label.setText(f"File selected: {Path(file_path).name} ({size_mb:.1f} MB)")
        except Exception:
            self.status_label.setText(f"File selected: {Path(file_path).name}")

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
