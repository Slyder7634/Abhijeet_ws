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
    QProgressBar, QToolBar, QGraphicsPixmapItem , QListView,
    QStyledItemDelegate
)
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
            editor.setStyleSheet("background-color: #ffffff; color: #0f172a; border: 1px solid #1a73e8; font-size: 14px;")
            editor.setAutoFillBackground(True)
        return editor

    def setEditorData(self, editor, index):
        super().setEditorData(editor, index)
        if isinstance(editor, QLineEdit):
            # Auto-select text so typing immediately replaces the old value!
            editor.selectAll()


class SpinBoxDelegate(QStyledItemDelegate):
    """Delegate that provides a spin box with proper keyboard support"""
    
    def __init__(self, parent=None, min_val=0, max_val=999999, decimals=0, step=1.0):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self.decimals = decimals
        self.step = step
        
    def createEditor(self, parent, option, index):
        if self.decimals == 0:
            # Integer spin box for quantity
            editor = QSpinBox(parent)
            editor.setRange(int(self.min_val), int(self.max_val))
            editor.setSingleStep(int(self.step))
        else:
            # Double spin box for rate
            editor = QDoubleSpinBox(parent)
            editor.setRange(self.min_val, self.max_val)
            editor.setDecimals(self.decimals)
            editor.setSingleStep(self.step)
        
        # Style to make it look like a table cell editor - larger font
        editor.setStyleSheet("""
            QSpinBox, QDoubleSpinBox {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #1a73e8;
                border-radius: 2px;
                padding: 4px 8px;
                font-size: 14px;
                font-weight: 500;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button,
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                width: 20px;
                background-color: #f8fafc;
                border: none;
            }
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #e2e8f0;
            }
        """)
        
        # Enable keyboard tracking
        editor.setKeyboardTracking(True)
        
        # Select all text when editor opens for easy typing
        editor.selectAll()
        
        return editor
        
    def setEditorData(self, editor, index):
        value = index.data(Qt.ItemDataRole.EditRole)
        try:
            if value:
                editor.setValue(float(value))
            else:
                editor.setValue(0)
        except (ValueError, TypeError):
            editor.setValue(0)
            
    def setModelData(self, editor, model, index):
        value = editor.value()
        if self.decimals == 0:
            # Integer - no decimal places
            model.setData(index, str(int(value)), Qt.ItemDataRole.EditRole)
        else:
            # Float with proper formatting
            model.setData(index, f"{value:.2f}", Qt.ItemDataRole.EditRole)


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
        # Remove vehicle_no if it exists (backward compatibility)
        if 'vehicle_no' in company_data:
            del company_data['vehicle_no']
            
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
        self.setMinimumSize(700, 600)
        self.setup_ui()
        self.load_companies()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        header = QLabel("Manage Company Data")
        header.setStyleSheet("font-size: 20px; font-weight: 700; color: #1a73e8; padding: 8px 0;")
        layout.addWidget(header)
        
        form_group = QGroupBox("Add / Edit Company")
        form_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: 600;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding-top: 14px;
                margin-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
            }
        """)
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.company_name_in = QLineEdit()
        self.company_name_in.setPlaceholderText("e.g., GSC GLASS PRIVATE LIMITED")
        self.company_name_in.setStyleSheet("font-size: 14px; padding: 8px 12px;")
        form_layout.addRow("Company Name *:", self.company_name_in)
        
        self.customer_address_in = QLineEdit()
        self.customer_address_in.setPlaceholderText("Full address")
        self.customer_address_in.setStyleSheet("font-size: 14px; padding: 8px 12px;")
        form_layout.addRow("Address:", self.customer_address_in)
        
        self.customer_gstin_in = QLineEdit()
        self.customer_gstin_in.setPlaceholderText("e.g., 09AAACG0050D1ZA")
        self.customer_gstin_in.setStyleSheet("font-size: 14px; padding: 8px 12px;")
        form_layout.addRow("GSTIN:", self.customer_gstin_in)
        
        self.customer_state_in = QLineEdit()
        self.customer_state_in.setPlaceholderText("e.g., UTTAR PRADESH")
        self.customer_state_in.setStyleSheet("font-size: 14px; padding: 8px 12px;")
        form_layout.addRow("State:", self.customer_state_in)
        
        self.customer_code_in = QLineEdit()
        self.customer_code_in.setPlaceholderText("e.g., 09")
        self.customer_code_in.setStyleSheet("font-size: 14px; padding: 8px 12px;")
        form_layout.addRow("State Code:", self.customer_code_in)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.save_btn = QPushButton("Save Company")
        self.save_btn.setStyleSheet("background: #1a73e8; color: white; font-weight: 600; border-radius: 6px; padding: 10px 24px; font-size: 14px;")
        self.save_btn.clicked.connect(self.save_company)
        btn_layout.addWidget(self.save_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet("background: #f1f5f9; color: #0f172a; font-weight: 500; border-radius: 6px; padding: 10px 24px; font-size: 14px;")
        self.clear_btn.clicked.connect(self.clear_form)
        btn_layout.addWidget(self.clear_btn)
        
        btn_layout.addStretch()
        form_layout.addRow(btn_layout)
        
        layout.addWidget(form_group)
        
        list_group = QGroupBox("Saved Companies")
        list_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: 600;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding-top: 14px;
                margin-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
            }
        """)
        list_layout = QVBoxLayout(list_group)
        list_layout.setSpacing(8)
        
        self.company_list = QListWidget()
        self.company_list.setStyleSheet("font-size: 14px; padding: 4px;")
        self.company_list.itemClicked.connect(self.on_company_selected)
        list_layout.addWidget(self.company_list)
        
        list_btn_layout = QHBoxLayout()
        list_btn_layout.setSpacing(10)
        load_btn = QPushButton("Load Selected")
        load_btn.setStyleSheet("background: #1a73e8; color: white; font-weight: 500; border-radius: 6px; padding: 8px 20px; font-size: 14px;")
        load_btn.clicked.connect(self.load_selected_company)
        list_btn_layout.addWidget(load_btn)
        
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("color: #dc3545; font-weight: 500; border: 1px solid #dc3545; border-radius: 6px; padding: 8px 20px; font-size: 14px;")
        delete_btn.clicked.connect(self.delete_selected_company)
        list_btn_layout.addWidget(delete_btn)
        
        list_btn_layout.addStretch()
        list_layout.addLayout(list_btn_layout)
        
        layout.addWidget(list_group)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.setStyleSheet("font-size: 14px; padding: 4px;")
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
            "customer_state_code": self.customer_code_in.text().strip()
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
        
    def on_company_selected(self, item: QListWidgetItem):
        company = item.data(Qt.ItemDataRole.UserRole)
        if company:
            self.company_name_in.setText(company.get('name', ''))
            self.customer_address_in.setText(company.get('customer_address', ''))
            self.customer_gstin_in.setText(company.get('customer_gstin', ''))
            self.customer_state_in.setText(company.get('customer_state', ''))
            self.customer_code_in.setText(company.get('customer_state_code', ''))
            
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
        
        # Header with zoom controls - LARGER FONTS
        header = QWidget()
        header.setStyleSheet("background: #f8fafc; border-bottom: 1px solid #e2e8f0;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)
        
        label = QLabel("Live Preview")
        label.setStyleSheet("font-size: 16px; font-weight: 600; color: #0f172a;")
        header_layout.addWidget(label)
        
        header_layout.addStretch()
        
        # Zoom controls - LARGER BUTTONS
        zoom_out_btn = QPushButton("−")
        zoom_out_btn.setFixedSize(80, 34)
        zoom_out_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                font-weight: bold;
                font-size: 18px;
            }
            QPushButton:hover {
                background: #f1f5f9;
            }
        """)
        zoom_out_btn.clicked.connect(lambda: self.set_zoom(self.zoom_level - 0.1))
        header_layout.addWidget(zoom_out_btn)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(60)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setStyleSheet("font-weight: 600; font-size: 16px; color: #0f172a;")
        header_layout.addWidget(self.zoom_label)
        
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(80, 34)
        zoom_in_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                font-weight: bold;
                font-size: 18px;
            }
            QPushButton:hover {
                background: #f1f5f9;
            }
        """)
        zoom_in_btn.clicked.connect(lambda: self.set_zoom(self.zoom_level + 0.1))
        header_layout.addWidget(zoom_in_btn)
        
        zoom_fit_btn = QPushButton("Fit")
        zoom_fit_btn.setFixedSize(80, 34)
        zoom_fit_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                font-weight: 500;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #f1f5f9;
            }
        """)
        zoom_fit_btn.clicked.connect(self.fit_to_view)
        header_layout.addWidget(zoom_fit_btn)
        
        zoom_100_btn = QPushButton("100%")
        zoom_100_btn.setFixedSize(80, 34)
        zoom_100_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                font-weight: 500;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #f1f5f9;
            }
        """)
        zoom_100_btn.clicked.connect(lambda: self.set_zoom(1.0))
        header_layout.addWidget(zoom_100_btn)
        
        layout.addWidget(header)
        
        # Graphics view for preview - HIGH QUALITY SETTINGS (Fixed for PyQt6)
        self.graphics_view = QGraphicsView()
        self.graphics_view.setStyleSheet("""
            QGraphicsView {
                background: #ffffff;
                border: none;
            }
        """)
        # Enable high quality rendering - Fixed for PyQt6
        self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.graphics_view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.graphics_view.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        # LosslessImageRendering is available in PyQt6
        self.graphics_view.setRenderHint(QPainter.RenderHint.LosslessImageRendering)
        self.graphics_view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.graphics_view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.graphics_view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.graphics_view.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, False)
        
        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)
        
        # Placeholder text - LARGER FONT
        self.placeholder_item = self.scene.addText("No preview available\n\nFill in the form to see live preview")
        self.placeholder_item.setDefaultTextColor(QColor("#94a3b8"))
        font = QFont("Inter", 16)
        self.placeholder_item.setFont(font)
        self.placeholder_item.setPos(200, 300)
        
        self.image_item = QGraphicsPixmapItem()
        self.scene.addItem(self.image_item)
        self.image_item.setVisible(False)
        self.image_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        
        layout.addWidget(self.graphics_view)
        
        # Status bar - LARGER FONT
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("padding: 8px 20px; color: #64748b; font-size: 14px; border-top: 1px solid #e2e8f0;")
        layout.addWidget(self.status_label)
        
        # Set default zoom to 55%
        self.set_zoom(0.55)
        
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
                # IMPORTANT: Don't call fit_to_view() here!
                # Just set the zoom to your desired level
                self.set_zoom(0.55)  # <--- SET ZOOM TO 55% HERE
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
        if self.pixmap and not self.pixmap.isNull():
            self.graphics_view.fitInView(self.image_item, Qt.AspectRatioMode.KeepAspectRatio)
            self.zoom_level = self.graphics_view.transform().m11()
            self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
        else:
            self.set_zoom(0.55)
        
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
        self.verticalHeader().setDefaultSectionSize(36)   # Try 36–42 px
        
    def setup_ui(self):
        # 5 columns: #, Description, Qty, Rate, GST %
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels([
            "#", "Description", "Qty", "Rate (Rs)", "GST %"
        ])
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Set larger font for table
        self.setStyleSheet("""
            QTableWidget {
                font-size: 14px;
            }
            QTableWidget::item {
                padding: 6px 8px;
            }
        """)
        
        header = self.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Description stretches
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # #
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(2, 100)   # Qty column
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Rate
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # GST %
        
        # Set header font size
        header.setStyleSheet("font-size: 13px; font-weight: 600;")
        
        self.setMinimumHeight(180)
        self.setItemDelegate(OpaqueItemDelegate(self))
        
        # Quantity column (index 2) - INTEGER only, no decimals
        self.setItemDelegateForColumn(2, SpinBoxDelegate(
            self, 
            min_val=0, 
            max_val=999999, 
            decimals=0,  # INTEGER
            step=1.0
        ))
        
        # Rate column (index 3) - FLOAT with 2 decimals
        self.setItemDelegateForColumn(3, SpinBoxDelegate(
            self, 
            min_val=0, 
            max_val=99999999, 
            decimals=2,  # FLOAT with 2 decimal places
            step=1.0
        ))
        
        self.itemChanged.connect(self.on_item_changed)
        
    def on_item_changed(self, item):
        if self.block_calc:
            return
            
        row = item.row()
        col = item.column()
        
        # If Qty or Rate changed, auto-calculate
        if col in [2, 3]:  # Qty (index 2) or Rate (index 3) column
            self.calculate_row(row)
            
        self.data_changed.emit()
        
    def calculate_row(self, row):
        """Auto-calculate taxable amount for a row"""
        self.block_calc = True
        
        try:
            qty_item = self.item(row, 2)   # Qty column
            rate_item = self.item(row, 3)  # Rate column
            
            qty = float(qty_item.text()) if qty_item and qty_item.text() else 0.0
            rate = float(rate_item.text()) if rate_item and rate_item.text() else 0.0
            
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
                qty_item = self.item(r, 2)      # Qty column
                rate_item = self.item(r, 3)     # Rate column
                gst_item = self.item(r, 4)      # GST column
                
                sno = sno_item.text() if sno_item else str(r+1)
                desc = desc_item.text() if desc_item else ""
                
                # Parse quantity as integer
                try:
                    qty = float(qty_item.text()) if qty_item else 1.0
                except:
                    qty = 1.0
                    
                # Parse rate as float
                try:
                    rate = float(rate_item.text()) if rate_item else 0.0
                except:
                    rate = 0.0
                
                # Auto-calculate taxable
                taxable = qty * rate
                
                gst_str = gst_item.text() if gst_item else "18%"
                try:
                    if '%' in gst_str:
                        gst_pct = float(gst_str.replace('%', '')) / 100.0
                    else:
                        gst_pct = float(gst_str) / 100.0
                except:
                    gst_pct = 0.18
                
                cgst_pct = gst_pct / 2
                sgst_pct = gst_pct / 2
                cgst_amt = taxable * cgst_pct
                sgst_amt = taxable * sgst_pct
                row_total = taxable + cgst_amt + sgst_amt
                
                items.append({
                    "sno": sno,
                    "description": desc,
                    "hsn": "84795000",  # Hardcoded HSN
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
        self.setItem(row, 2, QTableWidgetItem("1"))   # Qty
        self.setItem(row, 3, QTableWidgetItem("0.00")) # Rate
        self.setItem(row, 4, QTableWidgetItem("18%"))  # GST
        self.block_calc = False
        self.data_changed.emit()

    def load_items_data(self, items: List[Dict]):
        """Populate the table from previously-saved item rows (used when editing an existing submission)"""
        self.block_calc = True
        self.blockSignals(True)
        self.setRowCount(0)
        for i, item in enumerate(items or []):
            row = self.rowCount()
            self.insertRow(row)
            self.setItem(row, 0, QTableWidgetItem(str(item.get('sno', i + 1))))
            self.setItem(row, 1, QTableWidgetItem(str(item.get('description', ''))))
            self.setItem(row, 2, QTableWidgetItem(str(item.get('qty', 1))))
            try:
                rate_val = float(item.get('rate', 0))
            except (TypeError, ValueError):
                rate_val = 0.0
            self.setItem(row, 3, QTableWidgetItem(f"{rate_val:.2f}"))
            cgst_rate = item.get('cgst_rate', '9%')
            sgst_rate = item.get('sgst_rate', '9%')
            try:
                total_gst = float(str(cgst_rate).replace('%', '')) + float(str(sgst_rate).replace('%', ''))
            except (TypeError, ValueError):
                total_gst = 18
            self.setItem(row, 4, QTableWidgetItem(f"{total_gst:.0f}%"))
        if self.rowCount() == 0:
            self.insertRow(0)
            self.setItem(0, 0, QTableWidgetItem("1"))
            self.setItem(0, 1, QTableWidgetItem("New Item"))
            self.setItem(0, 2, QTableWidgetItem("1"))
            self.setItem(0, 3, QTableWidgetItem("0.00"))
            self.setItem(0, 4, QTableWidgetItem("18%"))
        self.blockSignals(False)
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
        left_panel.setMinimumWidth(420)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(24, 20, 24, 20)
        left_layout.setSpacing(16)
        
        # Header - LARGER FONT
        header = QLabel("New Challan")
        header.setStyleSheet("font-size: 22px; font-weight: 700; color: #0f172a; padding-bottom: 8px;")
        left_layout.addWidget(header)
        
        # Scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(16)
        
        # Company Selection - LARGER FONT
        company_group = QGroupBox("Company Details")
        company_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding-top: 14px;
                margin-top: 8px;
                font-weight: 600;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
            }
        """)
        company_layout = QVBoxLayout(company_group)
        company_layout.setSpacing(10)
        
        company_row = QHBoxLayout()
        company_row.setSpacing(8)
        
        self.company_combo = QComboBox()
        self.company_combo.setView(QListView())
        self.company_combo.setMinimumWidth(180)
        self.company_combo.setStyleSheet("font-size: 14px; padding: 8px 12px;")
        self.company_combo.currentIndexChanged.connect(self.on_company_selected)
        company_row.addWidget(self.company_combo, 1)
        
        # New Company button
        new_company_btn = QPushButton("+ New")
        new_company_btn.setStyleSheet("""
            QPushButton {
                background: #1a73e8;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 18px;
            }
            QPushButton:hover {
                background: #1557b0;
            }
        """)
        new_company_btn.clicked.connect(self.open_company_manager)
        company_row.addWidget(new_company_btn)
        
        company_layout.addLayout(company_row)
        
        # Company info display - LARGER FONT
        self.company_info = QLabel("No company selected")
        self.company_info.setWordWrap(True)
        self.company_info.setStyleSheet("color: #64748b; font-size: 13px; padding: 4px 0;")
        company_layout.addWidget(self.company_info)
        
        scroll_layout.addWidget(company_group)
        
        # ===== Vehicle Number Input (Editable per challan) =====
        vehicle_group = QGroupBox("Vehicle Details")
        vehicle_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding-top: 14px;
                margin-top: 8px;
                font-weight: 600;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
            }
        """)
        vehicle_layout = QVBoxLayout(vehicle_group)
        vehicle_layout.setSpacing(8)

        VEHICLE_INPUT_STYLE = """
            QLineEdit {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 15px;
                font-weight: 500;
                color: #0f172a;
            }
            QLineEdit:focus {
                border-color: #1a73e8;
            }
        """

        challan_vehicle_label = QLabel("Challan Vehicle No.")
        challan_vehicle_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748b;")
        vehicle_layout.addWidget(challan_vehicle_label)

        self.challan_vehicle_input = QLineEdit()
        self.challan_vehicle_input.setPlaceholderText("Enter vehicle number (e.g., UP-14-BT-9999)")
        self.challan_vehicle_input.setStyleSheet(VEHICLE_INPUT_STYLE)
        self.challan_vehicle_input.textChanged.connect(self.on_challan_vehicle_changed)
        vehicle_layout.addWidget(self.challan_vehicle_input)

        self.same_vehicle_checkbox = QCheckBox("Use same vehicle number for the Bill")
        self.same_vehicle_checkbox.setChecked(False)
        self.same_vehicle_checkbox.setStyleSheet("font-size: 12px; color: #64748b;")
        self.same_vehicle_checkbox.toggled.connect(self.on_same_vehicle_toggled)
        vehicle_layout.addWidget(self.same_vehicle_checkbox)

        bill_vehicle_label = QLabel("Bill Vehicle No.")
        bill_vehicle_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748b;")
        vehicle_layout.addWidget(bill_vehicle_label)

        self.bill_vehicle_input = QLineEdit()
        self.bill_vehicle_input.setPlaceholderText("Enter vehicle number (e.g., UP-14-BT-9999)")
        self.bill_vehicle_input.setStyleSheet(VEHICLE_INPUT_STYLE)
        self.bill_vehicle_input.setEnabled(False)  # linked to challan vehicle by default
        self.bill_vehicle_input.textChanged.connect(self.trigger_preview_update)
        vehicle_layout.addWidget(self.bill_vehicle_input)

        # Kept for backward compatibility with any code that still expects a
        # single combined vehicle_input.
        self.vehicle_input = self.challan_vehicle_input

        scroll_layout.addWidget(vehicle_group)

        # ===== Challan Number Input =====
        challan_number_group = QGroupBox("Challan Details")
        challan_number_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding-top: 14px;
                margin-top: 8px;
                font-weight: 600;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
            }
        """)
        challan_number_layout = QVBoxLayout(challan_number_group)
        challan_number_layout.setSpacing(8)

        challan_number_label = QLabel("Challan Number")
        challan_number_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748b;")
        challan_number_layout.addWidget(challan_number_label)

        self.challan_number_input = QLineEdit()
        self.challan_number_input.setPlaceholderText("Leave blank for automatic number")
        self.challan_number_input.setStyleSheet(VEHICLE_INPUT_STYLE)
        self.challan_number_input.textChanged.connect(self.trigger_preview_update)
        challan_number_layout.addWidget(self.challan_number_input)

        scroll_layout.addWidget(challan_number_group)
        
        # ===== Date Field =====
        date_group = QGroupBox("Date")
        date_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding-top: 14px;
                margin-top: 8px;
                font-weight: 600;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
            }
        """)
        date_layout = QVBoxLayout(date_group)
        date_layout.setSpacing(8)

        date_label = QLabel("Challan Date (DD-MM-YYYY)")
        date_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748b;")
        date_layout.addWidget(date_label)

        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText(f"Default: {datetime.now().strftime('%d-%m-%Y')}")
        self.date_input.setStyleSheet(VEHICLE_INPUT_STYLE)
        self.date_input.textChanged.connect(self.trigger_preview_update)
        date_layout.addWidget(self.date_input)

        scroll_layout.addWidget(date_group)
        
        # Items Table - LARGER FONT
        items_group = QGroupBox("Items / Services")
        items_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding-top: 14px;
                margin-top: 8px;
                font-weight: 600;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
            }
        """)
        items_layout = QVBoxLayout(items_group)
        items_layout.setSpacing(8)
        
        # Use custom items table
        self.items_table = ItemsTableWidget()
        self.items_table.data_changed.connect(self.on_item_changed)
        items_layout.addWidget(self.items_table)
        
        items_btn_layout = QHBoxLayout()
        items_btn_layout.setSpacing(8)
        add_btn = QPushButton("+ Add Row")
        add_btn.setStyleSheet("background: #1a73e8; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: 600; font-size: 13px;")
        add_btn.clicked.connect(self.items_table.add_row)
        items_btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("− Remove")
        remove_btn.setStyleSheet("background: #f1f5f9; border: none; border-radius: 6px; padding: 8px 16px; font-weight: 500; font-size: 13px;")
        remove_btn.clicked.connect(self.items_table.remove_row)
        items_btn_layout.addWidget(remove_btn)
        
        items_btn_layout.addStretch()
        items_layout.addLayout(items_btn_layout)
        
        scroll_layout.addWidget(items_group)
        
        # Totals - More compact but LARGER FONT
        totals_group = QGroupBox("Totals")
        totals_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding-top: 14px;
                margin-top: 8px;
                font-weight: 600;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
            }
        """)
        totals_layout = QGridLayout(totals_group)
        totals_layout.setSpacing(6)
        
        self.lbl_subtotal = QLabel("Rs 0.00")
        self.lbl_subtotal.setStyleSheet("font-weight: 600; font-size: 15px;")
        totals_layout.addWidget(QLabel("Subtotal:"), 0, 0)
        totals_layout.addWidget(self.lbl_subtotal, 0, 1)
        
        self.lbl_tax = QLabel("Rs 0.00")
        self.lbl_tax.setStyleSheet("font-weight: 600; font-size: 15px;")
        totals_layout.addWidget(QLabel("GST:"), 0, 2)
        totals_layout.addWidget(self.lbl_tax, 0, 3)
        
        self.lbl_grand = QLabel("Rs 0.00")
        self.lbl_grand.setStyleSheet("font-size: 20px; font-weight: 700; color: #1a73e8;")
        totals_layout.addWidget(QLabel("Grand Total:"), 1, 0)
        totals_layout.addWidget(self.lbl_grand, 1, 1)
        
        self.lbl_words = QLabel("Zero Rupees Only")
        self.lbl_words.setStyleSheet("font-style: italic; color: #64748b; font-size: 14px;")
        totals_layout.addWidget(QLabel("Amount in Words:"), 2, 0)
        totals_layout.addWidget(self.lbl_words, 2, 1, 1, 3)
        
        scroll_layout.addWidget(totals_group)
        
        # Generate button - LARGER
        generate_btn = QPushButton("Generate Challan")
        generate_btn.setStyleSheet("""
            QPushButton {
                background: #1a73e8;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 14px 24px;
                font-size: 18px;
                font-weight: 700;
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
        self.splitter.setSizes([400, 650])  # 35% / 65% split
        
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
        
    def on_challan_vehicle_changed(self, text):
        if self.same_vehicle_checkbox.isChecked():
            self.bill_vehicle_input.blockSignals(True)
            self.bill_vehicle_input.setText(text)
            self.bill_vehicle_input.blockSignals(False)
        self.trigger_preview_update()

    def on_same_vehicle_toggled(self, checked):
        self.bill_vehicle_input.setEnabled(not checked)
        if checked:
            self.bill_vehicle_input.setText(self.challan_vehicle_input.text())
        self.trigger_preview_update()

    def trigger_preview_update(self):
        self.preview_timer.stop()
        self.preview_timer.start(500)  # Faster preview updates
        
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
            
        # Get vehicle numbers from the editable input fields
        challan_vehicle_no = self.challan_vehicle_input.text().strip() or "UP-14-BT-9999"
        bill_vehicle_no = self.bill_vehicle_input.text().strip() or challan_vehicle_no
        
        # Get date from input field or use today
        date_str = self.date_input.text().strip() or datetime.now().strftime('%d-%m-%Y')

        # Use the entered challan number, or generate a preview default
        challan_number = self.challan_number_input.text().strip() or f"CH-{datetime.now().strftime('%Y%m%d')}-001"
            
        payload = {
            "copy_type": "Original Copy",
            "company_name": "NEXTUP ROBOTICS PVT LTD",
            "supplier_gstin": "09AAHCN8459L1ZM",
            "supplier_state": "UTTAR PRADESH",
            "supplier_state_code": "09",
            "date": date_str,
            "challanNumber": challan_number,
            "items": items,
            "studentName": self.selected_company.get('name', ''),
            "customer_address": self.selected_company.get('customer_address', ''),
            "customer_gstin": self.selected_company.get('customer_gstin', ''),
            "customer_state": self.selected_company.get('customer_state', ''),
            "customer_state_code": self.selected_company.get('customer_state_code', ''),
            "challan_vehicle_no": challan_vehicle_no,
            "bill_vehicle_no": bill_vehicle_no,
        }
        
        generator = get_generator()
        try:
            # Higher DPI for better quality preview
            png_bytes = generator.render_preview_png(payload, dpi=150)
            self.preview_widget.update_preview(png_bytes)
        except Exception as e:
            print("Preview error:", e)
            self.preview_widget.update_preview(None)
            
    def reset_defaults(self):
        self.items_table.blockSignals(True)
        self.items_table.setRowCount(1)
        self.items_table.setItem(0, 0, QTableWidgetItem("1"))
        self.items_table.setItem(0, 1, QTableWidgetItem("New Item"))
        self.items_table.setItem(0, 2, QTableWidgetItem("1"))   # Qty
        self.items_table.setItem(0, 3, QTableWidgetItem("0.00")) # Rate
        self.items_table.setItem(0, 4, QTableWidgetItem("18%"))  # GST
        self.items_table.blockSignals(False)
        self.same_vehicle_checkbox.setChecked(True)
        self.challan_vehicle_input.clear()
        self.bill_vehicle_input.clear()
        self.challan_number_input.clear()
        self.date_input.clear()  # Reset date field to use default (today)
        self.on_item_changed()
        
    def generate_challan(self):
        if not self.selected_company:
            self.main_window.toast.show_message("Please select a company first!", "error")
            return
            
        items = self.items_table.get_items_data()
        if not items or all(it.get('rate', 0) == 0 for it in items):
            self.main_window.toast.show_message("Add at least one item with a rate!", "error")
            return
            
        # Get vehicle numbers from editable inputs
        challan_vehicle_no = self.challan_vehicle_input.text().strip() or "UP-14-BT-9999"
        bill_vehicle_no = self.bill_vehicle_input.text().strip() or challan_vehicle_no
        
        # Get date from input field or use today
        date_str = self.date_input.text().strip() or datetime.now().strftime('%d-%m-%Y')

        # Use the entered challan number, or generate one automatically
        challan_number = self.challan_number_input.text().strip() or f"CH-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
            
        payload = {
            "copy_type": "Original Copy",
            "company_name": "NEXTUP ROBOTICS PVT LTD",
            "supplier_gstin": "09AAHCN8459L1ZM",
            "supplier_state": "UTTAR PRADESH",
            "supplier_state_code": "09",
            "date": date_str,
            "challanNumber": challan_number,
            "items": items,
            "studentName": self.selected_company.get('name', ''),
            "customer_address": self.selected_company.get('customer_address', ''),
            "customer_gstin": self.selected_company.get('customer_gstin', ''),
            "customer_state": self.selected_company.get('customer_state', ''),
            "customer_state_code": self.selected_company.get('customer_state_code', ''),
            "challan_vehicle_no": challan_vehicle_no,
            "bill_vehicle_no": bill_vehicle_no,
        }
        
        generator = get_generator()
        
        # Save PDFs locally
        saved_paths = generator.save_dual_pdfs(payload)
        
        # 🔥 IMPORTANT: Submit to backend API to save to MongoDB
        try:
            import requests
            response = requests.post(
                f"{API_BASE}/submit",
                json=payload,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.main_window.toast.show_message("✅ Bill and Challan generated and saved to database!", "success")
                    # Refresh search panel
                    self.main_window.refresh_search_tab()
                else:
                    self.main_window.toast.show_message("⚠️ Generated but failed to save to database.", "warning")
            else:
                self.main_window.toast.show_message(f"⚠️ Database save failed: {response.status_code}", "warning")
        except requests.exceptions.ConnectionError:
            print("Backend server not running!")
            self.main_window.toast.show_message("⚠️ Backend server not running. Data not saved to database.", "warning")
        except Exception as e:
            print(f"Error submitting to database: {e}")
            self.main_window.toast.show_message("⚠️ Database save failed. Check backend server.", "warning")
        
        # Open the generated PDFs
        QDesktopServices.openUrl(QUrl.fromLocalFile(saved_paths['bill']))
        QDesktopServices.openUrl(QUrl.fromLocalFile(saved_paths['challan']))


# ======================== SEARCH CHALLAN TAB ========================

class SearchTab(QWidget):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.current_results = []
        self.setup_ui()
        
        # Auto-refresh timer - every 5 seconds
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_recent)

        # Debounce timer for live search-as-you-type (avoids firing a
        # request on every keystroke)
        self.search_debounce_timer = QTimer()
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.timeout.connect(self.search)
        
        self.load_recent()

    def on_search_text_changed(self):
        self.search_debounce_timer.stop()
        self.search_debounce_timer.start(400)
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        header = QLabel("Search Challans")
        header.setStyleSheet("font-size: 24px; font-weight: 700; color: #0f172a;")
        layout.addWidget(header)
        
        # Search bar with filters - LARGER FONTS
        search_container = QFrame()
        search_container.setStyleSheet("""
            QFrame {
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        search_layout = QVBoxLayout(search_container)
        search_layout.setSpacing(12)
        
        # First row: Search type + search input
        row1 = QHBoxLayout()
        row1.setSpacing(12)
        
        label = QLabel("Search by:")
        label.setStyleSheet("font-size: 14px; font-weight: 600;")
        row1.addWidget(label)
        
        self.search_type = QComboBox()
        self.search_type.addItems([
            "Challan Number",
            "Customer Name",
            "Date Range",
            "Amount Range",
            "GSTIN",
            "Vehicle No"
        ])
        self.search_type.setStyleSheet("""
            QComboBox {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 8px 14px;
                min-width: 180px;
                font-size: 14px;
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
                padding: 8px 14px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #1a73e8;
            }
        """)
        self.search_input.returnPressed.connect(self.search)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        row1.addWidget(self.search_input, 1)
        
        search_btn = QPushButton("Search")
        search_btn.setStyleSheet("""
            QPushButton {
                background: #1a73e8;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: 600;
                font-size: 14px;
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
                padding: 8px 20px;
                font-weight: 500;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #e2e8f0;
            }
        """)
        clear_btn.clicked.connect(self.clear_search)
        row1.addWidget(clear_btn)
        
        # Refresh button - LARGER
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(42, 42)
        refresh_btn.setToolTip("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 20px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #e2e8f0;
            }
        """)
        refresh_btn.clicked.connect(self.load_recent)
        row1.addWidget(refresh_btn)
        
        search_layout.addLayout(row1)
        
        # Second row: Dynamic filter widgets
        self.filter_widget = QWidget()
        self.filter_layout = QHBoxLayout(self.filter_widget)
        self.filter_layout.setContentsMargins(0, 10, 0, 0)
        self.filter_layout.setSpacing(12)
        
        # Date range widgets (hidden by default)
        self.date_widget = QWidget()
        date_layout = QHBoxLayout(self.date_widget)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setSpacing(12)
        
        date_label = QLabel("From:")
        date_label.setStyleSheet("font-size: 14px; font-weight: 500;")
        date_layout.addWidget(date_label)
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setStyleSheet("border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 10px; font-size: 14px;")
        date_layout.addWidget(self.date_from)
        
        date_label2 = QLabel("To:")
        date_label2.setStyleSheet("font-size: 14px; font-weight: 500;")
        date_layout.addWidget(date_label2)
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setStyleSheet("border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 10px; font-size: 14px;")
        date_layout.addWidget(self.date_to)
        
        date_layout.addStretch()
        self.date_widget.hide()
        self.filter_layout.addWidget(self.date_widget)
        
        # Amount range widgets (hidden by default)
        self.amount_widget = QWidget()
        amount_layout = QHBoxLayout(self.amount_widget)
        amount_layout.setContentsMargins(0, 0, 0, 0)
        amount_layout.setSpacing(12)
        
        amount_label = QLabel("Min:")
        amount_label.setStyleSheet("font-size: 14px; font-weight: 500;")
        amount_layout.addWidget(amount_label)
        self.amount_min = QDoubleSpinBox()
        self.amount_min.setRange(0, 9999999)
        self.amount_min.setPrefix("Rs ")
        self.amount_min.setStyleSheet("border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 10px; font-size: 14px;")
        amount_layout.addWidget(self.amount_min)
        
        amount_label2 = QLabel("Max:")
        amount_label2.setStyleSheet("font-size: 14px; font-weight: 500;")
        amount_layout.addWidget(amount_label2)
        self.amount_max = QDoubleSpinBox()
        self.amount_max.setRange(0, 9999999)
        self.amount_max.setPrefix("Rs ")
        self.amount_max.setValue(999999)
        self.amount_max.setStyleSheet("border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 10px; font-size: 14px;")
        amount_layout.addWidget(self.amount_max)
        
        amount_layout.addStretch()
        self.amount_widget.hide()
        self.filter_layout.addWidget(self.amount_widget)
        
        # Quick filters - LARGER
        quick_label = QLabel("Quick:")
        quick_label.setStyleSheet("font-weight: 600; color: #64748b; font-size: 14px;")
        self.filter_layout.addWidget(quick_label)
        
        today_btn = QPushButton("Today")
        today_btn.setStyleSheet("background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 16px; font-size: 14px;")
        today_btn.clicked.connect(lambda: self.set_date_range(0))
        self.filter_layout.addWidget(today_btn)
        
        week_btn = QPushButton("This Week")
        week_btn.setStyleSheet("background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 16px; font-size: 14px;")
        week_btn.clicked.connect(lambda: self.set_date_range(7))
        self.filter_layout.addWidget(week_btn)
        
        month_btn = QPushButton("This Month")
        month_btn.setStyleSheet("background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 16px; font-size: 14px;")
        month_btn.clicked.connect(lambda: self.set_date_range(30))
        self.filter_layout.addWidget(month_btn)
        
        self.filter_layout.addStretch()
        search_layout.addWidget(self.filter_widget)
        
        layout.addWidget(search_container)
        
        # Results table - LARGER FONT with better row height
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "Challan No", "Customer", "Challan Vehicle", "Bill Vehicle", "Date", "Amount (Rs)", "Actions"
        ])
        self.results_table.setColumnWidth(6, 560)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Set minimum row height for better button visibility
        self.results_table.verticalHeader().setDefaultSectionSize(55)
        
        self.results_table.setStyleSheet("""
            QTableWidget {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                font-size: 14px;
            }
            QTableWidget::item {
                padding: 10px 12px;
            }
            QHeaderView::section {
                background: #f8fafc;
                font-weight: 600;
                padding: 10px;
                font-size: 13px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
            }
        """)
        layout.addWidget(self.results_table)
        
        # Results count - LARGER
        self.results_count = QLabel("Showing 0 results")
        self.results_count.setStyleSheet("color: #64748b; font-size: 15px; padding: 4px 0;")
        layout.addWidget(self.results_count)
        
    def on_search_type_changed(self, index):
        # Show/hide appropriate filter widgets
        search_type = self.search_type.currentText()
        
        self.date_widget.hide()
        self.amount_widget.hide()
        self.search_input.setEnabled(True)
        self.search_input.setPlaceholderText("Enter search term...")
        
        if search_type == "Date Range":
            self.date_widget.show()
            self.search_input.setPlaceholderText("Select date range using the calendar or quick filters")
            self.search_input.setEnabled(False)
        elif search_type == "Amount Range":
            self.amount_widget.show()
            self.search_input.setPlaceholderText("Enter min and max amount")
            self.search_input.setEnabled(False)
        elif search_type == "Challan Number":
            self.search_input.setPlaceholderText("Enter challan number...")
            self.search_input.setEnabled(True)
        elif search_type == "Customer Name":
            self.search_input.setPlaceholderText("Enter customer name...")
            self.search_input.setEnabled(True)
        elif search_type == "GSTIN":
            self.search_input.setPlaceholderText("Enter GSTIN...")
            self.search_input.setEnabled(True)
        elif search_type == "Vehicle No":
            self.search_input.setPlaceholderText("Enter vehicle number...")
            self.search_input.setEnabled(True)
            
    def set_date_range(self, days):
        self.search_type.setCurrentText("Date Range")
        self.date_from.setDate(QDate.currentDate().addDays(-days))
        self.date_to.setDate(QDate.currentDate())
        
    def clear_search(self):
        self.search_input.clear()
        self.search_input.setEnabled(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_to.setDate(QDate.currentDate())
        self.amount_min.setValue(0)
        self.amount_max.setValue(999999)
        self.load_recent()
        
    def load_recent(self):
        """Load recent submissions from MongoDB"""
        try:
            import requests
            response = requests.get(
                f"{API_BASE}/submissions/recent?limit=50",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    submissions = data.get('submissions', [])
                    self.display_submissions(submissions)
                    return
        except Exception as e:
            print(f"Error loading recent submissions: {e}")
        
        # Fallback to local files if API fails
        generator = get_generator()
        gen_dir = os.path.join(generator.base_dir, 'generated')
        if os.path.exists(gen_dir):
            files = sorted([f for f in os.listdir(gen_dir) if f.endswith('.pdf')], reverse=True)
            self.display_results(files[:50])


    def search(self):
        """Search submissions using MongoDB"""
        search_type = self.search_type.currentText()
        query = self.search_input.text().strip()
        
        if not query and search_type not in ["Date Range", "Amount Range"]:
            self.load_recent()
            return
        
        try:
            import requests
            payload = {
                "search_type": search_type,
                "query": query
            }
            
            # Add date range if applicable
            if search_type == "Date Range":
                payload["from_date"] = self.date_from.date().toString("yyyy-MM-dd")
                payload["to_date"] = self.date_to.date().toString("yyyy-MM-dd")
            elif search_type == "Amount Range":
                payload["min_amount"] = self.amount_min.value()
                payload["max_amount"] = self.amount_max.value()
            
            response = requests.post(
                f"{API_BASE}/submissions/search",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    submissions = data.get('submissions', [])
                    self.display_submissions(submissions)
                    return
        except Exception as e:
            print(f"Error searching: {e}")
        
        # Fallback to local file search
        self.search_local(search_type, query)
    
    def search_local(self, search_type, query):
        """Fallback search using local files"""
        generator = get_generator()
        gen_dir = os.path.join(generator.base_dir, 'generated')
        if not os.path.exists(gen_dir):
            self.results_table.setRowCount(0)
            self.results_count.setText("No results found")
            return
            
        files = [f for f in os.listdir(gen_dir) if f.endswith('.pdf')]
        
        if query:
            filtered_files = [f for f in files if query.lower() in f.lower()]
        else:
            filtered_files = files
            
        self.display_results(filtered_files[:50])
    
    def display_submissions(self, submissions):
        """Display submissions from MongoDB with THICKER Bill and Challan buttons"""
        self.results_table.setRowCount(len(submissions))
        self.results_count.setText(f"Showing {len(submissions)} results")
        
        generator = get_generator()
        
        for idx, sub in enumerate(submissions):
            # Ensure we have valid data
            challan_no = sub.get('challanNumber', 'N/A')
            customer_name = sub.get('studentName', 'Unknown')
            legacy_vehicle = sub.get('vehicle_no', 'N/A')
            challan_vehicle_no = sub.get('challan_vehicle_no') or legacy_vehicle
            bill_vehicle_no = sub.get('bill_vehicle_no') or legacy_vehicle
            date_val = sub.get('date', 'N/A')
            amount = sub.get('amount', '0.00')
            
            # Format amount
            try:
                amount_str = f"Rs {float(amount):.2f}"
            except:
                amount_str = f"Rs 0.00"
            
            # Set table items - larger font
            self.results_table.setItem(idx, 0, QTableWidgetItem(str(challan_no)))
            self.results_table.setItem(idx, 1, QTableWidgetItem(str(customer_name)))
            self.results_table.setItem(idx, 2, QTableWidgetItem(str(challan_vehicle_no)))
            self.results_table.setItem(idx, 3, QTableWidgetItem(str(bill_vehicle_no)))
            self.results_table.setItem(idx, 4, QTableWidgetItem(str(date_val)))
            self.results_table.setItem(idx, 5, QTableWidgetItem(amount_str))
            
            # Actions widget with THICKER buttons
            btn_widget = QWidget()
            btn_widget.setStyleSheet("background: transparent;")
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(8, 6, 8, 6)
            btn_layout.setSpacing(10)
            
            # Get file paths
            bill_file = sub.get('billFilename', '')
            challan_file = sub.get('challanFilename', '')
            
            bill_path = os.path.join(generator.base_dir, 'generated', bill_file)
            challan_path = os.path.join(generator.base_dir, 'generated', challan_file)
            
            # Bill button - THICKER and LARGER
            bill_btn = QPushButton("📄 Bill")
            bill_btn.setMinimumHeight(36)
            bill_btn.setMinimumWidth(80)
            bill_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1a73e8;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #1557b0;
                }
                QPushButton:pressed {
                    background-color: #0d47a1;
                }
                QPushButton:disabled {
                    background-color: #94a3b8;
                    color: #ffffff;
                }
            """)
            if os.path.exists(bill_path):
                bill_btn.clicked.connect(lambda _, p=bill_path: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
            else:
                bill_btn.setEnabled(False)
                bill_btn.setToolTip("Bill file not found")
            
            btn_layout.addWidget(bill_btn)
            
            # Challan button - THICKER and LARGER
            challan_btn = QPushButton("📋 Challan")
            challan_btn.setMinimumHeight(36)
            challan_btn.setMinimumWidth(90)
            challan_btn.setStyleSheet("""
                QPushButton {
                    background-color: #10b981;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #059669;
                }
                QPushButton:pressed {
                    background-color: #047857;
                }
                QPushButton:disabled {
                    background-color: #94a3b8;
                    color: #ffffff;
                }
            """)
            if os.path.exists(challan_path):
                challan_btn.clicked.connect(lambda _, p=challan_path: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
            else:
                challan_btn.setEnabled(False)
                challan_btn.setToolTip("Challan file not found")
            
            btn_layout.addWidget(challan_btn)

            # Edit button - opens a dialog pre-filled with every saved field
            # (company details, both vehicle numbers, items, etc.) so fixing
            # a mistake - like an incorrect vehicle number - regenerates both
            # the Bill and the Challan with the correction applied.
            edit_btn = QPushButton("✏️ Edit")
            edit_btn.setMinimumHeight(36)
            edit_btn.setMinimumWidth(80)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f59e0b;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #d97706;
                }
                QPushButton:pressed {
                    background-color: #b45309;
                }
            """)
            edit_btn.clicked.connect(lambda _, s=sub: self.open_edit_dialog(s))
            btn_layout.addWidget(edit_btn)
            
            btn_layout.addStretch()
            self.results_table.setCellWidget(idx, 6, btn_widget)

    def open_edit_dialog(self, submission: Dict):
        """Open the pre-filled edit dialog for an existing submission"""
        dialog = EditSubmissionDialog(submission, self)
        if dialog.exec():
            # Saved successfully - refresh the results so the table reflects the edit
            self.load_recent()
    
    def display_results(self, files):
        """Fallback display using local files with THICKER Bill and Challan buttons"""
        self.results_table.setRowCount(len(files))
        self.results_count.setText(f"Showing {len(files)} results")
        
        generator = get_generator()
        
        for idx, f in enumerate(files[:100]):
            parts = f.replace('.pdf', '').split('_')
            challan_no = parts[1] if len(parts) > 1 else 'N/A'
            
            # Extract customer name from filename
            customer_name = "Unknown"
            if len(parts) >= 3:
                name_candidate = parts[2] if len(parts) > 2 else ""
                if len(parts) > 3:
                    for i, part in enumerate(parts):
                        if part.isdigit() and len(part) == 8:  # YYYYMMDD
                            name_candidate = "_".join(parts[2:i])
                            break
                    else:
                        name_candidate = "_".join(parts[2:])
                customer_name = name_candidate.replace('_', ' ') if name_candidate else "Unknown"
            
            self.results_table.setItem(idx, 0, QTableWidgetItem(challan_no))
            self.results_table.setItem(idx, 1, QTableWidgetItem(customer_name))
            self.results_table.setItem(idx, 2, QTableWidgetItem("N/A"))
            self.results_table.setItem(idx, 3, QTableWidgetItem("N/A"))
            
            file_path = os.path.join(generator.base_dir, 'generated', f)
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            self.results_table.setItem(idx, 4, QTableWidgetItem(mod_time.strftime("%Y-%m-%d %H:%M")))
            
            self.results_table.setItem(idx, 5, QTableWidgetItem("Rs 0.00"))
            self.results_table.setItem(idx, 6, QTableWidgetItem("Generated"))
            
            # Actions widget with THICKER buttons
            btn_widget = QWidget()
            btn_widget.setStyleSheet("background: transparent;")
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(8, 6, 8, 6)
            btn_layout.setSpacing(10)
            
            # Check if it's a Bill or Challan file
            is_bill = f.startswith('Bill_')
            is_challan = f.startswith('Challan_')
            
            # Bill button - THICKER and LARGER
            bill_btn = QPushButton("📄 Bill")
            bill_btn.setMinimumHeight(36)
            bill_btn.setMinimumWidth(80)
            bill_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1a73e8;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #1557b0;
                }
                QPushButton:pressed {
                    background-color: #0d47a1;
                }
                QPushButton:disabled {
                    background-color: #94a3b8;
                    color: #ffffff;
                }
            """)
            if is_bill or is_challan:
                bill_btn.clicked.connect(lambda _, p=file_path: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
            else:
                bill_btn.setEnabled(False)
            
            btn_layout.addWidget(bill_btn)
            
            # Challan button - THICKER and LARGER
            challan_btn = QPushButton("📋 Challan")
            challan_btn.setMinimumHeight(36)
            challan_btn.setMinimumWidth(90)
            challan_btn.setStyleSheet("""
                QPushButton {
                    background-color: #10b981;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #059669;
                }
                QPushButton:pressed {
                    background-color: #047857;
                }
                QPushButton:disabled {
                    background-color: #94a3b8;
                    color: #ffffff;
                }
            """)
            if is_challan or is_bill:
                challan_btn.clicked.connect(lambda _, p=file_path: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
            else:
                challan_btn.setEnabled(False)
            
            btn_layout.addWidget(challan_btn)

            no_edit_btn = QPushButton("✏️ Edit")
            no_edit_btn.setMinimumHeight(36)
            no_edit_btn.setMinimumWidth(80)
            no_edit_btn.setEnabled(False)
            no_edit_btn.setToolTip("Start the backend server to enable editing")
            no_edit_btn.setStyleSheet("background-color: #cbd5e1; color: #ffffff; border: none; border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 600;")
            btn_layout.addWidget(no_edit_btn)
            
            btn_layout.addStretch()
            self.results_table.setCellWidget(idx, 7, btn_widget)


# ======================== EDIT SUBMISSION DIALOG ========================

class EditSubmissionDialog(QDialog):
    """
    Dialog for editing an existing submission. Every field is pre-filled from the
    submission's stored data (customer details, both vehicle numbers, items, etc.)
    so fixing a mistake - such as a vehicle number typed wrong at creation time -
    is a matter of correcting the one field and saving; both the Bill and the
    Challan PDFs are regenerated from the corrected data on save.
    """

    def __init__(self, submission: Dict, parent=None):
        super().__init__(parent)
        self.submission = submission
        self.full_data = submission.get('fullData', {}) or {}
        self.setWindowTitle(f"Edit Submission - {submission.get('challanNumber', '')}")
        self.setMinimumSize(720, 700)
        self.setStyleSheet("background: #ffffff;")
        self.setup_ui()
        self.populate_fields()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        header = QLabel("Edit Submission")
        header.setStyleSheet("font-size: 20px; font-weight: 700; color: #0f172a;")
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        content = QWidget()
        form = QFormLayout(content)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        input_style = "border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 12px; font-size: 14px;"

        self.customer_name_in = QLineEdit()
        self.customer_name_in.setStyleSheet(input_style)
        form.addRow("Customer Name:", self.customer_name_in)

        self.customer_address_in = QLineEdit()
        self.customer_address_in.setStyleSheet(input_style)
        form.addRow("Customer Address:", self.customer_address_in)

        self.customer_gstin_in = QLineEdit()
        self.customer_gstin_in.setStyleSheet(input_style)
        form.addRow("Customer GSTIN:", self.customer_gstin_in)

        self.customer_state_in = QLineEdit()
        self.customer_state_in.setStyleSheet(input_style)
        form.addRow("Customer State:", self.customer_state_in)

        self.customer_code_in = QLineEdit()
        self.customer_code_in.setStyleSheet(input_style)
        form.addRow("Customer State Code:", self.customer_code_in)

        self.challan_no_in = QLineEdit()
        self.challan_no_in.setStyleSheet(input_style)
        form.addRow("Challan Number:", self.challan_no_in)

        self.date_in = QLineEdit()
        self.date_in.setStyleSheet(input_style)
        form.addRow("Date:", self.date_in)

        self.challan_vehicle_in = QLineEdit()
        self.challan_vehicle_in.setStyleSheet(input_style)
        self.challan_vehicle_in.setPlaceholderText("e.g., UP-14-BT-9999")
        form.addRow("Challan Vehicle No:", self.challan_vehicle_in)

        self.bill_vehicle_in = QLineEdit()
        self.bill_vehicle_in.setStyleSheet(input_style)
        self.bill_vehicle_in.setPlaceholderText("e.g., UP-14-BT-9999")
        form.addRow("Bill Vehicle No:", self.bill_vehicle_in)

        same_row = QHBoxLayout()
        self.same_vehicle_btn = QPushButton("Copy Challan Vehicle → Bill Vehicle")
        self.same_vehicle_btn.setStyleSheet("background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 12px; font-size: 12px;")
        self.same_vehicle_btn.clicked.connect(lambda: self.bill_vehicle_in.setText(self.challan_vehicle_in.text()))
        same_row.addWidget(self.same_vehicle_btn)
        same_row.addStretch()
        form.addRow("", same_row)

        items_label = QLabel("Items / Services")
        items_label.setStyleSheet("font-weight: 600; font-size: 14px; margin-top: 8px;")
        form.addRow(items_label)

        self.items_table = ItemsTableWidget()
        self.items_table.setMinimumHeight(160)
        form.addRow(self.items_table)

        items_btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Row")
        add_btn.setStyleSheet("background: #1a73e8; color: white; border: none; border-radius: 6px; padding: 6px 14px; font-size: 12px;")
        add_btn.clicked.connect(self.items_table.add_row)
        items_btn_row.addWidget(add_btn)
        remove_btn = QPushButton("− Remove")
        remove_btn.setStyleSheet("background: #f1f5f9; border: none; border-radius: 6px; padding: 6px 14px; font-size: 12px;")
        remove_btn.clicked.connect(self.items_table.remove_row)
        items_btn_row.addWidget(remove_btn)
        items_btn_row.addStretch()
        form.addRow("", items_btn_row)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background: #f1f5f9; color: #0f172a; border: none; border-radius: 6px; padding: 10px 22px; font-weight: 500; font-size: 14px;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #1a73e8;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 26px;
                font-weight: 700;
                font-size: 14px;
            }
            QPushButton:hover { background: #1557b0; }
        """)
        save_btn.clicked.connect(self.save_changes)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def populate_fields(self):
        sub = self.submission
        fd = self.full_data

        self.customer_name_in.setText(sub.get('studentName', fd.get('studentName', '')))
        self.customer_address_in.setText(fd.get('customer_address', ''))
        self.customer_gstin_in.setText(fd.get('customer_gstin', ''))
        self.customer_state_in.setText(fd.get('customer_state', ''))
        self.customer_code_in.setText(fd.get('customer_state_code', ''))
        self.challan_no_in.setText(sub.get('challanNumber', ''))
        # Convert stored date (YYYY-MM-DD) to display format (DD-MM-YYYY) for editing
        stored_date = sub.get('date', fd.get('date', ''))
        if stored_date and '-' in str(stored_date) and str(stored_date).count('-') == 2:
            parts = str(stored_date).split('-')
            if len(parts[0]) == 4:  # YYYY-MM-DD format
                display_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
            else:  # Already DD-MM-YYYY
                display_date = stored_date
        else:
            display_date = stored_date or datetime.now().strftime('%d-%m-%Y')
        self.date_in.setText(display_date)

        legacy_vehicle = sub.get('vehicle_no', '')
        self.challan_vehicle_in.setText(sub.get('challan_vehicle_no') or legacy_vehicle)
        self.bill_vehicle_in.setText(sub.get('bill_vehicle_no') or legacy_vehicle)

        items = fd.get('items', [])
        self.items_table.load_items_data(items)

    def save_changes(self):
        if not self.customer_name_in.text().strip() and not self.challan_no_in.text().strip():
            QMessageBox.warning(self, "Missing Info", "Customer name or challan number is required.")
            return

        items = self.items_table.get_items_data()
        if not items:
            QMessageBox.warning(self, "Missing Items", "Add at least one item.")
            return

        payload = {
            "studentName": self.customer_name_in.text().strip(),
            "customer_address": self.customer_address_in.text().strip(),
            "customer_gstin": self.customer_gstin_in.text().strip(),
            "customer_state": self.customer_state_in.text().strip(),
            "customer_state_code": self.customer_code_in.text().strip(),
            "challanNumber": self.challan_no_in.text().strip(),
            "date": self.date_in.text().strip(),
            "challan_vehicle_no": self.challan_vehicle_in.text().strip(),
            "bill_vehicle_no": self.bill_vehicle_in.text().strip() or self.challan_vehicle_in.text().strip(),
            "items": items,
            "amount": str(sum(float(item.get('total', 0)) for item in items)),
            "description": "Services",
            "rollNo": self.full_data.get('rollNo', '001'),
            "copy_type": self.full_data.get('copy_type', 'Original Copy'),
            "company_name": self.full_data.get('company_name', 'NEXTUP ROBOTICS PVT LTD'),
            "supplier_gstin": self.full_data.get('supplier_gstin', '09AAHCN8459L1ZM'),
            "supplier_state": self.full_data.get('supplier_state', 'UTTAR PRADESH'),
            "supplier_state_code": self.full_data.get('supplier_state_code', '09'),
        }

        submission_id = self.submission.get('_id')
        try:
            import requests
            response = requests.put(
                f"{API_BASE}/submissions/{submission_id}",
                json=payload,
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    QMessageBox.information(self, "Saved", "Submission updated - Bill and Challan regenerated.")
                    self.accept()
                    return
                else:
                    QMessageBox.critical(self, "Error", data.get('error', 'Failed to update submission.'))
                    return
            else:
                QMessageBox.critical(self, "Error", f"Update failed: {response.status_code} - {response.text}")
                return
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "Backend Not Running", "Could not reach the backend server. Start it and try again.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update submission: {e}")


# ======================== SETTINGS TAB ========================

class SettingsTab(QWidget):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        header = QLabel("Settings")
        header.setStyleSheet("font-size: 24px; font-weight: 700; color: #0f172a;")
        layout.addWidget(header)
        
        # Company management - LARGER
        company_group = QGroupBox("Company Management")
        company_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding-top: 14px;
                margin-top: 8px;
                font-weight: 600;
                font-size: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        company_layout = QVBoxLayout(company_group)
        company_layout.setSpacing(10)
        
        manage_btn = QPushButton("Manage Companies")
        manage_btn.setStyleSheet("background: #1a73e8; color: white; border: none; border-radius: 6px; padding: 12px 24px; font-weight: 600; font-size: 15px;")
        manage_btn.clicked.connect(self.open_company_manager)
        company_layout.addWidget(manage_btn)
        
        layout.addWidget(company_group)
        
        # Defaults - LARGER
        defaults_group = QGroupBox("Default Settings")
        defaults_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding-top: 14px;
                margin-top: 8px;
                font-weight: 600;
                font-size: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        defaults_layout = QFormLayout(defaults_group)
        defaults_layout.setSpacing(12)
        defaults_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.default_gst = QComboBox()
        self.default_gst.addItems(["5%", "12%", "18%", "28%"])
        self.default_gst.setCurrentText("18%")
        self.default_gst.setStyleSheet("font-size: 14px; padding: 6px 12px;")
        defaults_layout.addRow("Default GST Rate:", self.default_gst)
        
        self.default_hsn = QLineEdit("84795000")
        self.default_hsn.setStyleSheet("font-size: 14px; padding: 8px 12px;")
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
        self.setFixedHeight(64)
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(8)
        
        # App logo/title - LARGER
        app_title = QLabel("Challan Generator")
        app_title.setStyleSheet("""
            QLabel {
                font-size: 22px;
                font-weight: 700;
                color: #1a73e8;
                padding: 0 20px 0 0;
            }
        """)
        layout.addWidget(app_title)
        
        layout.addStretch()
        
        # Navigation buttons - LARGER
        nav_style = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 16px;
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
                border-bottom: 2px solid #e2e8f0;
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
        self.setMinimumSize(1300, 850)
        
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
        
    def refresh_search_tab(self):
        """Refresh the search tab when new challan is generated"""
        self.search_tab.load_recent()
        
    def apply_theme(self):
        # Set larger default font for the entire application
        font = QFont("Inter", 12)
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        QApplication.setFont(font)


# ======================== MESSAGE TOAST ========================

class MessageToast(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        self.label = QLabel()
        self.label.setStyleSheet("color: white; font-size: 18px; font-weight: 600;")
        layout.addWidget(self.label)
        
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def show_message(self, text: str, msg_type: str = "success"):
        bg = "#10b981" if msg_type == "success" else "#ef4444" if msg_type == "error" else "#1a73e8"
        self.label.setText(text)
        self.setStyleSheet(f"QWidget {{ background-color: {bg}; border-radius: 10px; }}")
        
        if self.parent():
            geo = self.parent().geometry()
            self.move(geo.x() + geo.width() - 380, geo.y() + geo.height() - 100)
            
        self.show()
        self.timer.start(4000)


# ======================== GET GLOBAL STYLESHEET ========================

def get_global_stylesheet() -> str:
    return """
        QMainWindow {
            background: #f8fafc;
        }
        QWidget {
            color: #0f172a;
            font-family: "Inter", "Segoe UI", sans-serif;
            font-size: 14px;
        }

        /* Input Controls - LARGER FONT */
        QLineEdit, QDateEdit, QSpinBox, QDoubleSpinBox {
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 14px;
            selection-background-color: #1a73e8;
            selection-color: #ffffff;
        }

        /* --- QCOMBOBOX OVERRIDE --- */
        QComboBox {
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 8px 14px;
            font-size: 14px;
        }
        QComboBox QListView {
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            padding: 4px;
            outline: 0px;
            font-size: 14px;
        }
        QComboBox QListView::item {
            background-color: #ffffff;
            color: #0f172a;
            padding: 8px 12px;
            min-height: 30px;
            border-radius: 4px;
            font-size: 14px;
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
            font-size: 14px;
            selection-background-color: #e8f0fe;
            selection-color: #0f172a;
        }
        QTableWidget::item {
            padding: 6px 8px;
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
            padding: 4px 6px;
            margin: 0px;
            font-size: 14px;
            selection-background-color: #1a73e8;
            selection-color: #ffffff;
        }

        /* Table Headers */
        QHeaderView::section {
            background-color: #f8fafc;
            color: #475569;
            padding: 8px;
            border: none;
            border-bottom: 1px solid #e2e8f0;
            font-weight: 600;
            font-size: 13px;
        }

        /* Scrollbars & GroupBoxes */
        QScrollArea {
            border: none;
            background: transparent;
        }
        QScrollBar:vertical {
            border: none;
            background: #f1f5f9;
            width: 8px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background: #cbd5e1;
            min-height: 30px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical:hover {
            background: #94a3b8;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QSplitter::handle {
            background: #e2e8f0;
            width: 3px;
        }
        QSplitter::handle:hover {
            background: #1a73e8;
        }
        QGroupBox {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding-top: 12px;
            margin-top: 6px;
            font-weight: 600;
            font-size: 14px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px;
        }
        QPushButton {
            border: none;
            border-radius: 6px;
            padding: 8px 18px;
            font-weight: 600;
            font-size: 14px;
        }
        
        QLabel {
            font-size: 14px;
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