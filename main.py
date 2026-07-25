# main.py - Professional Challan Generator with Top Navigation

import sys
import os
import json
import copy
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QDateEdit, QFormLayout,
    QScrollArea, QFrame, QMessageBox, QTabWidget, QGroupBox,
    QGridLayout, QSpinBox, QComboBox, QColorDialog, QDoubleSpinBox,
    QFileDialog, QCheckBox, QSlider, QListWidget, QListWidgetItem,
    QInputDialog, QSplitter, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsRectItem, QGraphicsPixmapItem,
    QDialog, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QMenuBar, QMenu, QDialogButtonBox, QStackedWidget, QSizePolicy,
    QProgressBar, QToolBar, QGraphicsPixmapItem , QListView
)
from PyQt6.QtWidgets import QStyledItemDelegate  # Ensure this is imported

from PyQt6.QtCore import (
    Qt, QTimer, QDate, QUrl, pyqtSignal, QRectF, QPointF, QSize,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
)
from PyQt6.QtGui import (
    QFont, QColor, QDesktopServices, QPen, QBrush, QPainter, QPixmap, QImage,
    QTransform, QKeySequence, QAction, QIcon, QPainterPath, QLinearGradient,
    QPalette, QFontDatabase, QWheelEvent
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from app import get_generator

API_BASE = "http://localhost:5173/api"
A4_WIDTH_PT = 595.27
A4_HEIGHT_PT = 841.89


class OpaqueItemDelegate(QStyledItemDelegate):
    """Ensures cell editors have a solid background and auto-select text on edit."""
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if editor:
            # Force solid background so underlying text doesn't show through
            editor.setStyleSheet("background-color: #ffffff; color: #0f172a; border: 1px solid #1a73e8;")
            editor.setAutoFillBackground(True)
        return editor

    def setEditorData(self, editor, index):
        super().setEditorData(editor, index)
        if isinstance(editor, QLineEdit):
            # Auto-select text so typing immediately replaces the old value!
            editor.selectAll()


# ======================== COMPANY DATA MANAGER ========================

class CompanyDataManager:
    """Manages saved company data for quick form filling"""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.companies_file = os.path.join(self.base_dir, 'config', 'companies.json')
        self.companies = []
        self._load_companies()
        
    def _load_companies(self):
        try:
            with open(self.companies_file, 'r') as f:
                data = json.load(f)
                self.companies = data.get('companies', [])
        except (FileNotFoundError, json.JSONDecodeError):
            self.companies = []
            self._save_companies()
            
    def _save_companies(self):
        os.makedirs(os.path.dirname(self.companies_file), exist_ok=True)
        with open(self.companies_file, 'w') as f:
            json.dump({'companies': self.companies}, f, indent=4)
            
    def get_all_companies(self) -> List[Dict]:
        return self.companies
        
    def get_company(self, name: str) -> Optional[Dict]:
        for company in self.companies:
            if company.get('name') == name:
                return company
        return None
        
    def add_company(self, company_data: Dict):
        for i, c in enumerate(self.companies):
            if c.get('name') == company_data.get('name'):
                self.companies[i] = company_data
                self._save_companies()
                return
        self.companies.append(company_data)
        self._save_companies()
        
    def delete_company(self, name: str):
        self.companies = [c for c in self.companies if c.get('name') != name]
        self._save_companies()
        
    def get_company_names(self) -> List[str]:
        return [c.get('name', 'Unnamed') for c in self.companies]


# ======================== COMPANY MANAGEMENT DIALOG ========================

class CompanyManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = CompanyDataManager()
        self.setWindowTitle("Manage Companies")
        self.setMinimumSize(600, 500)
        self.setup_ui()
        self.load_companies()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        header = QLabel("Manage Company Data")
        header.setStyleSheet("font-size: 16px; font-weight: 600; color: #1a73e8;")
        layout.addWidget(header)
        
        form_group = QGroupBox("Add / Edit Company")
        form_layout = QFormLayout(form_group)
        
        self.company_name_in = QLineEdit()
        self.company_name_in.setPlaceholderText("e.g., GSC GLASS PRIVATE LIMITED")
        form_layout.addRow("Company Name *:", self.company_name_in)
        
        self.customer_address_in = QLineEdit()
        self.customer_address_in.setPlaceholderText("Full address")
        form_layout.addRow("Address:", self.customer_address_in)
        
        self.customer_gstin_in = QLineEdit()
        self.customer_gstin_in.setPlaceholderText("e.g., 09AAACG0050D1ZA")
        form_layout.addRow("GSTIN:", self.customer_gstin_in)
        
        self.customer_state_in = QLineEdit()
        self.customer_state_in.setPlaceholderText("e.g., UTTAR PRADESH")
        form_layout.addRow("State:", self.customer_state_in)
        
        self.customer_code_in = QLineEdit()
        self.customer_code_in.setPlaceholderText("e.g., 09")
        form_layout.addRow("State Code:", self.customer_code_in)
        
        self.vehicle_no_in = QLineEdit()
        self.vehicle_no_in.setPlaceholderText("e.g., UP-14-BT-9999")
        form_layout.addRow("Vehicle No:", self.vehicle_no_in)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Company")
        self.save_btn.setStyleSheet("background: #1a73e8; color: white; font-weight: 600; border-radius: 6px; padding: 8px 16px;")
        self.save_btn.clicked.connect(self.save_company)
        btn_layout.addWidget(self.save_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_form)
        btn_layout.addWidget(self.clear_btn)
        
        btn_layout.addStretch()
        form_layout.addRow(btn_layout)
        
        layout.addWidget(form_group)
        
        list_group = QGroupBox("Saved Companies")
        list_layout = QVBoxLayout(list_group)
        
        self.company_list = QListWidget()
        self.company_list.itemClicked.connect(self.on_company_selected)
        list_layout.addWidget(self.company_list)
        
        list_btn_layout = QHBoxLayout()
        load_btn = QPushButton("Load Selected")
        load_btn.clicked.connect(self.load_selected_company)
        list_btn_layout.addWidget(load_btn)
        
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("color: #dc3545;")
        delete_btn.clicked.connect(self.delete_selected_company)
        list_btn_layout.addWidget(delete_btn)
        
        list_btn_layout.addStretch()
        list_layout.addLayout(list_btn_layout)
        
        layout.addWidget(list_group)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def load_companies(self):
        self.company_list.clear()
        for company in self.manager.get_all_companies():
            name = company.get('name', 'Unnamed')
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, company)
            self.company_list.addItem(item)
            
    def save_company(self):
        name = self.company_name_in.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Field", "Company Name is required!")
            return
            
        company_data = {
            "name": name,
            "customer_address": self.customer_address_in.text().strip(),
            "customer_gstin": self.customer_gstin_in.text().strip(),
            "customer_state": self.customer_state_in.text().strip(),
            "customer_state_code": self.customer_code_in.text().strip(),
            "vehicle_no": self.vehicle_no_in.text().strip()
        }
        
        self.manager.add_company(company_data)
        self.load_companies()
        self.clear_form()
        QMessageBox.information(self, "Success", f"Company '{name}' saved successfully!")
        
    def clear_form(self):
        self.company_name_in.clear()
        self.customer_address_in.clear()
        self.customer_gstin_in.clear()
        self.customer_state_in.clear()
        self.customer_code_in.clear()
        self.vehicle_no_in.clear()
        
    def on_company_selected(self, item: QListWidgetItem):
        company = item.data(Qt.ItemDataRole.UserRole)
        if company:
            self.company_name_in.setText(company.get('name', ''))
            self.customer_address_in.setText(company.get('customer_address', ''))
            self.customer_gstin_in.setText(company.get('customer_gstin', ''))
            self.customer_state_in.setText(company.get('customer_state', ''))
            self.customer_code_in.setText(company.get('customer_state_code', ''))
            self.vehicle_no_in.setText(company.get('vehicle_no', ''))
            
    def load_selected_company(self):
        item = self.company_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a company first!")
            return
        self.on_company_selected(item)
        
    def delete_selected_company(self):
        item = self.company_list.currentItem()
        if not item:
            return
            
        name = item.text()
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete company '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.delete_company(name)
            self.load_companies()
            self.clear_form()


