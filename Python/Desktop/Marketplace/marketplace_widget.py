import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                              QLineEdit, QPushButton, QLabel, QScrollArea,
                              QFrame, QComboBox, QFileDialog, QMessageBox,
                              QProgressBar, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QPalette, QColor

# Import your API client
from marketService import MakrosAPIClient


class DownloadThread(QThread):
    """Thread for downloading makros"""
    progress = Signal(int)
    finished = Signal(str)  # Success message
    error = Signal(str)
    
    def __init__(self, api_client, makro_id: int, save_path: str):
        super().__init__()
        self.api_client = api_client
        self.makro_id = makro_id
        self.save_path = save_path
    
    def run(self):
        try:
            if not self.api_client:
                # Simulate download for testing
                import time
                for i in range(101):
                    time.sleep(0.01)
                    self.progress.emit(i)
                self.finished.emit(f"Downloaded makro to {self.save_path}")
                return
            
            # Real download
            content = self.api_client.download_makro(self.makro_id, self.save_path)
            self.finished.emit(f"Downloaded makro to {self.save_path}")
            
        except Exception as e:
            self.error.emit(f"Download failed: {str(e)}")


class MakroCard(QFrame):
    """Individual makro card widget"""
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
        
        # Header with name and author
        header_layout = QHBoxLayout()
        
        name_label = QLabel(self.makro_data.get('name', 'Unknown'))
        name_label.setObjectName("makroName")
        
        author_label = QLabel(f"by {self.makro_data.get('author', {}).get('name', 'Unknown')}")
        author_label.setObjectName("makroAuthor")
        
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        header_layout.addWidget(author_label)
        
        layout.addLayout(header_layout)
        
        # Description
        desc = self.makro_data.get('desc', 'No description available')
        if len(desc) > 100:
            desc = desc[:100] + "..."
        
        desc_label = QLabel(desc)
        desc_label.setObjectName("makroDesc")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Use case and download button
        bottom_layout = QHBoxLayout()
        
        usecase = self.makro_data.get('usecase', 'General')
        usecase_label = QLabel(f"#{usecase}")
        usecase_label.setObjectName("makroUsecase")
        
        download_btn = QPushButton("DOWNLOAD")
        download_btn.setObjectName("downloadButton")
        download_btn.clicked.connect(self.request_download)
        
        bottom_layout.addWidget(usecase_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(download_btn)
        
        layout.addLayout(bottom_layout)
        self.setLayout(layout)
    
    def apply_styles(self):
        self.setStyleSheet("""
            MakroCard {
                background-color: #151515;
                border: 1px solid #2b2b2b;
                border-radius: 8px;
                margin: 5px;
            }
            
            MakroCard:hover {
                border-color: #FFB238;
                background-color: #111111;
            }
            
            #makroName {
                font-size: 16px;
                font-weight: bold;
                color: #FFB238;
            }
            
            #makroAuthor {
                font-size: 12px;
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
            }
            
            #downloadButton:hover {
                background-color: #FFB238;
                color: #0a0a0a;
            }
        """)
    
    def request_download(self):
        makro_id = self.makro_data.get('id')
        makro_name = self.makro_data.get('name', 'makro')
        if makro_id:
            self.download_requested.emit(makro_id, makro_name)


class MarketplaceWidget(QWidget):
    """Marketplace browser widget with search and pagination"""
    
    def __init__(self, api_client=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client or MakrosAPIClient()
        #self.api_client = api_client  # For testing without API
        
        self.current_page = 1
        self.per_page = 5
        self.total_pages = 1
        self.current_makros = []
        
        self.setWindowTitle("Makros Marketplace")
        self.setMinimumSize(800, 600)
        self.init_ui()
        self.apply_styles()
        
        # Load initial data
        self.load_makros()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("MARKETPLACE")
        header.setAlignment(Qt.AlignCenter)
        header.setObjectName("header")
        layout.addWidget(header)
        
        # Search and filters
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(15)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search makros...")
        self.search_input.setObjectName("searchInput")
        self.search_input.returnPressed.connect(self.search_makros)
        
        self.usecase_filter = QComboBox()
        self.usecase_filter.setObjectName("filterCombo")
        self.usecase_filter.addItems(["All Categories", "Productivity", "Development", "Gaming", "Testing", "Other"])
        self.usecase_filter.currentTextChanged.connect(self.filter_changed)
        
        self.author_filter = QLineEdit()
        self.author_filter.setPlaceholderText("Filter by author...")
        self.author_filter.setObjectName("searchInput")
        self.author_filter.returnPressed.connect(self.search_makros)
        
        search_btn = QPushButton("SEARCH")
        search_btn.setObjectName("primaryButton")
        search_btn.clicked.connect(self.search_makros)
        
        random_btn = QPushButton("RANDOM")
        random_btn.setObjectName("secondaryButton")
        random_btn.clicked.connect(self.load_random_makros)
        
        filter_layout.addWidget(self.search_input, 2)
        filter_layout.addWidget(self.usecase_filter, 1)
        filter_layout.addWidget(self.author_filter, 1)
        filter_layout.addWidget(search_btn)
        filter_layout.addWidget(random_btn)
        
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
        
        # Progress bar for downloads
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
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
            
            #primaryButton {
                background-color: #FFB238;
                color: #0a0a0a;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            
            #primaryButton:hover {
                background-color: #ffc24d;
            }
            
            #secondaryButton {
                background-color: #2b2b2b;
                color: #FFB238;
                border: 1px solid #FFB238;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            
            #secondaryButton:hover {
                background-color: #FFB238;
                color: #0a0a0a;
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
    
    def load_makros(self):
        """Load makros from marketplace"""
        try:
            if not self.api_client:
                # Generate fake data for testing
                fake_makros = []
                for i in range(self.per_page):
                    fake_makros.append({
                        'id': i + 1 + (self.current_page - 1) * self.per_page,
                        'name': f'Sample Makro {i + 1 + (self.current_page - 1) * self.per_page}',
                        'desc': f'This is a sample makro description for testing purposes. It demonstrates the marketplace functionality.',
                        'usecase': 'Testing',
                        'author': {'name': f'User{i + 1}'}
                    })
                
                self.display_makros(fake_makros)
                self.total_pages = 5  # Simulate 5 pages
                self.update_pagination()
                self.status_label.setText(f"Loaded {len(fake_makros)} makros (page {self.current_page})")
                return
            
            # Real API call
            result = self.api_client.list_marketplace_makros(
                page=self.current_page,
                per_page=self.per_page
            )
            
            makros = result.get('makros', [])
            self.total_pages = result.get('pages', 1)
            
            self.display_makros(makros)
            self.update_pagination()
            self.status_label.setText(f"Loaded {len(makros)} makros")
            
        except Exception as e:
            self.status_label.setText(f"Error loading makros: {str(e)}")
    
    def search_makros(self):
        """Search makros with current filters"""
        query = self.search_input.text().strip() or None
        usecase = self.usecase_filter.currentText()
        if usecase == "All Categories":
            usecase = None
        author = self.author_filter.text().strip() or None
        
        try:
            if not self.api_client:
                # Simulate search results
                fake_results = []
                search_term = query or "search"
                for i in range(min(3, self.per_page)):  # Fewer results for search
                    fake_results.append({
                        'id': i + 100,
                        'name': f'{search_term.title()} Result {i + 1}',
                        'desc': f'Search result for "{search_term}". This makro matches your search criteria.',
                        'usecase': usecase or 'Testing',
                        'author': {'name': f'Author{i + 1}'}
                    })
                
                self.display_makros(fake_results)
                self.total_pages = 1
                self.current_page = 1
                self.update_pagination()
                self.status_label.setText(f"Found {len(fake_results)} results")
                return
            
            # Real API call
            result = self.api_client.search_makros(
                query=query,
                usecase=usecase,
                author=author,
                page=self.current_page,
                per_page=self.per_page
            )
            
            makros = result.get('makros', [])
            self.total_pages = result.get('pages', 1)
            
            self.display_makros(makros)
            self.update_pagination()
            self.status_label.setText(f"Found {len(makros)} results")
            
        except Exception as e:
            self.status_label.setText(f"Search error: {str(e)}")
    
    def load_random_makros(self):
        """Load random makros"""
        try:
            if not self.api_client:
                # Generate random fake data
                import random
                fake_makros = []
                for i in range(self.per_page):
                    fake_makros.append({
                        'id': random.randint(1000, 9999),
                        'name': f'Random Makro {random.randint(1, 100)}',
                        'desc': f'This is a randomly selected makro for discovery purposes.',
                        'usecase': random.choice(['Productivity', 'Development', 'Gaming', 'Other']),
                        'author': {'name': f'RandomUser{random.randint(1, 50)}'}
                    })
                
                self.display_makros(fake_makros)
                self.total_pages = 1
                self.current_page = 1
                self.update_pagination()
                self.status_label.setText(f"Loaded {len(fake_makros)} random makros")
                return
            
            # Real API call
            result = self.api_client.get_random_makros(count=self.per_page)
            makros = result.get('makros', [])
            
            self.display_makros(makros)
            self.total_pages = 1
            self.current_page = 1
            self.update_pagination()
            self.status_label.setText(f"Loaded {len(makros)} random makros")
            
        except Exception as e:
            self.status_label.setText(f"Error loading random makros: {str(e)}")
    
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
                card = MakroCard(makro)
                card.download_requested.connect(self.handle_download)
                self.makros_layout.addWidget(card)
        
        # Add stretch to push cards to top
        self.makros_layout.addStretch()
    
    def handle_download(self, makro_id: int, makro_name: str):
        """Handle makro download request"""
        # Ask user where to save
        download_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Download Directory",
            str(Path.home() / "Downloads"),
            QFileDialog.ShowDirsOnly
        )
        
        if not download_dir:
            return
        
        # Create filename
        safe_name = "".join(c for c in makro_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_name}.zip"
        save_path = Path(download_dir) / filename
        
        # Start download in thread
        self.download_thread = DownloadThread(self.api_client, makro_id, str(save_path))
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.error.connect(self.download_error)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Downloading {makro_name}...")
        
        self.download_thread.start()
    
    def update_progress(self, value: int):
        """Update download progress"""
        self.progress_bar.setValue(value)
    
    def download_finished(self, message: str):
        """Handle download completion"""
        self.progress_bar.setVisible(False)
        self.status_label.setText(message)
        
        QMessageBox.information(self, "Download Complete", message)
    
    def download_error(self, error_msg: str):
        """Handle download error"""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Download failed: {error_msg}")
        
        QMessageBox.critical(self, "Download Error", error_msg)
    
    def filter_changed(self):
        """Handle filter combo box changes"""
        if self.search_input.text().strip() or self.author_filter.text().strip():
            # If there are search terms, perform search
            self.search_makros()
        else:
            # Otherwise, reload normal marketplace view
            self.current_page = 1
            self.load_makros()
    
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            if self.search_input.text().strip() or self.author_filter.text().strip() or self.usecase_filter.currentText() != "All Categories":
                self.search_makros()
            else:
                self.load_makros()
    
    def next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            if self.search_input.text().strip() or self.author_filter.text().strip() or self.usecase_filter.currentText() != "All Categories":
                self.search_makros()
            else:
                self.load_makros()
    
    def update_pagination(self):
        """Update pagination controls"""
        self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)


def main():
    """Test the marketplace widget"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    widget = MarketplaceWidget()
    widget.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()