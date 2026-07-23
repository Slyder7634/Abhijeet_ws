# main.py - Updated version with Settings Menu and Company Management

import sys
import os
import json
import copy
import shutil
from datetime import datetime
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
    QMenuBar, QMenu, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QTimer, QDate, QUrl, pyqtSignal, QRectF, QPointF, QSize
from PyQt6.QtGui import (
    QFont, QColor, QDesktopServices, QPen, QBrush, QPainter, QPixmap, QImage,
    QTransform, QKeySequence, QAction, QIcon, QPainterPath
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from app import get_generator

API_BASE = "http://localhost:5173/api"
A4_WIDTH_PT = 595.27
A4_HEIGHT_PT = 841.89

# ======================== COMPANY DATA MANAGER ========================

class CompanyDataManager:
    """Manages saved company data for quick form filling"""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.companies_file = os.path.join(self.base_dir, 'config', 'companies.json')
        self.companies = []
        self._load_companies()
        
    def _load_companies(self):
        """Load companies from JSON file"""
        try:
            with open(self.companies_file, 'r') as f:
                data = json.load(f)
                self.companies = data.get('companies', [])
        except (FileNotFoundError, json.JSONDecodeError):
            self.companies = []
            self._save_companies()
            
    def _save_companies(self):
        """Save companies to JSON file"""
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
        # Check if company already exists
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
    """Dialog for managing saved company data"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = CompanyDataManager()
        self.setWindowTitle("🏢 Manage Saved Companies")
        self.setMinimumSize(700, 500)
        self.setup_ui()
        self.load_companies()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("Save and Manage Company Data for Quick Form Filling")
        header.setStyleSheet("font-size: 16px; font-weight: 700; color: #1e40af;")
        layout.addWidget(header)
        
        # Form for adding/editing company
        form_group = QGroupBox("Add / Edit Company Data")
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
        self.save_btn = QPushButton("💾 Save Company")
        self.save_btn.setStyleSheet("background: #10b981; color: white; font-weight: 700;")
        self.save_btn.clicked.connect(self.save_company)
        btn_layout.addWidget(self.save_btn)
        
        self.clear_btn = QPushButton("🔄 Clear Form")
        self.clear_btn.clicked.connect(self.clear_form)
        btn_layout.addWidget(self.clear_btn)
        
        btn_layout.addStretch()
        form_layout.addRow(btn_layout)
        
        layout.addWidget(form_group)
        
        # Company list
        list_group = QGroupBox("Saved Companies")
        list_layout = QVBoxLayout(list_group)
        
        self.company_list = QListWidget()
        self.company_list.itemClicked.connect(self.on_company_selected)
        list_layout.addWidget(self.company_list)
        
        list_btn_layout = QHBoxLayout()
        load_btn = QPushButton("📂 Load Selected")
        load_btn.clicked.connect(self.load_selected_company)
        list_btn_layout.addWidget(load_btn)
        
        delete_btn = QPushButton("🗑️ Delete Selected")
        delete_btn.setStyleSheet("color: #dc2626;")
        delete_btn.clicked.connect(self.delete_selected_company)
        list_btn_layout.addWidget(delete_btn)
        
        list_btn_layout.addStretch()
        list_layout.addLayout(list_btn_layout)
        
        layout.addWidget(list_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def load_companies(self):
        self.company_list.clear()
        for company in self.manager.get_all_companies():
            name = company.get('name', 'Unnamed')
            item = QListWidgetItem(f"🏢 {name}")
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
            
        name = item.text().replace("🏢 ", "")
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete company '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.delete_company(name)
            self.load_companies()
            self.clear_form()


# ======================== VISUAL DESIGNER TAB ========================

class VisualDesignerTab(QWidget):
    """Visual Designer Tab with Canvas, Toolbars, Live PDF Preview, & Property Drawer"""

    config_saved = pyqtSignal(dict)

    def __init__(self, main_window: 'MainWindow'):
        super().__init__(main_window)
        self.main_window = main_window
        self.config = {}
        self.selected_element_config = None
        self.zoom_factor = 1.0
        
        self.setup_ui()
        QTimer.singleShot(100, self.load_initial_config)

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Side: Canvas + Controls
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        # Top Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        
        add_text_btn = QPushButton("🔤 Add Text")
        add_text_btn.clicked.connect(lambda: self.add_element('text'))
        toolbar.addWidget(add_text_btn)
        
        add_table_btn = QPushButton("📊 Add Table")
        add_table_btn.clicked.connect(lambda: self.add_element('table'))
        toolbar.addWidget(add_table_btn)
        
        add_rect_btn = QPushButton("🔲 Add Box")
        add_rect_btn.clicked.connect(lambda: self.add_element('rect'))
        toolbar.addWidget(add_rect_btn)
        
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.setStyleSheet("background: #fee2e2; color: #dc2626; border: 1px solid #fca5a5; border-radius: 6px; font-weight: 600;")
        delete_btn.clicked.connect(self.delete_selected_element)
        toolbar.addWidget(delete_btn)
        
        toolbar.addSpacing(10)
        
        load_pdf_btn = QPushButton("📄 Change Template PDF")
        load_pdf_btn.clicked.connect(self.load_background_pdf)
        toolbar.addWidget(load_pdf_btn)
        
        toolbar.addStretch()
        
        self.grid_cb = QCheckBox("Show Grid")
        self.grid_cb.setChecked(True)
        self.grid_cb.toggled.connect(self.toggle_grid)
        toolbar.addWidget(self.grid_cb)
        
        self.snap_cb = QCheckBox("Snap Grid")
        self.snap_cb.setChecked(True)
        self.snap_cb.toggled.connect(self.toggle_snap)
        toolbar.addWidget(self.snap_cb)
        
        left_layout.addLayout(toolbar)
        
        # Canvas Container View
        self.scene = TemplateGraphicsScene(self)
        self.scene.element_selected.connect(self.on_element_selected_from_scene)
        self.scene.element_modified.connect(self.on_element_modified_from_scene)
        
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setStyleSheet("QGraphicsView { border: 1px solid #cbd5e1; background: #f8fafc; border-radius: 8px; }")
        
        left_layout.addWidget(self.view, 1)
        
        # Bottom Zoom & Live Preview Bar
        bottom_bar = QHBoxLayout()
        
        zoom_out_btn = QPushButton("🔍 -")
        zoom_out_btn.clicked.connect(lambda: self.change_zoom(-0.1))
        bottom_bar.addWidget(zoom_out_btn)
        
        self.zoom_lbl = QLabel("100%")
        self.zoom_lbl.setStyleSheet("font-weight: 700; color: #0f172a; min-width: 50px;")
        self.zoom_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_bar.addWidget(self.zoom_lbl)
        
        zoom_in_btn = QPushButton("🔍 +")
        zoom_in_btn.clicked.connect(lambda: self.change_zoom(0.1))
        bottom_bar.addWidget(zoom_in_btn)
        
        fit_page_btn = QPushButton("Fit Page")
        fit_page_btn.clicked.connect(self.fit_page_in_view)
        bottom_bar.addWidget(fit_page_btn)
        
        bottom_bar.addStretch()
        
        preview_btn = QPushButton("👁️ Live PDF Preview")
        preview_btn.setStyleSheet("""
            QPushButton {
                background: #8b5cf6; color: white; border: none;
                border-radius: 6px; padding: 8px 16px; font-weight: 700;
            }
            QPushButton:hover { background: #7c3aed; }
        """)
        preview_btn.clicked.connect(self.show_live_pdf_preview)
        bottom_bar.addWidget(preview_btn)
        
        save_btn = QPushButton("💾 Save Template Config")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #10b981; color: white; border: none;
                border-radius: 6px; padding: 8px 16px; font-weight: 700;
            }
            QPushButton:hover { background: #059669; }
        """)
        save_btn.clicked.connect(self.save_config)
        bottom_bar.addWidget(save_btn)
        
        left_layout.addLayout(bottom_bar)
        splitter.addWidget(left_widget)
        
        props_panel = self.create_property_inspector()
        splitter.addWidget(props_panel)
        
        splitter.setSizes([850, 350])
        main_layout.addWidget(splitter)

    def create_property_inspector(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(300)
        panel.setStyleSheet("background: #ffffff; border-radius: 8px; border: 1px solid #cbd5e1;")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        title = QLabel("⚙️ Property Inspector")
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #1e40af;")
        layout.addWidget(title)
        
        layout.addWidget(QLabel("Select Element:"))
        self.elem_combo = QComboBox()
        self.elem_combo.currentIndexChanged.connect(self.on_elem_combo_changed)
        layout.addWidget(self.elem_combo)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        pos_group = QGroupBox("Position & Geometry (A4 Points)")
        pos_grid = QGridLayout(pos_group)
        
        pos_grid.addWidget(QLabel("X:"), 0, 0)
        self.spin_x = QDoubleSpinBox()
        self.spin_x.setRange(0, 595)
        self.spin_x.valueChanged.connect(lambda v: self.update_elem_prop('x', v))
        pos_grid.addWidget(self.spin_x, 0, 1)
        
        pos_grid.addWidget(QLabel("Y:"), 0, 2)
        self.spin_y = QDoubleSpinBox()
        self.spin_y.setRange(0, 841)
        self.spin_y.valueChanged.connect(lambda v: self.update_elem_prop('y', v))
        pos_grid.addWidget(self.spin_y, 0, 3)
        
        pos_grid.addWidget(QLabel("W:"), 1, 0)
        self.spin_w = QDoubleSpinBox()
        self.spin_w.setRange(5, 595)
        self.spin_w.valueChanged.connect(lambda v: self.update_elem_prop('width', v))
        pos_grid.addWidget(self.spin_w, 1, 1)
        
        pos_grid.addWidget(QLabel("H:"), 1, 2)
        self.spin_h = QDoubleSpinBox()
        self.spin_h.setRange(5, 841)
        self.spin_h.valueChanged.connect(lambda v: self.update_elem_prop('height', v))
        pos_grid.addWidget(self.spin_h, 1, 3)
        
        scroll_layout.addWidget(pos_group)
        
        text_group = QGroupBox("Text & Typography")
        text_layout = QFormLayout(text_group)
        
        self.txt_content = QLineEdit()
        self.txt_content.editingFinished.connect(lambda: self.update_elem_prop('text', self.txt_content.text()))
        text_layout.addRow("Content:", self.txt_content)
        
        self.var_combo = QComboBox()
        self.var_combo.addItems([
            "-- Insert Variable --",
            "{{studentName}}", "{{rollNo}}", "{{amount}}", "{{date}}",
            "{{challanNumber}}", "{{subtotal}}", "{{cgst_total}}", "{{sgst_total}}",
            "{{tax_total}}", "{{amount_words}}", "{{customer_address}}", "{{supplier_gstin}}"
        ])
        self.var_combo.currentIndexChanged.connect(self.insert_variable)
        text_layout.addRow("Placeholders:", self.var_combo)
        
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Times-Roman", "Times-Bold", "Courier"])
        self.font_combo.currentTextChanged.connect(lambda v: self.update_elem_prop('font', v))
        text_layout.addRow("Font Family:", self.font_combo)
        
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(6, 72)
        self.spin_font_size.valueChanged.connect(lambda v: self.update_elem_prop('font_size', v))
        text_layout.addRow("Font Size:", self.spin_font_size)
        
        self.align_combo = QComboBox()
        self.align_combo.addItems(["left", "center", "right"])
        self.align_combo.currentTextChanged.connect(lambda v: self.update_elem_prop('alignment', v))
        text_layout.addRow("Alignment:", self.align_combo)
        
        color_row = QHBoxLayout()
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(50, 26)
        self.color_btn.clicked.connect(self.pick_color)
        color_row.addWidget(self.color_btn)
        color_row.addStretch()
        text_layout.addRow("Color:", color_row)
        
        scroll_layout.addWidget(text_group)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
        
        return panel

    def insert_variable(self, idx: int):
        if idx > 0:
            var_text = self.var_combo.currentText()
            self.txt_content.setText(self.txt_content.text() + " " + var_text)
            self.update_elem_prop('text', self.txt_content.text())
            self.var_combo.setCurrentIndex(0)

    def change_zoom(self, delta: float):
        self.zoom_factor = max(0.2, min(3.0, self.zoom_factor + delta))
        self.view.setTransform(QTransform().scale(self.zoom_factor, self.zoom_factor))
        self.zoom_lbl.setText(f"{int(self.zoom_factor * 100)}%")

    def fit_page_in_view(self):
        self.view.fitInView(self.scene.page_bg_item, Qt.AspectRatioMode.KeepAspectRatio)
        self.zoom_factor = self.view.transform().m11()
        self.zoom_lbl.setText(f"{int(self.zoom_factor * 100)}%")

    def toggle_grid(self, checked: bool):
        self.scene.grid_visible = checked
        self.scene.update()

    def toggle_snap(self, checked: bool):
        self.scene.snap_to_grid = checked

    def load_initial_config(self):
        generator = get_generator()
        self.update_config_display(generator.config)

    def update_config_display(self, config: Dict):
        self.config = copy.deepcopy(config)
        elements = self.config.get('elements', [])
        
        generator = get_generator()
        bg_pdf = self.config.get('background_pdf', 'challan copy.pdf')
        bg_path = os.path.join(generator.base_dir, bg_pdf)
        if not os.path.exists(bg_path):
            bg_path = os.path.join(generator.base_dir, 'challan copy.pdf')
            
        if os.path.exists(bg_path):
            try:
                import fitz
                doc = fitz.open(bg_path)
                pix = doc[0].get_pixmap(dpi=150)
                qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
                self.scene.set_background_pixmap(pixmap)
            except Exception as e:
                print(f"Error rendering background PDF page: {e}")

        self.scene.load_elements(elements)
        self.refresh_elem_combo()
        QTimer.singleShot(200, self.fit_page_in_view)

    def refresh_elem_combo(self):
        self.elem_combo.blockSignals(True)
        self.elem_combo.clear()
        elements = self.config.get('elements', [])
        for elem in elements:
            self.elem_combo.addItem(f"{elem.get('name', 'Item')} ({elem.get('type')})", elem.get('id'))
        self.elem_combo.blockSignals(False)

    def on_element_selected_from_scene(self, elem_config: Dict):
        self.selected_element_config = elem_config
        elem_id = elem_config.get('id')
        idx = self.elem_combo.findData(elem_id)
        if idx >= 0:
            self.elem_combo.blockSignals(True)
            self.elem_combo.setCurrentIndex(idx)
            self.elem_combo.blockSignals(False)
        self.populate_properties(elem_config)

    def on_element_modified_from_scene(self, elem_config: Dict):
        self.selected_element_config = elem_config
        self.populate_properties(elem_config)

    def on_elem_combo_changed(self, idx: int):
        elem_id = self.elem_combo.itemData(idx)
        elements = self.config.get('elements', [])
        for elem in elements:
            if elem.get('id') == elem_id:
                item = self.scene.element_items.get(elem_id)
                if item:
                    self.scene.clearSelection()
                    item.setSelected(True)
                    self.populate_properties(elem)
                break

    def populate_properties(self, elem: Dict):
        self.spin_x.blockSignals(True)
        self.spin_y.blockSignals(True)
        self.spin_w.blockSignals(True)
        self.spin_h.blockSignals(True)
        self.txt_content.blockSignals(True)
        self.font_combo.blockSignals(True)
        self.spin_font_size.blockSignals(True)
        self.align_combo.blockSignals(True)
        
        self.spin_x.setValue(float(elem.get('x', 0)))
        self.spin_y.setValue(float(elem.get('y', 0)))
        self.spin_w.setValue(float(elem.get('width', 100)))
        self.spin_h.setValue(float(elem.get('height', 20)))
        self.txt_content.setText(str(elem.get('text', '')))
        
        idx = self.font_combo.findText(elem.get('font', 'Helvetica'))
        if idx >= 0:
            self.font_combo.setCurrentIndex(idx)
            
        self.spin_font_size.setValue(int(elem.get('font_size', 10)))
        
        idx = self.align_combo.findText(elem.get('alignment', 'left'))
        if idx >= 0:
            self.align_combo.setCurrentIndex(idx)
            
        color = elem.get('color', '#000000')
        self.color_btn.setStyleSheet(f"background-color: {color}; border: 1px solid #cbd5e1; border-radius: 4px;")
        
        self.spin_x.blockSignals(False)
        self.spin_y.blockSignals(False)
        self.spin_w.blockSignals(False)
        self.spin_h.blockSignals(False)
        self.txt_content.blockSignals(False)
        self.font_combo.blockSignals(False)
        self.spin_font_size.blockSignals(False)
        self.align_combo.blockSignals(False)

    def update_elem_prop(self, key: str, value: Any):
        if not self.selected_element_config:
            return
        self.selected_element_config[key] = value
        
        elem_id = self.selected_element_config.get('id')
        item = self.scene.element_items.get(elem_id)
        if item:
            if key == 'x':
                item.setPos(float(value), item.pos().y())
            elif key == 'y':
                item.setPos(item.pos().x(), float(value))
            elif key in ['width', 'height']:
                item.setRect(0, 0, float(self.selected_element_config.get('width', 100)), float(self.selected_element_config.get('height', 20)))
                item.update_handle_positions()
            item.update()

    def pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            self.color_btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #cbd5e1; border-radius: 4px;")
            self.update_elem_prop('color', hex_color)

    def add_element(self, elem_type: str):
        elem_id = f"elem_{len(self.config.get('elements', [])) + 1}"
        new_elem = {
            "id": elem_id,
            "type": elem_type,
            "name": f"New {elem_type.title()}",
            "x": 100,
            "y": 100,
            "width": 150,
            "height": 30 if elem_type != 'table' else 120,
            "text": "New Text Element" if elem_type != 'table' else "",
            "font": "Helvetica",
            "font_size": 10,
            "color": "#000000",
            "alignment": "left"
        }
        if 'elements' not in self.config:
            self.config['elements'] = []
        self.config['elements'].append(new_elem)
        
        item = DesignerElementItem(new_elem, self.scene)
        self.scene.addItem(item)
        self.scene.element_items[elem_id] = item
        self.refresh_elem_combo()
        item.setSelected(True)

    def delete_selected_element(self):
        if not self.selected_element_config:
            return
        elem_id = self.selected_element_config.get('id')
        elements = self.config.get('elements', [])
        self.config['elements'] = [e for e in elements if e.get('id') != elem_id]
        
        item = self.scene.element_items.get(elem_id)
        if item:
            self.scene.removeItem(item)
            del self.scene.element_items[elem_id]
            
        self.selected_element_config = None
        self.refresh_elem_combo()

    def load_background_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Template PDF", "", "PDF Files (*.pdf)")
        if file_path:
            filename = os.path.basename(file_path)
            dest = os.path.join(get_generator().base_dir, 'templates', filename)
            shutil.copy(file_path, dest)
            self.config['background_pdf'] = f"templates/{filename}"
            self.update_config_display(self.config)

    def show_live_pdf_preview(self):
        generator = get_generator()
        sample_data = {
            'studentName': 'GSC GLASS PRIVATE LIMITED',
            'rollNo': '2026-2027/05',
            'amount': '84795.00',
            'description': 'RIGHT ANGLE SPM & ROLLER CONVEYOR',
            'date': '11-06-2026'
        }
        png_bytes = generator.render_preview_png(sample_data, self.config, dpi=150)
        
        dialog = QDialog(self)
        dialog.setWindowTitle("👁️ Live PDF Preview")
        dialog.setMinimumSize(650, 850)
        
        d_layout = QVBoxLayout(dialog)
        img_lbl = QLabel()
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        pixmap = QPixmap()
        pixmap.loadFromData(png_bytes)
        img_lbl.setPixmap(pixmap.scaled(600, 800, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        d_layout.addWidget(img_lbl)
        dialog.exec()

    def save_config(self):
        generator = get_generator()
        generator.save_config(self.config)
        self.main_window.toast.show_message("✅ Template Configuration Saved!", "success")
        self.config_saved.emit(self.config)


class TemplateGraphicsScene(QGraphicsScene):
    """QGraphicsScene representing exact A4 canvas (595.27 x 841.89 pt)"""

    element_selected = pyqtSignal(dict)
    element_modified = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(0, 0, A4_WIDTH_PT, A4_HEIGHT_PT, parent)
        
        self.setBackgroundBrush(QBrush(QColor('#e2e8f0')))
        
        self.page_bg_item = QGraphicsRectItem(0, 0, A4_WIDTH_PT, A4_HEIGHT_PT)
        self.page_bg_item.setBrush(QBrush(QColor('#ffffff')))
        self.page_bg_item.setPen(QPen(QColor('#cbd5e1'), 1))
        self.addItem(self.page_bg_item)
        
        self.template_pixmap_item = QGraphicsPixmapItem(self.page_bg_item)
        
        self.grid_visible = True
        self.snap_to_grid = True
        self.grid_size = 10
        self.element_items = {}

    def set_background_pixmap(self, pixmap: QPixmap):
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                int(A4_WIDTH_PT), int(A4_HEIGHT_PT),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.template_pixmap_item.setPixmap(scaled)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        super().drawBackground(painter, rect)
        
        if self.grid_visible:
            painter.save()
            painter.setPen(QPen(QColor('#f1f5f9'), 1, Qt.PenStyle.SolidLine))
            
            x_start = int(rect.left()) - (int(rect.left()) % self.grid_size)
            x_end = int(rect.right())
            for x in range(x_start, x_end, self.grid_size):
                if 0 <= x <= A4_WIDTH_PT:
                    painter.drawLine(x, 0, x, int(A4_HEIGHT_PT))
                    
            y_start = int(rect.top()) - (int(rect.top()) % self.grid_size)
            y_end = int(rect.bottom())
            for y in range(y_start, y_end, self.grid_size):
                if 0 <= y <= A4_HEIGHT_PT:
                    painter.drawLine(0, y, int(A4_WIDTH_PT), y)
                    
            painter.restore()

    def load_elements(self, elements: List[Dict]):
        for item in self.element_items.values():
            self.removeItem(item)
        self.element_items.clear()
        
        for elem in elements:
            item = DesignerElementItem(elem, self)
            self.addItem(item)
            self.element_items[elem.get('id', id(elem))] = item

    def on_element_selected(self, item: 'DesignerElementItem'):
        self.element_selected.emit(item.elem_config)

    def on_element_changed(self, item: 'DesignerElementItem'):
        self.element_modified.emit(item.elem_config)


class DesignerElementItem(QGraphicsRectItem):
    """Visual Element on Designer Canvas with 8-handle resizing"""

    def __init__(self, elem_config: Dict[str, Any], parent_scene: TemplateGraphicsScene):
        x = float(elem_config.get('x', 50))
        y = float(elem_config.get('y', 50))
        w = float(elem_config.get('width', 150))
        h = float(elem_config.get('height', 30))
        
        super().__init__(0, 0, w, h)
        
        self.elem_config = elem_config
        self.parent_scene = parent_scene
        
        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        
        self.handles = {}
        handle_positions = ['top_left', 'top', 'top_right', 'right', 'bottom_right', 'bottom', 'bottom_left', 'left']
        for pos_code in handle_positions:
            h_item = ResizeHandleItem(pos_code, self)
            h_item.hide()
            self.handles[pos_code] = h_item
            
        self.update_handle_positions()

    def update_handle_positions(self):
        r = self.rect()
        w, h = r.width(), r.height()
        
        positions = {
            'top_left': QPointF(0, 0),
            'top': QPointF(w / 2.0, 0),
            'top_right': QPointF(w, 0),
            'right': QPointF(w, h / 2.0),
            'bottom_right': QPointF(w, h),
            'bottom': QPointF(w / 2.0, h),
            'bottom_left': QPointF(0, h),
            'left': QPointF(0, h / 2.0)
        }
        for pos_code, pos_pt in positions.items():
            if pos_code in self.handles:
                self.handles[pos_code].setPos(pos_pt)

    def handle_resize(self, pos_code: str, dx: float, dy: float):
        r = self.rect()
        pos = self.pos()
        x, y, w, h = pos.x(), pos.y(), r.width(), r.height()
        min_w, min_h = 10, 10
        
        if 'left' in pos_code:
            new_w = max(min_w, w - dx)
            new_x = x + (w - new_w)
            self.setPos(new_x, y)
            w = new_w
            x = new_x
        elif 'right' in pos_code:
            w = max(min_w, w + dx)
            
        if 'top' in pos_code:
            new_h = max(min_h, h - dy)
            new_y = y + (h - new_h)
            self.setPos(x, new_y)
            h = new_h
        elif 'bottom' in pos_code:
            h = max(min_h, h + dy)
            
        self.setRect(0, 0, w, h)
        self.elem_config['x'] = round(x, 1)
        self.elem_config['y'] = round(y, 1)
        self.elem_config['width'] = round(w, 1)
        self.elem_config['height'] = round(h, 1)
        
        self.update_handle_positions()
        self.parent_scene.on_element_changed(self)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            p = self.pos()
            new_x = round(p.x(), 1)
            new_y = round(p.y(), 1)
            
            if self.parent_scene and self.parent_scene.snap_to_grid:
                gs = self.parent_scene.grid_size
                new_x = round(new_x / gs) * gs
                new_y = round(new_y / gs) * gs
                self.setPos(new_x, new_y)
                
            self.elem_config['x'] = new_x
            self.elem_config['y'] = new_y
            self.parent_scene.on_element_changed(self)
            
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            is_selected = bool(value)
            for h_item in self.handles.values():
                h_item.setVisible(is_selected)
            if is_selected:
                self.parent_scene.on_element_selected(self)
                
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option: Any, widget: Optional[QWidget] = None):
        r = self.rect()
        elem_type = self.elem_config.get('type', 'text')
        is_selected = self.isSelected()
        
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if is_selected:
            pen = QPen(QColor('#2563eb'), 2, Qt.PenStyle.DashLine)
            brush = QBrush(QColor(37, 99, 235, 40))
        else:
            pen = QPen(QColor('#94a3b8'), 1, Qt.PenStyle.SolidLine)
            brush = QBrush(QColor(241, 245, 249, 30))
            
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRoundedRect(r, 3, 3)
        
        font_size = max(8, int(self.elem_config.get('font_size', 10)))
        font = QFont("Helvetica", font_size)
        if "Bold" in self.elem_config.get('font', ''):
            font.setBold(True)
        painter.setFont(font)
        
        color_hex = self.elem_config.get('color', '#0f172a')
        painter.setPen(QPen(QColor(color_hex)))
        
        align_flag = Qt.AlignmentFlag.AlignLeft
        align = self.elem_config.get('alignment', 'left')
        if align == 'center':
            align_flag = Qt.AlignmentFlag.AlignCenter
        elif align == 'right':
            align_flag = Qt.AlignmentFlag.AlignRight
            
        align_flag |= Qt.AlignmentFlag.AlignVCenter
        
        if elem_type == 'table':
            cols = self.elem_config.get('columns', [])
            col_x = 0
            for col in cols:
                cw = float(col.get('width', 40))
                painter.setPen(QPen(QColor('#cbd5e1'), 1, Qt.PenStyle.DotLine))
                painter.drawLine(int(col_x), 0, int(col_x), int(r.height()))
                painter.setPen(QPen(QColor('#334155')))
                painter.drawText(QRectF(col_x + 2, 0, cw - 4, r.height()), Qt.AlignmentFlag.AlignCenter, col.get('title', 'Col'))
                col_x += cw
        else:
            text = self.elem_config.get('text', self.elem_config.get('name', 'Text'))
            painter.drawText(r.adjusted(4, 2, -4, -2), align_flag, text)
            
        painter.restore()


class ResizeHandleItem(QGraphicsRectItem):
    """Control handle for resizing designer items (8 positions around box)"""

    def __init__(self, position_code: str, parent_element: DesignerElementItem):
        super().__init__(-4, -4, 8, 8, parent_element)
        self.position_code = position_code
        self.parent_element = parent_element
        
        self.setBrush(QBrush(QColor('#2563eb')))
        self.setPen(QPen(QColor('#1e40af'), 1))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(100)
        
        cursors = {
            'top_left': Qt.CursorShape.SizeFDiagCursor,
            'top': Qt.CursorShape.SizeVerCursor,
            'top_right': Qt.CursorShape.SizeBDiagCursor,
            'right': Qt.CursorShape.SizeHorCursor,
            'bottom_right': Qt.CursorShape.SizeFDiagCursor,
            'bottom': Qt.CursorShape.SizeVerCursor,
            'bottom_left': Qt.CursorShape.SizeBDiagCursor,
            'left': Qt.CursorShape.SizeHorCursor
        }
        self.setCursor(cursors.get(position_code, Qt.CursorShape.ArrowCursor))
        self.drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.scenePos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_start_pos is not None:
            delta = event.scenePos() - self.drag_start_pos
            self.drag_start_pos = event.scenePos()
            self.parent_element.handle_resize(self.position_code, delta.x(), delta.y())
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_start_pos = None
        event.accept()


# ======================== SIMPLIFIED GENERATE CHALLAN TAB ========================

class GenerateChallanTab(QWidget):
    """Simplified Landing Page: Company dropdown + Item Table only"""

    def __init__(self, main_window: 'MainWindow'):
        super().__init__(main_window)
        self.main_window = main_window
        self.company_manager = CompanyDataManager()
        self.setup_ui()
        self.reset_defaults()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        card = QWidget()
        card.setStyleSheet("background: #ffffff; border-radius: 12px; border: 1px solid #cbd5e1;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)
        
        title = QLabel("📋 Delivery Challan Generator (NextUp Robotics)")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #1e40af;")
        card_layout.addWidget(title)
        
        desc = QLabel("Select a company and enter item details. All other fields are auto-filled from saved data.")
        desc.setStyleSheet("color: #475569; font-size: 13px;")
        card_layout.addWidget(desc)
        
        # ====== SIMPLIFIED FORM: Company Dropdown + Items ======
        
        # Company Selection
        company_group = QGroupBox("🏢 Select Company")
        company_layout = QVBoxLayout(company_group)
        
        company_row = QHBoxLayout()
        company_row.addWidget(QLabel("Company Name:"))
        
        self.company_combo = QComboBox()
        self.company_combo.setMinimumWidth(400)
        self.company_combo.currentIndexChanged.connect(self.on_company_selected)
        company_row.addWidget(self.company_combo)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_companies)
        company_row.addWidget(refresh_btn)
        
        company_row.addStretch()
        company_layout.addLayout(company_row)
        
        card_layout.addWidget(company_group)
        
        # Hidden fields (auto-filled when company is selected)
        self.hidden_fields = {}
        
        # Items Table
        items_group = QGroupBox("📦 Items / Services")
        items_layout = QVBoxLayout(items_group)
        
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(8)
        self.items_table.setHorizontalHeaderLabels([
            "S.No", "Description / Service", "HSN Code", "Qty", "Rate (₹)",
            "Taxable (₹)", "GST %", "Total (₹)"
        ])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.items_table.setMinimumHeight(180)
        self.items_table.itemChanged.connect(self.recalculate_totals)
        items_layout.addWidget(self.items_table)
        
        items_btn_layout = QHBoxLayout()
        add_item_btn = QPushButton("➕ Add Row")
        add_item_btn.clicked.connect(self.add_item_row)
        items_btn_layout.addWidget(add_item_btn)
        
        remove_item_btn = QPushButton("🗑️ Remove Row")
        remove_item_btn.clicked.connect(self.remove_item_row)
        items_btn_layout.addWidget(remove_item_btn)
        
        items_btn_layout.addStretch()
        items_layout.addLayout(items_btn_layout)
        
        card_layout.addWidget(items_group)
        
        # Live Totals Summary
        totals_group = QGroupBox("💰 Auto-Calculated Totals")
        totals_layout = QGridLayout(totals_group)
        
        self.lbl_subtotal = QLabel("₹ 0.00")
        self.lbl_subtotal.setStyleSheet("font-weight: 700; color: #1e293b;")
        totals_layout.addWidget(QLabel("Subtotal:"), 0, 0)
        totals_layout.addWidget(self.lbl_subtotal, 0, 1)
        
        self.lbl_gst = QLabel("₹ 0.00")
        totals_layout.addWidget(QLabel("GST Total:"), 0, 2)
        totals_layout.addWidget(self.lbl_gst, 0, 3)
        
        self.lbl_grand_total = QLabel("₹ 0.00")
        self.lbl_grand_total.setStyleSheet("font-size: 16px; font-weight: 800; color: #1e40af;")
        totals_layout.addWidget(QLabel("Grand Total:"), 1, 0)
        totals_layout.addWidget(self.lbl_grand_total, 1, 1)
        
        self.lbl_words = QLabel("Rupees Zero Only")
        self.lbl_words.setStyleSheet("font-style: italic; color: #334155;")
        totals_layout.addWidget(QLabel("Amount in Words:"), 2, 0)
        totals_layout.addWidget(self.lbl_words, 2, 1, 1, 3)
        
        card_layout.addWidget(totals_group)
        
        # Action Buttons
        act_layout = QHBoxLayout()
        
        reset_btn = QPushButton("🔄 Reset")
        reset_btn.clicked.connect(self.reset_defaults)
        act_layout.addWidget(reset_btn)
        
        preview_btn = QPushButton("👁️ Preview PDF")
        preview_btn.setStyleSheet("background: #8b5cf6; color: white; font-weight: 700; padding: 12px 20px;")
        preview_btn.clicked.connect(self.preview_pdf)
        act_layout.addWidget(preview_btn)
        
        generate_btn = QPushButton("✓ Generate & Download PDF")
        generate_btn.setStyleSheet("background: #2563eb; color: white; font-weight: 700; padding: 14px 28px; font-size: 15px;")
        generate_btn.clicked.connect(self.submit_form)
        act_layout.addWidget(generate_btn)
        
        card_layout.addLayout(act_layout)
        scroll.setWidget(card)
        layout.addWidget(scroll)
        
        # Load companies
        self.refresh_companies()

    def refresh_companies(self):
        self.company_combo.blockSignals(True)
        self.company_combo.clear()
        self.company_combo.addItem("-- Select a Company --", None)
        for company in self.company_manager.get_all_companies():
            self.company_combo.addItem(company.get('name', 'Unnamed'), company)
        self.company_combo.blockSignals(False)

    def on_company_selected(self, index: int):
        if index <= 0:
            return
        company = self.company_combo.currentData()
        if company:
            # Auto-fill all fields - store in hidden dict
            self.hidden_fields = {
                'studentName': company.get('name', ''),
                'customer_address': company.get('customer_address', ''),
                'customer_gstin': company.get('customer_gstin', ''),
                'customer_state': company.get('customer_state', ''),
                'customer_state_code': company.get('customer_state_code', ''),
                'vehicle_no': company.get('vehicle_no', ''),
                'supplier_gstin': '09AAHCN8459L1ZM',
                'supplier_state': 'UTTAR PRADESH',
                'supplier_state_code': '09',
                'company_name': 'NEXTUP ROBOTICS PVT LTD'
            }
            self.main_window.toast.show_message(f"✅ Loaded data for {company.get('name')}", "success")

    def reset_defaults(self):
        self.company_combo.setCurrentIndex(0)
        self.hidden_fields = {}
        
        self.items_table.blockSignals(True)
        self.items_table.setRowCount(1)
        
        default_items = [
            {"sno": "1", "desc": "Service / Item Description", "hsn": "84795000", "qty": "1.00", "rate": "0.00", "taxable": "0.00", "gst": "18%", "total": "0.00"}
        ]
        
        for row, it in enumerate(default_items):
            self.items_table.setItem(row, 0, QTableWidgetItem(it["sno"]))
            self.items_table.setItem(row, 1, QTableWidgetItem(it["desc"]))
            self.items_table.setItem(row, 2, QTableWidgetItem(it["hsn"]))
            self.items_table.setItem(row, 3, QTableWidgetItem(it["qty"]))
            self.items_table.setItem(row, 4, QTableWidgetItem(it["rate"]))
            self.items_table.setItem(row, 5, QTableWidgetItem(it["taxable"]))
            self.items_table.setItem(row, 6, QTableWidgetItem(it["gst"]))
            self.items_table.setItem(row, 7, QTableWidgetItem(it["total"]))
            
        self.items_table.blockSignals(False)
        self.recalculate_totals()

    def add_item_row(self):
        row = self.items_table.rowCount()
        self.items_table.blockSignals(True)
        self.items_table.insertRow(row)
        self.items_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.items_table.setItem(row, 1, QTableWidgetItem("New Service / Item"))
        self.items_table.setItem(row, 2, QTableWidgetItem("84795000"))
        self.items_table.setItem(row, 3, QTableWidgetItem("1.00"))
        self.items_table.setItem(row, 4, QTableWidgetItem("0.00"))
        self.items_table.setItem(row, 5, QTableWidgetItem("0.00"))
        self.items_table.setItem(row, 6, QTableWidgetItem("18%"))
        self.items_table.setItem(row, 7, QTableWidgetItem("0.00"))
        self.items_table.blockSignals(False)
        self.recalculate_totals()

    def remove_item_row(self):
        row = self.items_table.currentRow()
        if row >= 0 and self.items_table.rowCount() > 1:
            self.items_table.removeRow(row)
            self.recalculate_totals()

    def get_items_data(self) -> List[Dict]:
        items = []
        for r in range(self.items_table.rowCount()):
            try:
                sno = self.items_table.item(r, 0).text() if self.items_table.item(r, 0) else str(r + 1)
                desc = self.items_table.item(r, 1).text() if self.items_table.item(r, 1) else ""
                hsn = self.items_table.item(r, 2).text() if self.items_table.item(r, 2) else ""
                qty = float(self.items_table.item(r, 3).text()) if self.items_table.item(r, 3) else 1.0
                rate = float(self.items_table.item(r, 4).text()) if self.items_table.item(r, 4) else 0.0
                taxable = qty * rate
                
                gst_str = self.items_table.item(r, 6).text() if self.items_table.item(r, 6) else "18%"
                gst_pct = float(gst_str.replace('%', '')) / 100.0 if '%' in gst_str else float(gst_str or 0) / 100.0
                
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

    def recalculate_totals(self):
        items = self.get_items_data()
        generator = get_generator()
        data = {"items": items}
        enriched = generator.process_data_and_totals(data)
        
        self.lbl_subtotal.setText(f"₹ {enriched.get('subtotal', '0.00')}")
        self.lbl_gst.setText(f"₹ {enriched.get('tax_total', '0.00')}")
        self.lbl_grand_total.setText(f"₹ {enriched.get('amount', '0.00')}")
        self.lbl_words.setText(enriched.get('amount_words', 'Rupees Zero Only'))

    def collect_form_payload(self) -> Dict[str, Any]:
        payload = {
            "copy_type": "Original Copy",
            "company_name": "NEXTUP ROBOTICS PVT LTD",
            "supplier_gstin": "09AAHCN8459L1ZM",
            "supplier_state": "UTTAR PRADESH",
            "supplier_state_code": "09",
            "date": datetime.now().strftime('%d-%m-%Y'),
            "challanNumber": f"CH-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}",
            "items": self.get_items_data()
        }
        
        # Merge hidden fields
        payload.update(self.hidden_fields)
        
        # Generate challan number if not set
        if not payload.get('challanNumber'):
            payload['challanNumber'] = f"CH-{datetime.now().strftime('%Y%m%d')}-001"
            
        return payload

    def preview_pdf(self):
        payload = self.collect_form_payload()
        if not payload.get('studentName'):
            self.main_window.toast.show_message("Please select a company first!", "error")
            return
            
        generator = get_generator()
        png_bytes = generator.render_preview_png(payload, dpi=150)
        
        dialog = QDialog(self)
        dialog.setWindowTitle("👁️ Live PDF Preview - Delivery Challan")
        dialog.setMinimumSize(650, 850)
        
        d_layout = QVBoxLayout(dialog)
        img_lbl = QLabel()
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        pixmap = QPixmap()
        pixmap.loadFromData(png_bytes)
        img_lbl.setPixmap(pixmap.scaled(600, 800, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        d_layout.addWidget(img_lbl)
        dialog.exec()

    def submit_form(self):
        payload = self.collect_form_payload()
        if not payload.get('studentName'):
            self.main_window.toast.show_message("Please select a company first!", "error")
            return
            
        generator = get_generator()
        save_path = generator.save_pdf(payload)
        
        self.main_window.toast.show_message("✅ Challan generated & downloaded!", "success")
        QDesktopServices.openUrl(QUrl.fromLocalFile(save_path))


# ======================== RECENT CHALLANS TAB ========================

class RecentChallansTab(QWidget):
    """Tab to view and manage generated challans"""

    def __init__(self, main_window: 'MainWindow'):
        super().__init__(main_window)
        self.main_window = main_window
        self.setup_ui()
        QTimer.singleShot(200, self.fetch_submissions)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        
        card = QWidget()
        card.setStyleSheet("background: #ffffff; border-radius: 12px; border: 1px solid #cbd5e1;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        
        header = QHBoxLayout()
        title = QLabel("📄 Recent Generated Challans")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #1e40af;")
        header.addWidget(title)
        
        header.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.fetch_submissions)
        header.addWidget(refresh_btn)
        
        card_layout.addLayout(header)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Customer", "Challan No", "Amount (₹)", "Date", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                color: #0f172a;
                gridline-color: #e2e8f0;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #f1f5f9;
                color: #1e40af;
                font-weight: 700;
                padding: 8px;
                border: 1px solid #cbd5e1;
            }
        """)
        card_layout.addWidget(self.table)
        
        layout.addWidget(card)

    def fetch_submissions(self):
        generator = get_generator()
        gen_dir = os.path.join(generator.base_dir, 'generated')
        if not os.path.exists(gen_dir):
            return
            
        files = sorted(os.listdir(gen_dir), reverse=True)
        pdf_files = [f for f in files if f.endswith('.pdf')]
        
        self.table.setRowCount(len(pdf_files))
        for idx, f in enumerate(pdf_files):
            parts = f.replace('.pdf', '').split('_')
            challan_no = parts[1] if len(parts) > 1 else 'N/A'
            
            self.table.setItem(idx, 0, QTableWidgetItem("Delivery Challan"))
            self.table.setItem(idx, 1, QTableWidgetItem(challan_no))
            self.table.setItem(idx, 2, QTableWidgetItem("₹ Amount"))
            self.table.setItem(idx, 3, QTableWidgetItem(datetime.now().strftime("%Y-%m-%d")))
            
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            
            open_btn = QPushButton("📄 Open")
            open_btn.setStyleSheet("background: #2563eb; color: white; border: none; padding: 4px 8px; font-weight: 600; border-radius: 4px;")
            file_path = os.path.join(gen_dir, f)
            open_btn.clicked.connect(lambda _, p=file_path: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
            btn_layout.addWidget(open_btn)
            
            self.table.setCellWidget(idx, 4, btn_widget)


# ======================== MAIN WINDOW ========================

class MainWindow(QMainWindow):
    """Main Application Window with Settings Menu"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Challan Generator Pro - NextUp Robotics")
        self.setMinimumSize(1100, 800)
        
        self.network_manager = QNetworkAccessManager()
        self.toast = MessageToast(self)
        
        self.setup_ui()

    def setup_ui(self):
        # Menu Bar
        menubar = self.menuBar()
        
        # Settings Menu
        settings_menu = menubar.addMenu("⚙️ Settings")
        
        # Template Editor action (hidden behind Settings)
        designer_action = QAction("🎨 Template Editor (Advanced)", self)
        designer_action.triggered.connect(self.open_designer_tab)
        settings_menu.addAction(designer_action)
        
        settings_menu.addSeparator()
        
        # Company Management action
        company_action = QAction("🏢 Manage Saved Companies", self)
        company_action.triggered.connect(self.open_company_manager)
        settings_menu.addAction(company_action)
        
        settings_menu.addSeparator()
        
        # Refresh companies action
        refresh_action = QAction("🔄 Refresh Companies List", self)
        refresh_action.triggered.connect(self.refresh_companies)
        settings_menu.addAction(refresh_action)
        
        # Main Layout
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QWidget()
        header.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e3a5f, stop:1 #2563eb); padding: 16px 24px;")
        h_layout = QHBoxLayout(header)
        
        title = QLabel("📋 Delivery Challan Generator")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: 800;")
        h_layout.addWidget(title)
        
        subtitle = QLabel("Select Company → Add Items → Generate")
        subtitle.setStyleSheet("color: #93c5fd; font-size: 13px; margin-left: 12px; font-weight: 500;")
        h_layout.addWidget(subtitle)
        
        h_layout.addStretch()
        layout.addWidget(header)
        
        # Tabs
        self.tabs = QTabWidget()
        self.generate_tab = GenerateChallanTab(self)
        self.designer_tab = VisualDesignerTab(self)
        self.recent_tab = RecentChallansTab(self)
        
        self.tabs.addTab(self.generate_tab, "📋 Generate Challan")
        self.tabs.addTab(self.recent_tab, "📄 Recent Challans")
        self.tabs.addTab(self.designer_tab, "🎨 Template Editor")
        
        # Hide designer tab by default (accessible only via Settings)
        self.tabs.setTabVisible(2, False)
        
        self.tabs.setCurrentIndex(0)
        layout.addWidget(self.tabs, 1)
        
        # Store reference to company manager
        self.company_manager = CompanyDataManager()

    def open_designer_tab(self):
        """Open the Template Designer tab (hidden by default)"""
        self.tabs.setTabVisible(2, True)
        self.tabs.setCurrentIndex(2)
        self.toast.show_message("🎨 Template Designer opened. Use with caution!", "success")
        
    def open_company_manager(self):
        """Open Company Management Dialog"""
        dialog = CompanyManagementDialog(self)
        if dialog.exec():
            self.refresh_companies()
            
    def refresh_companies(self):
        """Refresh companies in the generate tab"""
        self.generate_tab.refresh_companies()
        self.toast.show_message("🔄 Companies list refreshed", "success")


# ======================== MESSAGE TOAST ========================

class MessageToast(QWidget):
    """Toast Notification Overlay"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        self.label = QLabel()
        self.label.setStyleSheet("color: white; font-size: 14px; font-weight: 700;")
        layout.addWidget(self.label)
        
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def show_message(self, text: str, msg_type: str = "success"):
        bg = "#10b981" if msg_type == "success" else "#ef4444"
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
            background-color: #f8fafc;
        }
        QWidget {
            color: #0f172a;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        QLabel {
            color: #1e293b;
            font-size: 13px;
        }
        QLineEdit {
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 7px 10px;
            font-size: 13px;
        }
        QLineEdit:focus {
            border-color: #2563eb;
            background-color: #ffffff;
        }
        QDateEdit {
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 7px 10px;
            font-size: 13px;
        }
        QDateEdit:focus {
            border-color: #2563eb;
        }
        QSpinBox, QDoubleSpinBox {
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 6px 8px;
            font-size: 13px;
            font-weight: 500;
        }
        QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: #2563eb;
        }
        QComboBox {
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 13px;
            font-weight: 500;
            min-height: 24px;
        }
        QComboBox:hover {
            border-color: #2563eb;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 24px;
            border-left: 1px solid #e2e8f0;
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
        }
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            color: #0f172a;
            selection-background-color: #2563eb;
            selection-color: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 4px;
            outline: 0px;
        }
        QGroupBox {
            font-weight: 700;
            font-size: 14px;
            color: #1e40af;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 14px;
            background-color: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            left: 12px;
            background-color: #ffffff;
            color: #1e40af;
        }
        QPushButton {
            background-color: #ffffff;
            color: #1e293b;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 8px 14px;
            font-size: 13px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #f1f5f9;
            border-color: #2563eb;
            color: #1d4ed8;
        }
        QPushButton:pressed {
            background-color: #e2e8f0;
        }
        QCheckBox {
            color: #1e293b;
            font-size: 13px;
            font-weight: 500;
            spacing: 6px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 1px solid #cbd5e1;
            background-color: #ffffff;
        }
        QCheckBox::indicator:checked {
            background-color: #2563eb;
            border-color: #1d4ed8;
        }
        QTabWidget::pane {
            border: none;
            background: transparent;
        }
        QTabBar::tab {
            background: #e2e8f0;
            color: #475569;
            border: 1px solid #cbd5e1;
            border-bottom: none;
            border-radius: 8px 8px 0 0;
            padding: 10px 22px;
            font-size: 14px;
            font-weight: 600;
            margin-right: 4px;
        }
        QTabBar::tab:selected {
            background: #ffffff;
            color: #1e40af;
            border-bottom: 3px solid #2563eb;
        }
        QTabBar::tab:hover:!selected {
            background: #f1f5f9;
            color: #0f172a;
        }
        QScrollArea {
            border: none;
            background: transparent;
        }
        QSplitter::handle {
            background-color: #cbd5e1;
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