# ======================== ZOOMABLE PREVIEW WIDGET ========================

class ZoomablePreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = None
        self.zoom_level = 1.0
        self.min_zoom = 0.25
        self.max_zoom = 4.0
        self.pan_start = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with zoom controls
        header = QWidget()
        header.setStyleSheet("background: #f8fafc; border-bottom: 1px solid #e2e8f0;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        
        header_layout.addWidget(QLabel("Live Preview"))
        
        header_layout.addStretch()
        
        # Zoom controls
        zoom_out_btn = QPushButton("−")
        zoom_out_btn.setFixedSize(28, 28)
        zoom_out_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #f1f5f9;
            }
        """)
        zoom_out_btn.clicked.connect(lambda: self.set_zoom(self.zoom_level - 0.1))
        header_layout.addWidget(zoom_out_btn)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setStyleSheet("font-weight: 500; font-size: 13px;")
        header_layout.addWidget(self.zoom_label)
        
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(28, 28)
        zoom_in_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #f1f5f9;
            }
        """)
        zoom_in_btn.clicked.connect(lambda: self.set_zoom(self.zoom_level + 0.1))
        header_layout.addWidget(zoom_in_btn)
        
        zoom_fit_btn = QPushButton("Fit")
        zoom_fit_btn.setFixedSize(40, 28)
        zoom_fit_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #f1f5f9;
            }
        """)
        zoom_fit_btn.clicked.connect(self.fit_to_view)
        header_layout.addWidget(zoom_fit_btn)
        
        zoom_100_btn = QPushButton("100%")
        zoom_100_btn.setFixedSize(45, 28)
        zoom_100_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #f1f5f9;
            }
        """)
        zoom_100_btn.clicked.connect(lambda: self.set_zoom(1.0))
        header_layout.addWidget(zoom_100_btn)
        
        layout.addWidget(header)
        
        # Graphics view for preview
        self.graphics_view = QGraphicsView()
        self.graphics_view.setStyleSheet("""
            QGraphicsView {
                background: #ffffff;
                border: none;
            }
        """)
        self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.graphics_view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.graphics_view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.graphics_view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.graphics_view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)
        
        # Placeholder text
        self.placeholder_item = self.scene.addText("No preview available\n\nFill in the form to see live preview")
        self.placeholder_item.setDefaultTextColor(QColor("#94a3b8"))
        self.placeholder_item.setPos(200, 300)
        
        self.image_item = QGraphicsPixmapItem()
        self.scene.addItem(self.image_item)
        self.image_item.setVisible(False)
        
        layout.addWidget(self.graphics_view)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("padding: 6px 16px; color: #64748b; font-size: 12px; border-top: 1px solid #e2e8f0;")
        layout.addWidget(self.status_label)
        
        # Set default zoom to be larger (150%)
        self.set_zoom(1.5)
        
    def update_preview(self, pixmap_bytes):
        if pixmap_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(pixmap_bytes)
            if not pixmap.isNull():
                self.pixmap = pixmap
                self.image_item.setPixmap(pixmap)
                self.image_item.setVisible(True)
                self.placeholder_item.setVisible(False)
                self.status_label.setText("Preview updated")
                self.set_zoom(1.24)
                return
        
        # Show placeholder
        self.pixmap = None
        self.image_item.setVisible(False)
        self.placeholder_item.setVisible(True)
        self.status_label.setText("Waiting for input")
        
    def set_zoom(self, zoom_level):
        self.zoom_level = max(self.min_zoom, min(self.max_zoom, zoom_level))
        self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
        transform = QTransform()
        transform.scale(self.zoom_level, self.zoom_level)
        self.graphics_view.setTransform(transform)
        
    def fit_to_view(self):
        if self.pixmap:
            self.graphics_view.fitInView(self.image_item, Qt.AspectRatioMode.KeepAspectRatio)
            self.zoom_level = self.graphics_view.transform().m11()
            self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
        else:
            self.set_zoom(1.5)
            
    def wheelEvent(self, event: QWheelEvent):
        # Zoom with mouse wheel
        delta = event.angleDelta().y()
        if delta > 0:
            self.set_zoom(self.zoom_level + 0.1)
        else:
            self.set_zoom(self.zoom_level - 0.1)


