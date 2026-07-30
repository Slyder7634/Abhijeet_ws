"""
Utility functions for PDF generation, currency conversion, and QR codes
"""

import io
import math
from typing import Union
import fitz  # PyMuPDF
from PIL import Image

def number_to_words_indian(number: Union[int, float]) -> str:
    """
    Convert a number to Indian currency representation in words.
    E.g. 12345.50 -> "Rupees Twelve Thousand Three Hundred Forty-Five and Fifty Paise Only"
    """
    if number is None:
        return "Rupees Zero Only"
    
    try:
        num = float(number)
    except (ValueError, TypeError):
        return str(number)
        
    if num == 0:
        return "Rupees Zero Only"
        
    is_negative = num < 0
    num = abs(num)
    
    rupees = int(num)
    paise = int(round((num - rupees) * 100))
    
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", 
             "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    def convert_below_thousand(n: int) -> str:
        words = ""
        if n >= 100:
            words += units[n // 100] + " Hundred "
            n %= 100
        if n >= 20:
            words += tens[n // 10] + " "
            n %= 10
        elif n >= 10:
            words += teens[n - 10] + " "
            n = 0
        if n > 0:
            words += units[n] + " "
        return words.strip()

    def convert_rupees(n: int) -> str:
        if n == 0:
            return ""
            
        crores = n // 10000000
        n %= 10000000
        
        lakhs = n // 100000
        n %= 100000
        
        thousands = n // 1000
        n %= 1000
        
        hundreds = n
        
        res = ""
        if crores > 0:
            res += convert_below_thousand(crores) + " Crore "
        if lakhs > 0:
            res += convert_below_thousand(lakhs) + " Lakh "
        if thousands > 0:
            res += convert_below_thousand(thousands) + " Thousand "
        if hundreds > 0:
            res += convert_below_thousand(hundreds) + " "
            
        return res.strip()

    rupees_str = convert_rupees(rupees)
    if not rupees_str:
        rupees_str = "Zero"
        
    result = "Rupees " + rupees_str
    
    if paise > 0:
        paise_str = convert_below_thousand(paise)
        result += f" and {paise_str} Paise"
        
    result += " Only"
    if is_negative:
        result = "Minus " + result
        
    return result

def pdf_bytes_to_png_bytes(pdf_bytes: bytes, page_index: int = 0, dpi: int = 150) -> bytes:
    """Render a PDF page to PNG image bytes"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if page_index >= len(doc):
        page_index = 0
    page = doc[page_index]
    pix = page.get_pixmap(dpi=dpi)
    return pix.tobytes("png")

if __name__ == "__main__":
    print(number_to_words_indian(12345.50))
    print(number_to_words_indian(84795.00))
    print(number_to_words_indian(0))