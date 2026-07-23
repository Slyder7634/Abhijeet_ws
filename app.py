"""
Challan Generator - Core Engine
Handles PDF rendering, template overlays with white-out masking, dynamic tables, auto-calculations, and visual preview generation.
"""

import os
import json
import io
import copy
from datetime import datetime
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

try:
    from PyPDF2 import PdfReader, PdfWriter
except ImportError:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("❌ PyPDF2 or pypdf is required")
        raise

from pdf_utils import number_to_words_indian, pdf_bytes_to_png_bytes


class ChallanGenerator:
    """Core PDF generator and template engine"""
    
    def __init__(self, config_path: str = None, template_path: str = None):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        if config_path is None:
            config_path = os.path.join(self.base_dir, 'config', 'challan_coordinates.json')
            
        if template_path is None:
            attached = os.path.join(self.base_dir, 'challan copy.pdf')
            if os.path.exists(attached):
                template_path = attached
            else:
                template_path = os.path.join(self.base_dir, 'templates', 'challan.pdf')
                
        self.config_path = config_path
        self.template_path = template_path
        
        os.makedirs(os.path.join(self.base_dir, 'generated'), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'templates'), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'config'), exist_ok=True)
        
        self.config = self._load_config()
        self._ensure_template_exists()
        
    def _load_config(self) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            default_config = self.get_default_delivery_challan_config()
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
            
    def save_config(self, config: Dict):
        """Save configuration to JSON file"""
        self.config = config
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=4)

    def _ensure_template_exists(self):
        """Ensure default template exists"""
        if not os.path.exists(self.template_path):
            self._create_default_template()

    def _create_default_template(self):
        """Create a default template PDF if none exists"""
        c = canvas.Canvas(self.template_path, pagesize=A4)
        width, height = A4
        
        c.setFillColor(colors.HexColor('#1e3a5f'))
        c.rect(0, height - 70, width, 70, fill=True, stroke=False)
        
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(width / 2, height - 40, "DELIVERY CHALLAN")
        c.setFont("Helvetica", 10)
        c.drawCentredString(width / 2, height - 58, "NEXTUP ROBOTICS PRIVATE LIMITED")
        
        c.setFillColor(colors.HexColor('#666666'))
        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, 25, "This is a computer-generated document.")
        c.save()

    def get_default_delivery_challan_config(self) -> Dict:
        """Return full template configuration matching NextUp Robotics delivery challan"""
        return {
            "template_name": "NextUp Robotics Delivery Challan",
            "template_id": "delivery_challan",
            "page_size": "A4",
            "width_pt": 595.27,
            "height_pt": 841.89,
            "use_background_pdf": True,
            "background_pdf": "challan copy.pdf",
            "elements": [
                # Top Header / Document details
                {"id": "copy_type", "type": "text", "name": "Copy Type", "x": 500, "y": 14, "width": 80, "height": 14, "text": "{{copy_type|Original Copy}}", "font": "Helvetica-Bold", "font_size": 9, "color": "#000000", "alignment": "right", "erase_bg": True},
                {"id": "company_name", "type": "text", "name": "Company Name", "x": 104, "y": 48, "width": 380, "height": 22, "text": "{{company_name|NEXTUP ROBOTICS PVT LTD}}", "font": "Helvetica-Bold", "font_size": 18, "color": "#1e3a5f", "alignment": "center", "erase_bg": True},
                {"id": "head_office", "type": "text", "name": "Head Office", "x": 100, "y": 68, "width": 395, "height": 12, "text": "Head Office Add :- {{head_office|5/189, MAIN CHIRANJIV VIHAR ROAD, GHAZIABAD}}", "font": "Helvetica", "font_size": 8, "color": "#333333", "alignment": "center", "erase_bg": True},
                {"id": "branch_office", "type": "text", "name": "Branch Office", "x": 100, "y": 78, "width": 395, "height": 12, "text": "Branch Office Add :- {{branch_office|SA-7, SHASTRI NAGAR, GHAZIABAD}}", "font": "Helvetica", "font_size": 8, "color": "#333333", "alignment": "center", "erase_bg": True},
                {"id": "contact_info", "type": "text", "name": "Contact Info", "x": 100, "y": 88, "width": 395, "height": 12, "text": "Ph :- {{phone|+91 9313748154}}     E-mail :- {{email|nextuprobotics@gmail.com}}", "font": "Helvetica", "font_size": 8, "color": "#333333", "alignment": "center", "erase_bg": True},
                {"id": "doc_title", "type": "text", "name": "Document Title", "x": 200, "y": 103, "width": 195, "height": 16, "text": "Challan", "font": "Helvetica-Bold", "font_size": 14, "color": "#1e3a5f", "alignment": "center", "erase_bg": True},
                
                # Supplier & Customer Details Block
                {"id": "supplier_gstin", "type": "text", "name": "Supplier GSTIN", "x": 75, "y": 115, "width": 160, "height": 12, "text": "{{supplier_gstin|09AAHCN8459L1ZM}}", "font": "Helvetica-Bold", "font_size": 9, "color": "#000000", "alignment": "left", "erase_bg": True},
                {"id": "challan_no", "type": "text", "name": "Challan Number", "x": 75, "y": 127, "width": 160, "height": 12, "text": "{{challanNumber|2026-2027/05}}", "font": "Helvetica", "font_size": 9, "color": "#000000", "alignment": "left", "erase_bg": True},
                {"id": "challan_date", "type": "text", "name": "Challan Date", "x": 75, "y": 137, "width": 160, "height": 12, "text": "{{date|11-06-2026}}", "font": "Helvetica", "font_size": 9, "color": "#000000", "alignment": "left", "erase_bg": True},
                {"id": "supplier_state", "type": "text", "name": "Supplier State", "x": 75, "y": 148, "width": 65, "height": 12, "text": "{{supplier_state|UTTAR PRADESH}}", "font": "Helvetica", "font_size": 8, "color": "#000000", "alignment": "left", "erase_bg": True},
                {"id": "supplier_code", "type": "text", "name": "Supplier State Code", "x": 200, "y": 148, "width": 30, "height": 12, "text": "{{supplier_state_code|09}}", "font": "Helvetica", "font_size": 8, "color": "#000000", "alignment": "left", "erase_bg": True},
                
                # Customer / Consignee Details
                {"id": "customer_name", "type": "text", "name": "Customer Name", "x": 288, "y": 115, "width": 290, "height": 12, "text": "{{studentName|GSC GLASS PRIVATE LIMITED}}", "font": "Helvetica-Bold", "font_size": 9, "color": "#000000", "alignment": "left", "erase_bg": True},
                {"id": "customer_address", "type": "text", "name": "Customer Address", "x": 288, "y": 127, "width": 290, "height": 12, "text": "{{customer_address|5 & 7, UDYOG VIHAR INDUSTRIAL AREA, GREATER NOIDA, Gautambuddha Nagar, U.P-201306}}", "font": "Helvetica", "font_size": 8, "color": "#000000", "alignment": "left", "erase_bg": True},
                {"id": "customer_gstin", "type": "text", "name": "Customer GSTIN", "x": 288, "y": 137, "width": 160, "height": 12, "text": "{{customer_gstin|09AAACG0050D1ZA}}", "font": "Helvetica", "font_size": 8, "color": "#000000", "alignment": "left", "erase_bg": True},
                {"id": "vehicle_no", "type": "text", "name": "Vehicle No", "x": 415, "y": 148, "width": 75, "height": 12, "text": "{{vehicle_no|UP-14-BT-9999}}", "font": "Helvetica", "font_size": 8, "color": "#000000", "alignment": "left", "erase_bg": True},
                {"id": "customer_state", "type": "text", "name": "Customer State", "x": 288, "y": 148, "width": 60, "height": 12, "text": "{{customer_state|U.P}}", "font": "Helvetica", "font_size": 8, "color": "#000000", "alignment": "left", "erase_bg": True},
                {"id": "customer_code", "type": "text", "name": "Customer State Code", "x": 550, "y": 148, "width": 30, "height": 12, "text": "{{customer_state_code|09}}", "font": "Helvetica", "font_size": 8, "color": "#000000", "alignment": "left", "erase_bg": True},
                
                # Dynamic Items Table Component
                {
                    "id": "items_table",
                    "type": "table",
                    "name": "Items Table",
                    "x": 12,
                    "y": 168,
                    "width": 570,
                    "height": 180,
                    "row_height": 18,
                    "data_key": "items",
                    "erase_bg": True,
                    "columns": [
                        {"title": "S.NO.", "key": "sno", "width": 30, "align": "center"},
                        {"title": "Description/Service", "key": "description", "width": 120, "align": "left"},
                        {"title": "HSN Code", "key": "hsn", "width": 55, "align": "center"},
                        {"title": "Qty", "key": "qty", "width": 35, "align": "right"},
                        {"title": "Rate", "key": "rate", "width": 45, "align": "right"},
                        {"title": "Taxable Amt", "key": "taxable", "width": 50, "align": "right"},
                        {"title": "CGST %", "key": "cgst_rate", "width": 40, "align": "right"},
                        {"title": "CGST Amt", "key": "cgst_amt", "width": 50, "align": "right"},
                        {"title": "SGST %", "key": "sgst_rate", "width": 40, "align": "right"},
                        {"title": "SGST Amt", "key": "sgst_amt", "width": 50, "align": "right"},
                        {"title": "Total", "key": "total", "width": 55, "align": "right"}
                    ]
                },
                
                # Summary & Tax Totals
                {"id": "lbl_amount_words", "type": "text", "name": "Amount in Words", "x": 13, "y": 356, "width": 300, "height": 28, "text": "Total Amount in Words : {{amount_words}}", "font": "Helvetica-Bold", "font_size": 8, "color": "#000000", "alignment": "left", "erase_bg": True},
                {"id": "val_before_tax", "type": "text", "name": "Amount Before Tax", "x": 500, "y": 356, "width": 80, "height": 12, "text": "₹ {{subtotal|0.00}}", "font": "Helvetica-Bold", "font_size": 9, "color": "#000000", "alignment": "right", "erase_bg": True},
                {"id": "val_cgst", "type": "text", "name": "CGST Total", "x": 500, "y": 367, "width": 80, "height": 12, "text": "₹ {{cgst_total|0.00}}", "font": "Helvetica", "font_size": 9, "color": "#000000", "alignment": "right", "erase_bg": True},
                {"id": "val_sgst", "type": "text", "name": "SGST Total", "x": 500, "y": 377, "width": 80, "height": 12, "text": "₹ {{sgst_total|0.00}}", "font": "Helvetica", "font_size": 9, "color": "#000000", "alignment": "right", "erase_bg": True},
                {"id": "val_igst", "type": "text", "name": "IGST Total", "x": 500, "y": 387, "width": 80, "height": 12, "text": "₹ {{igst_total|0.00}}", "font": "Helvetica", "font_size": 9, "color": "#000000", "alignment": "right", "erase_bg": True},
                {"id": "val_tax_total", "type": "text", "name": "Total GST", "x": 500, "y": 397, "width": 80, "height": 12, "text": "₹ {{tax_total|0.00}}", "font": "Helvetica-Bold", "font_size": 9, "color": "#000000", "alignment": "right", "erase_bg": True},
                {"id": "val_round_off", "type": "text", "name": "Round Off", "x": 500, "y": 407, "width": 80, "height": 12, "text": "{{round_off|0.00}}", "font": "Helvetica", "font_size": 9, "color": "#000000", "alignment": "right", "erase_bg": True},
                {"id": "val_total_after_tax", "type": "text", "name": "Total After Tax", "x": 500, "y": 416, "width": 80, "height": 14, "text": "₹ {{amount|0.00}}", "font": "Helvetica-Bold", "font_size": 10, "color": "#1e3a5f", "alignment": "right", "erase_bg": True},
                
                # Bank & Signatory Footer Block
                {"id": "bank_name", "type": "text", "name": "Bank Holder", "x": 13, "y": 441, "width": 300, "height": 10, "text": "ACCOUNT HOLDER - {{bank_holder|NEXTUP ROBOTICS PRIVATE LIMITED}}", "font": "Helvetica", "font_size": 7.5, "color": "#000000", "alignment": "left", "erase_bg": True},
                {"id": "bank_acc", "type": "text", "name": "Account No", "x": 13, "y": 449, "width": 300, "height": 10, "text": "ACCOUNT NUMBER - {{bank_acc|0076108700000364}}", "font": "Helvetica", "font_size": 7.5, "color": "#000000", "alignment": "left", "erase_bg": True},
                {"id": "bank_ifsc", "type": "text", "name": "IFSC Code", "x": 13, "y": 457, "width": 300, "height": 10, "text": "IFSC - {{bank_ifsc|PUNB0007610}}", "font": "Helvetica", "font_size": 7.5, "color": "#000000", "alignment": "left", "erase_bg": True},
                {"id": "bank_branch", "type": "text", "name": "Bank Branch", "x": 13, "y": 466, "width": 300, "height": 10, "text": "BRANCH - {{bank_branch|PUNJAB NATIONAL BANK, RAZAPUR, GHAZIABAD}}", "font": "Helvetica", "font_size": 7.5, "color": "#000000", "alignment": "left", "erase_bg": True},
                {"id": "signatory", "type": "text", "name": "Signatory Label", "x": 380, "y": 449, "width": 200, "height": 12, "text": "For {{company_name|NextUp Robotics Pvt Ltd}}", "font": "Helvetica-Bold", "font_size": 9, "color": "#000000", "alignment": "center", "erase_bg": True},
                {"id": "auth_sign", "type": "text", "name": "Authorised Signatory", "x": 380, "y": 482, "width": 200, "height": 12, "text": "Authorised Signatory", "font": "Helvetica-Bold", "font_size": 9, "color": "#000000", "alignment": "center", "erase_bg": True}
            ]
        }

    def process_data_and_totals(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich submission data with auto-calculated subtotals, taxes, and currency words"""
        data = copy.deepcopy(data)
        
        items = data.get('items', [])
        if not items and data.get('description'):
            try:
                amt = float(data.get('amount', 0))
            except (ValueError, TypeError):
                amt = 0.0
            items = [
                {
                    "sno": 1,
                    "description": data.get('description', 'Service / Fee'),
                    "hsn": "84795000",
                    "qty": 1.0,
                    "rate": amt,
                    "taxable": amt,
                    "cgst_rate": "9%",
                    "cgst_amt": round(amt * 0.09, 2),
                    "sgst_rate": "9%",
                    "sgst_amt": round(amt * 0.09, 2),
                    "total": round(amt * 1.18, 2)
                }
            ]
            data['items'] = items

        # Calculate totals across items
        subtotal = 0.0
        cgst_total = 0.0
        sgst_total = 0.0
        igst_total = 0.0
        
        for idx, item in enumerate(items):
            item['sno'] = item.get('sno', idx + 1)
            try:
                qty = float(item.get('qty', 1))
                rate = float(item.get('rate', 0))
                taxable = float(item.get('taxable', qty * rate))
                item['taxable'] = taxable
                subtotal += taxable
                
                cgst_a = float(item.get('cgst_amt', 0))
                sgst_a = float(item.get('sgst_amt', 0))
                igst_a = float(item.get('igst_amt', 0))
                
                cgst_total += cgst_a
                sgst_total += sgst_a
                igst_total += igst_a
                
                item['total'] = item.get('total', taxable + cgst_a + sgst_a + igst_a)
            except (ValueError, TypeError):
                pass

        tax_total = cgst_total + sgst_total + igst_total
        grand_total = subtotal + tax_total
        round_off = round(round(grand_total) - grand_total, 2)
        final_amount = round(grand_total)
        
        data['subtotal'] = f"{subtotal:.2f}"
        data['cgst_total'] = f"{cgst_total:.2f}"
        data['sgst_total'] = f"{sgst_total:.2f}"
        data['igst_total'] = f"{igst_total:.2f}"
        data['tax_total'] = f"{tax_total:.2f}"
        data['round_off'] = f"{round_off:.2f}"
        
        if not data.get('amount') or data.get('amount') == '0':
            data['amount'] = f"{final_amount:.2f}"
            
        try:
            amt_num = float(data.get('amount', final_amount))
            data['amount_words'] = number_to_words_indian(amt_num)
        except (ValueError, TypeError):
            data['amount_words'] = number_to_words_indian(final_amount)
            
        if not data.get('date'):
            data['date'] = datetime.now().strftime('%d-%m-%Y')
            
        if not data.get('challanNumber'):
            data['challanNumber'] = f"CH-{datetime.now().strftime('%Y%m%d')}-{data.get('rollNo', '001')}"
            
        return data

    def generate_challan(self, data: Dict[str, Any], template_config: Optional[Dict] = None) -> bytes:
        """Generate PDF bytes from input data and template config"""
        if template_config is None:
            template_config = self.config
            
        data = self.process_data_and_totals(data)
        
        use_bg = template_config.get('use_background_pdf', True)
        bg_file = template_config.get('background_pdf', 'challan copy.pdf')
        bg_path = os.path.join(self.base_dir, bg_file)
        if not os.path.exists(bg_path):
            bg_path = self.template_path
            
        overlay_bytes = self._render_overlay(data, template_config, is_bg_active=use_bg)
        
        if use_bg and os.path.exists(bg_path):
            try:
                template_pdf = PdfReader(bg_path)
                overlay_pdf = PdfReader(io.BytesIO(overlay_bytes))
                writer = PdfWriter()
                
                for page_num in range(len(template_pdf.pages)):
                    template_page = template_pdf.pages[page_num]
                    if page_num < len(overlay_pdf.pages):
                        template_page.merge_page(overlay_pdf.pages[page_num])
                    writer.add_page(template_page)
                    
                output_buf = io.BytesIO()
                writer.write(output_buf)
                return output_buf.getvalue()
            except Exception as e:
                print(f"⚠️ Template overlay merge failed: {e}. Falling back to direct PDF render.")
                
        return overlay_bytes

    def _render_overlay(self, data: Dict[str, Any], template_config: Dict, is_bg_active: bool = True) -> bytes:
        """Render vector shapes, text, tables, and images on ReportLab canvas using Top-Left coordinates"""
        buffer = io.BytesIO()
        page_width = float(template_config.get('width_pt', 595.27))
        page_height = float(template_config.get('height_pt', 841.89))
        
        c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
        elements = template_config.get('elements', [])
        
        for elem in elements:
            elem_type = elem.get('type', 'text')
            x = float(elem.get('x', 0))
            y = float(elem.get('y', 0))
            w = float(elem.get('width', 100))
            h = float(elem.get('height', 20))
            
            rl_x = x
            rl_y = page_height - y - h
            
            # White-out Masking to erase underlying sample template text if background is active
            if is_bg_active and elem.get('erase_bg', True):
                c.setFillColor(colors.white)
                c.rect(rl_x - 1, rl_y - 1, w + 2, h + 2, fill=True, stroke=False)
            
            if elem_type == 'text':
                raw_text = elem.get('text', '')
                text_content = self._resolve_placeholders(raw_text, data)
                
                font_name = elem.get('font', 'Helvetica')
                font_size = int(elem.get('font_size', 10))
                color_hex = elem.get('color', '#000000')
                align = elem.get('alignment', 'left')
                
                c.setFont(font_name, font_size)
                try:
                    c.setFillColor(colors.HexColor(color_hex))
                except Exception:
                    c.setFillColor(colors.black)
                    
                baseline_y = rl_y + (h - font_size) / 2.0
                
                if align == 'center':
                    c.drawCentredString(rl_x + w / 2.0, baseline_y, text_content)
                elif align == 'right':
                    c.drawRightString(rl_x + w, baseline_y, text_content)
                else:
                    c.drawString(rl_x, baseline_y, text_content)
                    
            elif elem_type == 'rect':
                fill_color = elem.get('fill_color')
                stroke_color = elem.get('stroke_color', '#000000')
                line_width = float(elem.get('line_width', 1))
                
                c.setLineWidth(line_width)
                if stroke_color:
                    c.setStrokeColor(colors.HexColor(stroke_color))
                if fill_color:
                    c.setFillColor(colors.HexColor(fill_color))
                    c.rect(rl_x, rl_y, w, h, fill=True, stroke=bool(stroke_color))
                else:
                    c.rect(rl_x, rl_y, w, h, fill=False, stroke=True)
                    
            elif elem_type == 'line':
                stroke_color = elem.get('stroke_color', '#000000')
                line_width = float(elem.get('line_width', 1))
                c.setLineWidth(line_width)
                c.setStrokeColor(colors.HexColor(stroke_color))
                c.line(rl_x, rl_y + h, rl_x + w, rl_y)
                
            elif elem_type == 'table':
                self._draw_items_table(c, elem, data, rl_x, rl_y, w, h)

        c.save()
        return buffer.getvalue()

    def _draw_items_table(self, c: canvas.Canvas, elem: Dict, data: Dict, rl_x: float, rl_y: float, w: float, h: float):
        """Draw dynamic items table on canvas"""
        cols = elem.get('columns', [])
        items = data.get('items', [])
        row_h = float(elem.get('row_height', 18))
        
        font_name = elem.get('font', 'Helvetica')
        font_size = int(elem.get('font_size', 8))
        
        curr_y = rl_y + h - row_h
        
        c.setFont(font_name, font_size)
        c.setFillColor(colors.black)
        
        for item in items:
            if curr_y < rl_y:
                break
                
            curr_x = rl_x
            for col in cols:
                key = col.get('key', '')
                col_w = float(col.get('width', 40))
                align = col.get('align', 'left')
                val = str(item.get(key, ''))
                
                if isinstance(item.get(key), (int, float)):
                    val = f"{item[key]:.2f}"
                    
                baseline_y = curr_y + (row_h - font_size) / 2.0
                if align == 'center':
                    c.drawCentredString(curr_x + col_w / 2.0, baseline_y, val)
                elif align == 'right':
                    c.drawRightString(curr_x + col_w - 4, baseline_y, val)
                else:
                    c.drawString(curr_x + 4, baseline_y, val)
                    
                curr_x += col_w
                
            curr_y -= row_h

    def _resolve_placeholders(self, text: str, data: Dict[str, Any]) -> str:
        """Resolve placeholders like {{studentName|Default}} in strings"""
        if not text or "{{" not in text:
            return text
            
        import re
        pattern = r"\{\{\s*([a-zA-Z0-9_]+)(?:\|([^}]+))?\s*\}\}"
        
        def replace_match(m):
            key = m.group(1)
            default_val = m.group(2) if m.group(2) is not None else ""
            val = data.get(key)
            if val is not None and str(val).strip() != "":
                return str(val)
            return default_val
            
        return re.sub(pattern, replace_match, text)

    def render_preview_png(self, data: Dict[str, Any], template_config: Optional[Dict] = None, dpi: int = 150) -> bytes:
        """Generate live PDF preview and return PNG bytes"""
        pdf_bytes = self.generate_challan(data, template_config)
        return pdf_bytes_to_png_bytes(pdf_bytes, page_index=0, dpi=dpi)

    def save_pdf(self, data: Dict[str, Any], filename: str = None, template_config: Optional[Dict] = None) -> str:
        """Generate and save PDF file to generated directory"""
        pdf_bytes = self.generate_challan(data, template_config)
        
        if filename is None:
            roll_no = data.get('rollNo', data.get('challanNumber', 'challan'))
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"Challan_{roll_no}_{timestamp}.pdf"
            
        save_path = os.path.join(self.base_dir, 'generated', filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'wb') as f:
            f.write(pdf_bytes)
            
        return save_path


_challan_generator = None

def get_generator() -> ChallanGenerator:
    """Singleton getter for generator"""
    global _challan_generator
    if _challan_generator is None:
        _challan_generator = ChallanGenerator()
    return _challan_generator