# ======================== ITEMS TABLE WIDGET ========================

class ItemsTableWidget(QTableWidget):
    """Custom table with auto-calculation for taxable amount"""
    
    data_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.block_calc = False
        
    def setup_ui(self):
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            "#", "Description", "HSN", "Qty", "Rate (Rs)", "GST %"
        ])
        # 1. HIDE THE HORIZONTAL SCROLLBAR
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 2. AUTO-FIT COLUMNS TO THE TABLE WIDTH
        header = self.horizontalHeader()
        
        # Make 'Description' stretch to fill remaining space
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # Keep small/numeric columns sized neatly to their contents
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # #
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # HSN
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Qty
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Rate
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents) # GST %
        
        self.setMinimumHeight(150)
        self.setItemDelegate(OpaqueItemDelegate(self))
        self.itemChanged.connect(self.on_item_changed)
        
    def on_item_changed(self, item):
        if self.block_calc:
            return
            
        row = item.row()
        col = item.column()
        
        # If Qty or Rate changed, auto-calculate
        if col in [3, 4]:  # Qty or Rate column
            self.calculate_row(row)
            
        self.data_changed.emit()
        
    def calculate_row(self, row):
        """Auto-calculate taxable amount for a row"""
        self.block_calc = True
        
        try:
            qty_item = self.item(row, 3)
            rate_item = self.item(row, 4)
            
            qty = float(qty_item.text()) if qty_item and qty_item.text() else 0.0
            rate = float(rate_item.text()) if rate_item and rate_item.text() else 0.0
            
            taxable = qty * rate
            # Taxable is auto-calculated in get_items_data
            
        except Exception as e:
            print(f"Error calculating row {row}: {e}")
            
        self.block_calc = False
        
    def get_items_data(self) -> List[Dict]:
        items = []
        for r in range(self.rowCount()):
            try:
                sno_item = self.item(r, 0)
                desc_item = self.item(r, 1)
                hsn_item = self.item(r, 2)
                qty_item = self.item(r, 3)
                rate_item = self.item(r, 4)
                gst_item = self.item(r, 5)
                
                sno = sno_item.text() if sno_item else str(r+1)
                desc = desc_item.text() if desc_item else ""
                hsn = hsn_item.text() if hsn_item else ""
                
                try:
                    qty = float(qty_item.text()) if qty_item else 1.0
                except: qty = 1.0
                try:
                    rate = float(rate_item.text()) if rate_item else 0.0
                except: rate = 0.0
                
                # Auto-calculate taxable
                taxable = qty * rate
                
                gst_str = gst_item.text() if gst_item else "18%"
                try:
                    if '%' in gst_str:
                        gst_pct = float(gst_str.replace('%', '')) / 100.0
                    else:
                        gst_pct = float(gst_str) / 100.0
                except: gst_pct = 0.18
                
                cgst_pct = gst_pct / 2
                sgst_pct = gst_pct / 2
                cgst_amt = taxable * cgst_pct
                sgst_amt = taxable * sgst_pct
                row_total = taxable + cgst_amt + sgst_amt
                
                items.append({
                    "sno": sno,
                    "description": desc,
                    "hsn": hsn,
                    "qty": qty,
                    "rate": rate,
                    "taxable": taxable,
                    "cgst_rate": f"{cgst_pct * 100:.0f}%",
                    "cgst_amt": cgst_amt,
                    "sgst_rate": f"{sgst_pct * 100:.0f}%",
                    "sgst_amt": sgst_amt,
                    "igst_rate": "0%",
                    "igst_amt": 0,
                    "total": row_total
                })
            except Exception as e:
                print(f"Error parsing row {r}: {e}")
        return items
        
    def add_row(self):
        row = self.rowCount()
        self.block_calc = True
        self.insertRow(row)
        self.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.setItem(row, 1, QTableWidgetItem("New Item"))
        self.setItem(row, 2, QTableWidgetItem("84795000"))
        self.setItem(row, 3, QTableWidgetItem("1.00"))
        self.setItem(row, 4, QTableWidgetItem("0.00"))
        self.setItem(row, 5, QTableWidgetItem("18%"))
        self.block_calc = False
        self.data_changed.emit()
        
    def remove_row(self):
        row = self.currentRow()
        if row >= 0 and self.rowCount() > 1:
            self.removeRow(row)
            self.data_changed.emit()


# ======================== MAIN HOME TAB ========================

