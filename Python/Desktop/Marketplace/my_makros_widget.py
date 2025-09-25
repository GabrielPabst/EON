import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                              QLineEdit, QPushButton, QLabel, QScrollArea,
                              QFrame, QComboBox, QMessageBox, QDialog,
                              QTextEdit, QDialogButtonBox, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPalette, QColor

# Import your API client
from marketService import MakrosAPIClient


class MakroConfigDialog(QDialog):
    """Dialog for configuring makro details"""
    
    def __init__(self, makro_data: Dict[str, Any], api_client=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.makro_data = makro_data
        self.makro_id = makro_data.get('id')
        
        self.setWindowTitle(f"Configure - {makro_data.get('name', 'Makro')}")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        
        self.init_ui()
        self.apply_styles()
        self.load_data()
    
    def init_ui(self):
        """Initialize the dialog UI"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header = QLabel(f"Configure Makro")
        header.setObjectName("dialogHeader")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Form fields
        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)
        
        # Name field
        name_label = QLabel("Name")
        name_label.setObjectName("fieldLabel")
        
        self.name_input = QLineEdit()
        self.name_input.setObjectName("inputField")
        
        # Description field
        desc_label = QLabel("Description")
        desc_label.setObjectName("fieldLabel")
        
        self.desc_input = QTextEdit()
        self.desc_input.setObjectName("textField")
        self.desc_input.setMaximumHeight(100)
        
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
        
        form_layout.addWidget(name_label)
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(desc_label)
        form_layout.addWidget(self.desc_input)
        form_layout.addWidget(usecase_label)
        form_layout.addWidget(self.usecase_combo)
        
        layout.addLayout(form_layout)
        
        # Button box
        button_box = QDialogButtonBox()
        button_box.setObjectName("buttonBox")
        
        save_btn = QPushButton("SAVE CHANGES")
        save_btn.setObjectName("saveButton")
        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setObjectName("cancelButton")
        delete_btn = QPushButton("DELETE MAKRO")
        delete_btn.setObjectName("deleteButton")
        
        button_box.addButton(save_btn, QDialogButtonBox.AcceptRole)
        button_box.addButton(cancel_btn, QDialogButtonBox.RejectRole)
        button_box.addButton(delete_btn, QDialogButtonBox.DestructiveRole)
        
        save_btn.clicked.connect(self.save_changes)
        cancel_btn.clicked.connect(self.reject)
        delete_btn.clicked.connect(self.delete_makro)
        
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def apply_styles(self):
        """Apply dialog styles"""
        self.setStyleSheet("""
            QDialog {
                background-color: #0a0a0a;
                color: #f2f2f2;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            #dialogHeader {
                font-size: 20px;
                font-weight: bold;
                color: #FFB238;
                margin-bottom: 10px;
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
            
            #comboField QAbstractItemView {
                background-color: #151515;
                border: 1px solid #2b2b2b;
                selection-background-color: #FFB238;
                selection-color: #0a0a0a;
            }
            
            #saveButton {
                background-color: #FFB238;
                color: #0a0a0a;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            
            #saveButton:hover {
                background-color: #ffc24d;
            }
            
            #cancelButton {
                background-color: #2b2b2b;
                color: #a9abb0;
                border: 1px solid #555555;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                min-width: 120px;
            }
            
            #cancelButton:hover {
                background-color: #555555;
                color: #f2f2f2;
            }
            
            #deleteButton {
                background-color: #d63447;
                color: #ffffff;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            
            #deleteButton:hover {
                background-color: #c92a3d;
            }
        """)
    
    def load_data(self):
        """Load makro data into form fields"""
        self.name_input.setText(self.makro_data.get('name', ''))
        self.desc_input.setPlainText(self.makro_data.get('desc', ''))
        
        usecase = self.makro_data.get('usecase', 'Other')
        index = self.usecase_combo.findText(usecase)
        if index >= 0:
            self.usecase_combo.setCurrentIndex(index)
    
    def save_changes(self):
        """Save changes to the makro"""
        name = self.name_input.text().strip()
        desc = self.desc_input.toPlainText().strip()
        usecase = self.usecase_combo.currentText()
        
        if not name:
            QMessageBox.warning(self, "Invalid Input", "Name cannot be empty.")
            return
        
        try:
            if not self.api_client:
                # Simulate save for testing
                QMessageBox.information(self, "Success", f"Changes saved for '{name}'")
                self.accept()
                return
            
            # Real API call
            result = self.api_client.update_makro(
                self.makro_id,
                name=name,
                desc=desc if desc else None,
                usecase=usecase
            )
            
            QMessageBox.information(self, "Success", "Makro updated successfully!")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save changes: {str(e)}")
    
    def delete_makro(self):
        """Delete the makro"""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{self.makro_data.get('name', 'this makro')}'?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if not self.api_client:
                    # Simulate delete for testing
                    QMessageBox.information(self, "Deleted", f"Makro '{self.makro_data.get('name')}' has been deleted.")
                    self.accept()
                    return
                
                # Real API call
                self.api_client.delete_makro(self.makro_id)
                QMessageBox.information(self, "Deleted", "Makro deleted successfully!")
                self.accept()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete makro: {str(e)}")


class MyMakroCard(QFrame):
    """Card widget for user's own makros"""
    configure_requested = Signal(dict)  # makro_data
    download_requested = Signal(int, str)  # makro_id, makro_name
    
    def __init__(self, makro_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.makro_data = makro_data
        self.init_ui()
        self.apply_styles()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header with name and creation date
        header_layout = QHBoxLayout()
        
        name_label = QLabel(self.makro_data.get('name', 'Unknown'))
        name_label.setObjectName("makroName")
        
        # Format creation date if available
        created_at = self.makro_data.get('created_at', 'Unknown')
        if isinstance(created_at, str) and 'T' in created_at:
            # Parse ISO format date
            created_at = created_at.split('T')[0]
        
        date_label = QLabel(f"Created: {created_at}")
        date_label.setObjectName("makroDate")
        
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        header_layout.addWidget(date_label)
        
        layout.addLayout(header_layout)
        
        # Description
        desc = self.makro_data.get('desc', 'No description')
        if len(desc) > 100:
            desc = desc[:100] + "..."
        
        desc_label = QLabel(desc)
        desc_label.setObjectName("makroDesc")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Bottom row with usecase and buttons
        bottom_layout = QHBoxLayout()
        
        usecase = self.makro_data.get('usecase', 'General')
        usecase_label = QLabel(f"#{usecase}")
        usecase_label.setObjectName("makroUsecase")
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        download_btn = QPushButton("DOWNLOAD")
        download_btn.setObjectName("downloadButton")
        download_btn.clicked.connect(self.request_download)
        
        config_btn = QPushButton("CONFIGURE")
        config_btn.setObjectName("configButton")
        config_btn.clicked.connect(self.request_configure)
        
        button_layout.addWidget(download_btn)
        button_layout.addWidget(config_btn)
        
        bottom_layout.addWidget(usecase_label)
        bottom_layout.addStretch()
        bottom_layout.addLayout(button_layout)
        
        layout.addLayout(bottom_layout)
        self.setLayout(layout)
    
    def apply_styles(self):
        self.setStyleSheet("""
            MyMakroCard {
                background-color: #151515;
                border: 1px solid #2b2b2b;
                border-radius: 8px;
                margin: 5px;
            }
            
            MyMakroCard:hover {
                border-color: #FFB238;
                background-color: #111111;
            }
            
            #makroName {
                font-size: 16px;
                font-weight: bold;
                color: #FFB238;
            }
            
            #makroDate {
                font-size: 11px;
                color: #9ea0a4;
            }
            
            #makroDesc {
                color: #a9abb0;
                font-size: 13px;
                line-height: 1.4;
            }
            
            #makroUsecase {
                color: #ffc24d;
                font-size: 12px;
                font-weight: bold;
            }
            
            #downloadButton {
                background-color: #2b2b2b;
                color: #FFB238;
                border: 1px solid #FFB238;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                min-width: 80px;
            }
            
            #downloadButton:hover {
                background-color: #FFB238;
                color: #0a0a0a;
            }
            
            #configButton {
                background-color: #FFB238;
                color: #0a0a0a;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                min-width: 80px;
            }
            
            #configButton:hover {
                background-color: #ffc24d;
            }
        """)
    
    def request_configure(self):
        """Request to configure this makro"""
        self.configure_requested.emit(self.makro_data)
    
    def request_download(self):
        """Request to download this makro"""
        makro_id = self.makro_data.get('id')
        makro_name = self.makro_data.get('name', 'makro')
        if makro_id:
            self.download_requested.emit(makro_id, makro_name)


class MyMakrosWidget(QWidget):
    """Widget for managing user's uploaded makros"""
    
    def __init__(self, api_client=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client or MakrosAPIClient()
        #self.api_client = api_client  # For testing without API
        
        self.current_page = 1
        self.per_page = 5
        self.total_pages = 1
        self.current_makros = []
        
        self.setWindowTitle("My Makros")
        self.setMinimumSize(800, 600)
        self.init_ui()
        self.apply_styles()
        
        # Load initial data
        self.load_my_makros()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("MY MAKROS")
        title.setObjectName("header")
        
        refresh_btn = QPushButton("REFRESH")
        refresh_btn.setObjectName("refreshButton")
        refresh_btn.clicked.connect(self.load_my_makros)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Search and filters
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(15)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search my makros...")
        self.search_input.setObjectName("searchInput")
        self.search_input.textChanged.connect(self.filter_makros)
        
        self.usecase_filter = QComboBox()
        self.usecase_filter.setObjectName("filterCombo")
        self.usecase_filter.addItems(["All Categories", "Productivity", "Development", "Gaming", "Testing", "Automation", "Utility", "Other"])
        self.usecase_filter.currentTextChanged.connect(self.filter_makros)
        
        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.search_input, 2)
        filter_layout.addWidget(QLabel("Category:"))
        filter_layout.addWidget(self.usecase_filter, 1)
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # Makros list (scrollable)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("scrollArea")
        
        self.makros_widget = QWidget()
        self.makros_layout = QVBoxLayout()
        self.makros_layout.setSpacing(10)
        self.makros_widget.setLayout(self.makros_layout)
        
        self.scroll_area.setWidget(self.makros_widget)
        layout.addWidget(self.scroll_area)
        
        # Pagination
        pagination_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("← PREVIOUS")
        self.prev_btn.setObjectName("pageButton")
        self.prev_btn.clicked.connect(self.prev_page)
        
        self.page_label = QLabel("Page 1 of 1")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setObjectName("pageLabel")
        
        self.next_btn = QPushButton("NEXT →")
        self.next_btn.setObjectName("pageButton")
        self.next_btn.clicked.connect(self.next_page)
        
        pagination_layout.addWidget(self.prev_btn)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.next_btn)
        
        layout.addLayout(pagination_layout)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)
        
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
            
            #refreshButton {
                background-color: #2b2b2b;
                color: #FFB238;
                border: 1px solid #FFB238;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            
            #refreshButton:hover {
                background-color: #FFB238;
                color: #0a0a0a;
            }
            
            #searchInput {
                padding: 10px;
                border: 2px solid #2b2b2b;
                border-radius: 6px;
                background-color: #151515;
                color: #f2f2f2;
                font-size: 14px;
            }
            
            #searchInput:focus {
                border-color: #FFB238;
                background-color: #111111;
            }
            
            #filterCombo {
                padding: 10px;
                border: 2px solid #2b2b2b;
                border-radius: 6px;
                background-color: #151515;
                color: #f2f2f2;
                font-size: 14px;
            }
            
            #filterCombo:focus {
                border-color: #FFB238;
            }
            
            #filterCombo QAbstractItemView {
                background-color: #151515;
                border: 1px solid #2b2b2b;
                selection-background-color: #FFB238;
                selection-color: #0a0a0a;
            }
            
            #scrollArea {
                border: none;
                background-color: transparent;
            }
            
            #pageButton {
                background-color: #151515;
                color: #a9abb0;
                border: 1px solid #2b2b2b;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            
            #pageButton:hover {
                background-color: #2b2b2b;
                color: #FFB238;
            }
            
            #pageButton:disabled {
                background-color: #111111;
                color: #555555;
                border-color: #555555;
            }
            
            #pageLabel {
                color: #9ea0a4;
                font-size: 14px;
            }
            
            #statusLabel {
                color: #9ea0a4;
                font-size: 12px;
            }
            
            QLabel {
                color: #a9abb0;
            }
        """)
    
    def load_my_makros(self):
        """Load user's makros"""
        try:
            if not self.api_client:
                # Generate fake user makros for testing
                fake_makros = []
                for i in range(self.per_page):
                    fake_makros.append({
                        'id': i + 1 + (self.current_page - 1) * self.per_page,
                        'name': f'My Makro {i + 1 + (self.current_page - 1) * self.per_page}',
                        'desc': f'This is my personal makro #{i + 1}. It does various useful things.',
                        'usecase': ['Productivity', 'Development', 'Testing', 'Other'][i % 4],
                        'created_at': '2024-01-15',
                        'author': {'name': 'Me'}
                    })
                
                self.all_makros = fake_makros + [
                    # Add more fake data for pagination testing
                    {'id': 10, 'name': 'Advanced Tool', 'desc': 'Advanced makro', 'usecase': 'Development', 'created_at': '2024-01-10'},
                    {'id': 11, 'name': 'Game Helper', 'desc': 'Gaming utility', 'usecase': 'Gaming', 'created_at': '2024-01-08'},
                ]
                
                self.display_makros(fake_makros)
                self.total_pages = 3  # Simulate multiple pages
                self.update_pagination()
                self.status_label.setText(f"Loaded {len(fake_makros)} of your makros")
                return
            
            # Real API call
            result = self.api_client.list_my_makros(
                page=self.current_page,
                per_page=self.per_page
            )
            
            makros = result.get('makros', [])
            self.all_makros = makros  # Store for filtering
            self.total_pages = result.get('pages', 1)
            
            self.display_makros(makros)
            self.update_pagination()
            self.status_label.setText(f"Loaded {len(makros)} of your makros")
            
        except Exception as e:
            self.status_label.setText(f"Error loading makros: {str(e)}")
    
    def display_makros(self, makros: List[Dict[str, Any]]):
        """Display makros in the scroll area"""
        # Clear existing makros
        while self.makros_layout.count():
            child = self.makros_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.current_makros = makros
        
        if not makros:
            no_results = QLabel("No makros found")
            no_results.setAlignment(Qt.AlignCenter)
            no_results.setObjectName("noResults")
            no_results.setStyleSheet("""
                #noResults {
                    color: #9ea0a4;
                    font-size: 16px;
                    padding: 50px;
                }
            """)
            self.makros_layout.addWidget(no_results)
        else:
            for makro in makros:
                card = MyMakroCard(makro)
                card.configure_requested.connect(self.handle_configure)
                card.download_requested.connect(self.handle_download)
                self.makros_layout.addWidget(card)
        
        # Add stretch to push cards to top
        self.makros_layout.addStretch()
    
    def filter_makros(self):
        """Filter makros based on search and category"""
        if not hasattr(self, 'all_makros'):
            return
        
        search_text = self.search_input.text().lower()
        selected_category = self.usecase_filter.currentText()
        
        filtered_makros = []
        for makro in self.all_makros:
            # Check search text
            if search_text:
                name_match = search_text in makro.get('name', '').lower()
                desc_match = search_text in makro.get('desc', '').lower()
                if not (name_match or desc_match):
                    continue
            
            # Check category
            if selected_category != "All Categories":
                if makro.get('usecase', '') != selected_category:
                    continue
            
            filtered_makros.append(makro)
        
        self.display_makros(filtered_makros[:self.per_page])
        self.status_label.setText(f"Showing {len(filtered_makros[:self.per_page])} filtered makros")
    
    def handle_configure(self, makro_data: Dict[str, Any]):
        """Handle configure button click"""
        dialog = MakroConfigDialog(makro_data, self.api_client, self)
        if dialog.exec() == QDialog.Accepted:
            # Refresh the list after configuration changes
            self.load_my_makros()
    
    def handle_download(self, makro_id: int, makro_name: str):
        """Handle download request for own makro"""
        from PySide6.QtWidgets import QFileDialog
        
        # Ask user where to save
        download_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Download Directory",
            str(Path.home() / "Downloads"),
            QFileDialog.ShowDirsOnly
        )
        
        if not download_dir:
            return
        
        try:
            if not self.api_client:
                # Simulate download
                QMessageBox.information(self, "Download Complete", f"Downloaded {makro_name} to {download_dir}")
                return
            
            # Real download
            safe_name = "".join(c for c in makro_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{safe_name}.zip"
            save_path = Path(download_dir) / filename
            
            content = self.api_client.download_makro(makro_id, str(save_path))
            QMessageBox.information(self, "Download Complete", f"Downloaded {makro_name} to {save_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Download Error", f"Failed to download: {str(e)}")
    
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_my_makros()
    
    def next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_my_makros()
    
    def update_pagination(self):
        """Update pagination controls"""
        self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)


def main():
    """Test the my makros widget"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    widget = MyMakrosWidget()
    widget.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()