class HomeTab(QWidget):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.company_manager = CompanyDataManager()
        self.selected_company = None
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.update_preview)
        self.setup_ui()
        self.reset_defaults()
        
    def setup_ui(self):
        # Main horizontal layout with splitter for resizable panels
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Form (35%)
        left_panel = QWidget()
        left_panel.setStyleSheet("background: #ffffff;")
        left_panel.setMinimumWidth(380)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 16, 20, 16)
        left_layout.setSpacing(12)
        
        # Header
        header = QLabel("New Challan")
        header.setStyleSheet("font-size: 18px; font-weight: 700; color: #0f172a; padding-bottom: 4px;")
        left_layout.addWidget(header)
        
        # Scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)
        
        # Company Selection
        company_group = QGroupBox("Company Details")
        company_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding-top: 10px;
                margin-top: 6px;
                font-weight: 600;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
            }
        """)
        company_layout = QVBoxLayout(company_group)
        company_layout.setSpacing(8)
        
        company_row = QHBoxLayout()
        company_row.setSpacing(6)
        
        self.company_combo = QComboBox()
        self.company_combo.setView(QListView())
        self.company_combo.setMinimumWidth(150)
        self.company_combo.currentIndexChanged.connect(self.on_company_selected)
        company_row.addWidget(self.company_combo, 1)
        
        # New Company button
        new_company_btn = QPushButton("+ New")
        new_company_btn.setStyleSheet("""
            QPushButton {
                background: #1a73e8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: 500;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #1557b0;
            }
        """)
        new_company_btn.clicked.connect(self.open_company_manager)
        company_row.addWidget(new_company_btn)
        
        # # Manage button
        # manage_btn = QPushButton("⚙")
        # manage_btn.setFixedSize(28, 28)
        # manage_btn.setStyleSheet("""
        #     QPushButton {
        #         background: #f1f5f9;
        #         border: 1px solid #e2e8f0;
        #         border-radius: 4px;
        #         font-size: 12px;
        #     }
        #     QPushButton:hover {
        #         background: #e2e8f0;
        #     }
        # """)
        # manage_btn.setToolTip("Manage Companies")
        # manage_btn.clicked.connect(self.open_company_manager)
        # company_row.addWidget(manage_btn)
        
        company_layout.addLayout(company_row)
        
        # Company info display
        self.company_info = QLabel("No company selected")
        self.company_info.setStyleSheet("color: #64748b; font-size: 11px; padding: 2px 0;")
        company_layout.addWidget(self.company_info)
        
        scroll_layout.addWidget(company_group)
        
        # Items Table
        items_group = QGroupBox("Items / Services")
        items_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding-top: 10px;
                margin-top: 6px;
                font-weight: 600;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
            }
        """)
        items_layout = QVBoxLayout(items_group)
        items_layout.setSpacing(6)
        
        # Use custom items table
        self.items_table = ItemsTableWidget()
        self.items_table.data_changed.connect(self.on_item_changed)
        items_layout.addWidget(self.items_table)
        
        items_btn_layout = QHBoxLayout()
        items_btn_layout.setSpacing(6)
        add_btn = QPushButton("+ Add Row")
        add_btn.setStyleSheet("background: #1a73e8; color: white; border: none; border-radius: 4px; padding: 4px 10px; font-weight: 500; font-size: 11px;")
        add_btn.clicked.connect(self.items_table.add_row)
        items_btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("− Remove")
        remove_btn.setStyleSheet("background: #f1f5f9; border: none; border-radius: 4px; padding: 4px 10px; font-weight: 500; font-size: 11px;")
        remove_btn.clicked.connect(self.items_table.remove_row)
        items_btn_layout.addWidget(remove_btn)
        
        items_btn_layout.addStretch()
        items_layout.addLayout(items_btn_layout)
        
        scroll_layout.addWidget(items_group)
        
        # Totals - More compact
        totals_group = QGroupBox("Totals")
        totals_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding-top: 10px;
                margin-top: 6px;
                font-weight: 600;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
            }
        """)
        totals_layout = QGridLayout(totals_group)
        totals_layout.setSpacing(4)
        
        self.lbl_subtotal = QLabel("Rs 0.00")
        self.lbl_subtotal.setStyleSheet("font-weight: 500; font-size: 12px;")
        totals_layout.addWidget(QLabel("Subtotal:"), 0, 0)
        totals_layout.addWidget(self.lbl_subtotal, 0, 1)
        
        self.lbl_tax = QLabel("Rs 0.00")
        self.lbl_tax.setStyleSheet("font-weight: 500; font-size: 12px;")
        totals_layout.addWidget(QLabel("GST:"), 0, 2)
        totals_layout.addWidget(self.lbl_tax, 0, 3)
        
        self.lbl_grand = QLabel("Rs 0.00")
        self.lbl_grand.setStyleSheet("font-size: 15px; font-weight: 700; color: #1a73e8;")
        totals_layout.addWidget(QLabel("Grand Total:"), 1, 0)
        totals_layout.addWidget(self.lbl_grand, 1, 1)
        
        self.lbl_words = QLabel("Zero Rupees Only")
        self.lbl_words.setStyleSheet("font-style: italic; color: #64748b; font-size: 11px;")
        totals_layout.addWidget(QLabel("Amount in Words:"), 2, 0)
        totals_layout.addWidget(self.lbl_words, 2, 1, 1, 3)
        
        scroll_layout.addWidget(totals_group)
        
        # Generate button
        generate_btn = QPushButton("Generate Challan")
        generate_btn.setStyleSheet("""
            QPushButton {
                background: #1a73e8;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #1557b0;
            }
            QPushButton:pressed {
                background: #0d47a1;
            }
        """)
        generate_btn.clicked.connect(self.generate_challan)
        scroll_layout.addWidget(generate_btn)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll)
        
        # Right panel - Zoomable Preview (65%)
        self.preview_widget = ZoomablePreviewWidget()
        
        # Add to splitter
        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(self.preview_widget)
        self.splitter.setSizes([350, 650])  # 35% / 65% split
        
        main_layout.addWidget(self.splitter)
        
        # Load companies
        self.refresh_companies()
        
    def refresh_companies(self):
        self.company_combo.blockSignals(True)
        self.company_combo.clear()
        self.company_combo.addItem("Select a company...", None)
        for company in self.company_manager.get_all_companies():
            self.company_combo.addItem(company.get('name', 'Unnamed'), company)
        self.company_combo.blockSignals(False)
        
    def on_company_selected(self, index: int):
        if index <= 0:
            self.selected_company = None
            self.company_info.setText("No company selected")
            self.trigger_preview_update()
            return
            
        self.selected_company = self.company_combo.currentData()
        if self.selected_company:
            self.company_info.setText(
                f"Address: {self.selected_company.get('customer_address', 'N/A')} | "
                f"GSTIN: {self.selected_company.get('customer_gstin', 'N/A')}"
            )
            self.trigger_preview_update()
            
    def open_company_manager(self):
        dialog = CompanyManagementDialog(self)
        if dialog.exec():
            self.refresh_companies()
            
    def on_item_changed(self):
        self.update_totals()
        self.trigger_preview_update()
        
    def trigger_preview_update(self):
        self.preview_timer.stop()
        self.preview_timer.start(500)
        
    def update_totals(self):
        items = self.items_table.get_items_data()
        generator = get_generator()
        data = {"items": items}
        enriched = generator.process_data_and_totals(data)
        
        subtotal = float(enriched.get('subtotal', 0))
        tax_total = float(enriched.get('tax_total', 0))
        grand = float(enriched.get('amount', 0))
        
        self.lbl_subtotal.setText(f"Rs {subtotal:,.2f}")
        self.lbl_tax.setText(f"Rs {tax_total:,.2f}")
        self.lbl_grand.setText(f"Rs {grand:,.2f}")
        self.lbl_words.setText(enriched.get('amount_words', 'Zero Rupees Only'))
        
    def update_preview(self):
        if not self.selected_company:
            self.preview_widget.update_preview(None)
            return
            
        items = self.items_table.get_items_data()
        if not items:
            self.preview_widget.update_preview(None)
            return
            
        payload = {
            "copy_type": "Original Copy",
            "company_name": "NEXTUP ROBOTICS PVT LTD",
            "supplier_gstin": "09AAHCN8459L1ZM",
            "supplier_state": "UTTAR PRADESH",
            "supplier_state_code": "09",
            "date": datetime.now().strftime('%d-%m-%Y'),
            "challanNumber": f"CH-{datetime.now().strftime('%Y%m%d')}-001",
            "items": items,
            "studentName": self.selected_company.get('name', ''),
            "customer_address": self.selected_company.get('customer_address', ''),
            "customer_gstin": self.selected_company.get('customer_gstin', ''),
            "customer_state": self.selected_company.get('customer_state', ''),
            "customer_state_code": self.selected_company.get('customer_state_code', ''),
            "vehicle_no": self.selected_company.get('vehicle_no', ''),
        }
        
        generator = get_generator()
        try:
            png_bytes = generator.render_preview_png(payload, dpi=100)
            self.preview_widget.update_preview(png_bytes)
        except Exception as e:
            print("Preview error:", e)
            self.preview_widget.update_preview(None)
            
    def reset_defaults(self):
        self.items_table.blockSignals(True)
        self.items_table.setRowCount(1)
        self.items_table.setItem(0, 0, QTableWidgetItem("1"))
        self.items_table.setItem(0, 1, QTableWidgetItem("New Item"))
        self.items_table.setItem(0, 2, QTableWidgetItem("84795000"))
        self.items_table.setItem(0, 3, QTableWidgetItem("1.00"))
        self.items_table.setItem(0, 4, QTableWidgetItem("0.00"))
        self.items_table.setItem(0, 5, QTableWidgetItem("18%"))
        self.items_table.blockSignals(False)
        self.on_item_changed()
        
    def generate_challan(self):
        if not self.selected_company:
            self.main_window.toast.show_message("Please select a company first!", "error")
            return
            
        items = self.items_table.get_items_data()
        if not items or all(it.get('rate', 0) == 0 for it in items):
            self.main_window.toast.show_message("Add at least one item with a rate!", "error")
            return
            
        payload = {
            "copy_type": "Original Copy",
            "company_name": "NEXTUP ROBOTICS PVT LTD",
            "supplier_gstin": "09AAHCN8459L1ZM",
            "supplier_state": "UTTAR PRADESH",
            "supplier_state_code": "09",
            "date": datetime.now().strftime('%d-%m-%Y'),
            "challanNumber": f"CH-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}",
            "items": items,
            "studentName": self.selected_company.get('name', ''),
            "customer_address": self.selected_company.get('customer_address', ''),
            "customer_gstin": self.selected_company.get('customer_gstin', ''),
            "customer_state": self.selected_company.get('customer_state', ''),
            "customer_state_code": self.selected_company.get('customer_state_code', ''),
            "vehicle_no": self.selected_company.get('vehicle_no', ''),
        }
        
        generator = get_generator()
        save_path = generator.save_pdf(payload)
        self.main_window.toast.show_message("Challan generated successfully!", "success")
        QDesktopServices.openUrl(QUrl.fromLocalFile(save_path))


# ======================== SEARCH CHALLAN TAB ========================

class SearchTab(QWidget):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.current_results = []
        self.setup_ui()
        self.load_recent()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        header = QLabel("Search Challans")
        header.setStyleSheet("font-size: 20px; font-weight: 700; color: #0f172a;")
        layout.addWidget(header)
        
        # Search bar with filters
        search_container = QFrame()
        search_container.setStyleSheet("""
            QFrame {
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        search_layout = QVBoxLayout(search_container)
        
        # First row: Search type + search input
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        
        row1.addWidget(QLabel("Search by:"))
        
        self.search_type = QComboBox()
        self.search_type.addItems([
            "Challan Number",
            "Customer Name",
            "Date Range",
            "Amount Range",
            "HSN Code",
            "GSTIN"
        ])
        self.search_type.setStyleSheet("""
            QComboBox {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 150px;
            }
        """)
        self.search_type.currentIndexChanged.connect(self.on_search_type_changed)
        row1.addWidget(self.search_type)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #1a73e8;
            }
        """)
        self.search_input.returnPressed.connect(self.search)
        row1.addWidget(self.search_input, 1)
        
        search_btn = QPushButton("Search")
        search_btn.setStyleSheet("""
            QPushButton {
                background: #1a73e8;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 20px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #1557b0;
            }
        """)
        search_btn.clicked.connect(self.search)
        row1.addWidget(search_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                color: #0f172a;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #e2e8f0;
            }
        """)
        clear_btn.clicked.connect(self.clear_search)
        row1.addWidget(clear_btn)
        
        search_layout.addLayout(row1)
        
        # Second row: Dynamic filter widgets
        self.filter_widget = QWidget()
        self.filter_layout = QHBoxLayout(self.filter_widget)
        self.filter_layout.setContentsMargins(0, 8, 0, 0)
        self.filter_layout.setSpacing(10)
        
        # Date range widgets (hidden by default)
        self.date_widget = QWidget()
        date_layout = QHBoxLayout(self.date_widget)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setSpacing(10)
        
        date_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setStyleSheet("border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 8px;")
        date_layout.addWidget(self.date_from)
        
        date_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setStyleSheet("border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 8px;")
        date_layout.addWidget(self.date_to)
        
        date_layout.addStretch()
        self.date_widget.hide()
        self.filter_layout.addWidget(self.date_widget)
        
        # Amount range widgets (hidden by default)
        self.amount_widget = QWidget()
        amount_layout = QHBoxLayout(self.amount_widget)
        amount_layout.setContentsMargins(0, 0, 0, 0)
        amount_layout.setSpacing(10)
        
        amount_layout.addWidget(QLabel("Min:"))
        self.amount_min = QDoubleSpinBox()
        self.amount_min.setRange(0, 9999999)
        self.amount_min.setPrefix("Rs ")
        self.amount_min.setStyleSheet("border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 8px;")
        amount_layout.addWidget(self.amount_min)
        
        amount_layout.addWidget(QLabel("Max:"))
        self.amount_max = QDoubleSpinBox()
        self.amount_max.setRange(0, 9999999)
        self.amount_max.setPrefix("Rs ")
        self.amount_max.setValue(999999)
        self.amount_max.setStyleSheet("border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 8px;")
        amount_layout.addWidget(self.amount_max)
        
        amount_layout.addStretch()
        self.amount_widget.hide()
        self.filter_layout.addWidget(self.amount_widget)
        
        # Quick filters
        quick_label = QLabel("Quick:")
        quick_label.setStyleSheet("font-weight: 500; color: #64748b;")
        self.filter_layout.addWidget(quick_label)
        
        today_btn = QPushButton("Today")
        today_btn.setStyleSheet("background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 12px;")
        today_btn.clicked.connect(lambda: self.set_date_range(0))
        self.filter_layout.addWidget(today_btn)
        
        week_btn = QPushButton("This Week")
        week_btn.setStyleSheet("background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 12px;")
        week_btn.clicked.connect(lambda: self.set_date_range(7))
        self.filter_layout.addWidget(week_btn)
        
        month_btn = QPushButton("This Month")
        month_btn.setStyleSheet("background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 12px;")
        month_btn.clicked.connect(lambda: self.set_date_range(30))
        self.filter_layout.addWidget(month_btn)
        
        self.filter_layout.addStretch()
        search_layout.addWidget(self.filter_widget)
        
        layout.addWidget(search_container)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Challan No", "Customer", "Date", "Amount (Rs)", "Status", "Actions"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setStyleSheet("""
            QTableWidget {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
            QHeaderView::section {
                background: #f8fafc;
                font-weight: 600;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
            }
        """)
        layout.addWidget(self.results_table)
        
        # Results count
        self.results_count = QLabel("Showing 0 results")
        self.results_count.setStyleSheet("color: #64748b; font-size: 13px;")
        layout.addWidget(self.results_count)
        
    def on_search_type_changed(self, index):
        # Show/hide appropriate filter widgets
        search_type = self.search_type.currentText()
        
        self.date_widget.hide()
        self.amount_widget.hide()
        self.search_input.setPlaceholderText("Enter search term...")
        
        if search_type == "Date Range":
            self.date_widget.show()
            self.search_input.setPlaceholderText("Select date range using the calendar or quick filters")
        elif search_type == "Amount Range":
            self.amount_widget.show()
            self.search_input.setPlaceholderText("Enter min and max amount")
        elif search_type == "Challan Number":
            self.search_input.setPlaceholderText("Enter challan number...")
        elif search_type == "Customer Name":
            self.search_input.setPlaceholderText("Enter customer name...")
        elif search_type == "HSN Code":
            self.search_input.setPlaceholderText("Enter HSN code...")
        elif search_type == "GSTIN":
            self.search_input.setPlaceholderText("Enter GSTIN...")
            
    def set_date_range(self, days):
        self.search_type.setCurrentText("Date Range")
        self.date_from.setDate(QDate.currentDate().addDays(-days))
        self.date_to.setDate(QDate.currentDate())
        
    def clear_search(self):
        self.search_input.clear()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_to.setDate(QDate.currentDate())
        self.amount_min.setValue(0)
        self.amount_max.setValue(999999)
        self.load_recent()
        
    def search(self):
        search_type = self.search_type.currentText()
        query = self.search_input.text().strip()
        
        generator = get_generator()
        gen_dir = os.path.join(generator.base_dir, 'generated')
        if not os.path.exists(gen_dir):
            self.results_table.setRowCount(0)
            self.results_count.setText("No results found")
            return
            
        files = [f for f in os.listdir(gen_dir) if f.endswith('.pdf')]
        
        # Filter based on search type
        filtered_files = []
        
        if search_type == "Date Range":
            from_date = self.date_from.date().toString("yyyy-MM-dd")
            to_date = self.date_to.date().toString("yyyy-MM-dd")
            for f in files:
                try:
                    file_path = os.path.join(gen_dir, f)
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    file_date = mod_time.strftime("%Y-%m-%d")
                    if from_date <= file_date <= to_date:
                        filtered_files.append(f)
                except:
                    pass
        elif search_type == "Amount Range":
            min_amt = self.amount_min.value()
            max_amt = self.amount_max.value()
            filtered_files = files
        else:
            if query:
                filtered_files = [f for f in files if query.lower() in f.lower()]
            else:
                filtered_files = files
                
        self.display_results(filtered_files)
        
    def display_results(self, files):
        self.results_table.setRowCount(len(files))
        self.results_count.setText(f"Showing {len(files)} results")
        
        for idx, f in enumerate(files[:100]):
            parts = f.replace('.pdf', '').split('_')
            challan_no = parts[1] if len(parts) > 1 else 'N/A'
            
            self.results_table.setItem(idx, 0, QTableWidgetItem(challan_no))
            self.results_table.setItem(idx, 1, QTableWidgetItem("Delivery Challan"))
            
            generator = get_generator()
            file_path = os.path.join(generator.base_dir, 'generated', f)
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            self.results_table.setItem(idx, 2, QTableWidgetItem(mod_time.strftime("%Y-%m-%d %H:%M")))
            
            self.results_table.setItem(idx, 3, QTableWidgetItem("Rs 0.00"))
            self.results_table.setItem(idx, 4, QTableWidgetItem("Generated"))
            
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 4, 4, 4)
            
            open_btn = QPushButton("Open")
            open_btn.setStyleSheet("""
    QPushButton {
        background-color: #1a73e8;
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 2px 10px;
        font-size: 11px;
        font-weight: 500;
        max-height: 22px;
    }
    QPushButton:hover {
        background-color: #1557b0;
    }
""")
            open_btn.clicked.connect(lambda _, p=file_path: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
            btn_layout.addWidget(open_btn)
            
            self.results_table.setCellWidget(idx, 5, btn_widget)
            
    def load_recent(self):
        generator = get_generator()
        gen_dir = os.path.join(generator.base_dir, 'generated')
        if not os.path.exists(gen_dir):
            return
            
        files = sorted([f for f in os.listdir(gen_dir) if f.endswith('.pdf')], reverse=True)
        self.display_results(files[:50])


# ======================== SETTINGS TAB ========================

class SettingsTab(QWidget):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        header = QLabel("Settings")
        header.setStyleSheet("font-size: 20px; font-weight: 700; color: #0f172a;")
        layout.addWidget(header)
        
        # Company management
        company_group = QGroupBox("Company Management")
        company_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding-top: 12px;
                margin-top: 8px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        company_layout = QVBoxLayout(company_group)
        
        manage_btn = QPushButton("Manage Companies")
        manage_btn.setStyleSheet("background: #1a73e8; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: 500;")
        manage_btn.clicked.connect(self.open_company_manager)
        company_layout.addWidget(manage_btn)
        
        layout.addWidget(company_group)
        
        # Defaults
        defaults_group = QGroupBox("Default Settings")
        defaults_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding-top: 12px;
                margin-top: 8px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        defaults_layout = QFormLayout(defaults_group)
        
        self.default_gst = QComboBox()
        self.default_gst.addItems(["5%", "12%", "18%", "28%"])
        self.default_gst.setCurrentText("18%")
        defaults_layout.addRow("Default GST Rate:", self.default_gst)
        
        self.default_hsn = QLineEdit("84795000")
        defaults_layout.addRow("Default HSN Code:", self.default_hsn)
        
        layout.addWidget(defaults_group)
        
        layout.addStretch()
        
    def open_company_manager(self):
        dialog = CompanyManagementDialog(self)
        dialog.exec()


# ======================== TOP NAVIGATION WIDGET ========================

class TopNavigationWidget(QWidget):
    """Top navigation bar with tabs"""
    
    page_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setFixedHeight(56)
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(4)
        
        # App logo/title
        app_title = QLabel("Challan Generator")
        app_title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 700;
                color: #1a73e8;
                padding: 0 16px 0 0;
            }
        """)
        layout.addWidget(app_title)
        
        layout.addStretch()
        
        # Navigation buttons
        nav_style = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 13px;
                color: #64748b;
            }
            QPushButton:hover {
                background: #f1f5f9;
                color: #0f172a;
            }
            QPushButton:checked {
                background: #e8f0fe;
                color: #1a73e8;
            }
        """
        
        self.home_btn = QPushButton("Home")
        self.home_btn.setCheckable(True)
        self.home_btn.setChecked(True)
        self.home_btn.setStyleSheet(nav_style)
        self.home_btn.clicked.connect(lambda: self.on_button_clicked(0))
        layout.addWidget(self.home_btn)
        
        self.search_btn = QPushButton("Search Challans")
        self.search_btn.setCheckable(True)
        self.search_btn.setStyleSheet(nav_style)
        self.search_btn.clicked.connect(lambda: self.on_button_clicked(1))
        layout.addWidget(self.search_btn)
        
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setCheckable(True)
        self.settings_btn.setStyleSheet(nav_style)
        self.settings_btn.clicked.connect(lambda: self.on_button_clicked(2))
        layout.addWidget(self.settings_btn)
        
        layout.addStretch()
        
        # Add a subtle separator at bottom
        self.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border-bottom: 1px solid #e2e8f0;
            }
        """)
        
    def on_button_clicked(self, index):
        # Uncheck all buttons
        self.home_btn.setChecked(False)
        self.search_btn.setChecked(False)
        self.settings_btn.setChecked(False)
        
        # Check the clicked button
        if index == 0:
            self.home_btn.setChecked(True)
        elif index == 1:
            self.search_btn.setChecked(True)
        elif index == 2:
            self.settings_btn.setChecked(True)
            
        self.page_changed.emit(index)
        
    def set_active(self, index):
        self.on_button_clicked(index)


# ======================== MAIN WINDOW ========================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Challan Generator")
        self.setMinimumSize(1200, 800)
        
        self.network_manager = QNetworkAccessManager()
        self.toast = MessageToast(self)
        
        self.setup_ui()
        self.apply_theme()
        
    def setup_ui(self):
        central = QWidget()
        central.setStyleSheet("background: #f8fafc;")
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        self.setCentralWidget(central)
        
        # Top Navigation
        self.top_nav = TopNavigationWidget()
        self.top_nav.page_changed.connect(self.on_nav_changed)
        central_layout.addWidget(self.top_nav)
        
        # Content area
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background: #ffffff;")
        central_layout.addWidget(self.content_stack, 1)
        
        # Pages
        self.home_tab = HomeTab(self)
        self.search_tab = SearchTab(self)
        self.settings_tab = SettingsTab(self)
        
        self.content_stack.addWidget(self.home_tab)
        self.content_stack.addWidget(self.search_tab)
        self.content_stack.addWidget(self.settings_tab)
        
        # Set default selection
        self.top_nav.set_active(0)
        
    def on_nav_changed(self, index):
        self.content_stack.setCurrentIndex(index)
        
    def apply_theme(self):
        font = QFont("Inter", 10)
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        QApplication.setFont(font)


# ======================== MESSAGE TOAST ========================

class MessageToast(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        self.label = QLabel()
        self.label.setStyleSheet("color: white; font-size: 14px; font-weight: 600;")
        layout.addWidget(self.label)
        
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def show_message(self, text: str, msg_type: str = "success"):
        bg = "#10b981" if msg_type == "success" else "#ef4444" if msg_type == "error" else "#1a73e8"
        self.label.setText(text)
        self.setStyleSheet(f"QWidget {{ background-color: {bg}; border-radius: 8px; }}")
        
        if self.parent():
            geo = self.parent().geometry()
            self.move(geo.x() + geo.width() - 340, geo.y() + geo.height() - 80)
            
        self.show()
        self.timer.start(3500)


# ======================== GET GLOBAL STYLESHEET ========================

def get_global_stylesheet() -> str:
    return """
        QMainWindow {
            background: #f8fafc;
        }
        QWidget {
            color: #0f172a;
            font-family: "Inter", "Segoe UI", sans-serif;
            font-size: 13px;
        }

        /* Input Controls */
        QLineEdit, QDateEdit, QSpinBox, QDoubleSpinBox {
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 12px;
            selection-background-color: #1a73e8;
            selection-color: #ffffff;
        }

        /* --- QCOMBOBOX OVERRIDE --- */
        QComboBox {
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 12px;
        }
        QComboBox QListView {
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            padding: 4px;
            outline: 0px;
        }
        QComboBox QListView::item {
            background-color: #ffffff;
            color: #0f172a;
            padding: 6px 10px;
            min-height: 24px;
            border-radius: 4px;
        }
        QComboBox QListView::item:hover,
        QComboBox QListView::item:selected {
            background-color: #1a73e8;
            color: #ffffff;
        }

        /* --- TABLE WIDGET & INLINE CELL EDITING FIX --- */
        QTableWidget {
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            background-color: #ffffff;
            gridline-color: #f1f5f9;
            font-size: 12px;
            selection-background-color: #e8f0fe;
            selection-color: #0f172a;
        }
        QTableWidget::item {
            padding: 4px 6px;
            color: #0f172a;
            background-color: #ffffff;
        }
        QTableWidget::item:selected {
            background-color: #e8f0fe;
            color: #1a73e8;
        }
        /* Style the active line edit when typing inside a table cell */
        QTableWidget QLineEdit {
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #1a73e8;
            border-radius: 2px;
            padding: 2px 4px;
            margin: 0px;
            selection-background-color: #1a73e8;
            selection-color: #ffffff;
        }

        /* Table Headers */
        QHeaderView::section {
            background-color: #f8fafc;
            color: #475569;
            padding: 6px;
            border: none;
            border-bottom: 1px solid #e2e8f0;
            font-weight: 600;
            font-size: 11px;
        }

        /* Scrollbars & GroupBoxes */
        QScrollArea {
            border: none;
            background: transparent;
        }
        QScrollBar:vertical {
            border: none;
            background: #f1f5f9;
            width: 6px;
            border-radius: 3px;
        }
        QScrollBar::handle:vertical {
            background: #cbd5e1;
            min-height: 20px;
            border-radius: 3px;
        }
        QScrollBar::handle:vertical:hover {
            background: #94a3b8;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QSplitter::handle {
            background: #e2e8f0;
            width: 2px;
        }
        QSplitter::handle:hover {
            background: #1a73e8;
        }
        QGroupBox {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding-top: 10px;
            margin-top: 4px;
            font-weight: 600;
            font-size: 12px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 6px;
        }
        QPushButton {
            border: none;
            border-radius: 6px;
            padding: 6px 14px;
            font-weight: 500;
        }
    """

# ======================== MAIN ENTRY ========================

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(get_global_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()