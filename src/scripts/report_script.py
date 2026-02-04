"""
QMC Agent - Visual Report Generator (PIL Version)
Generates a PNG status report using native Python imaging (Lightweight, No Playwright).
"""

import sys
import json
import os
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

# 1. Configuration
PROCESS_ALIAS = {
    "FE_HITOS": "Hitos",
    "FE_HITOS_DIARIO": "Hitos",
    "FE_COBRANZAS": "Cobranzas", 
    "FE_COBRANZAS_DIARIA": "Cobranzas",
    "FE_PASIVOS": "Pasivos",
    "FE_PRODUCCION": "Reporte de Producción",
    "FE_CALIDADCARTERA": "Calidad de Cartera",
    "FE_CALIDADCARTERA_DIARIO": "Calidad de Cartera",
    "FE_INTERFACES_DIARIA": "Interfaces"
}

STATUS_MAP = {
    "Success": {"text": "Procesado", "color": "#002060"},     # Blue
    "Running": {"text": "En proceso", "color": "#e46c0a"},    # Orange
    "Failed": {"text": "Fallido", "color": "red"},            # Red
    "Pending": {"text": "Pendiente", "color": "#7f7f7f"},     # Grey
    "No Run": {"text": "Pendiente", "color": "#7f7f7f"}       # Fallback
}

# Layout Config
WIDTH = 500
HEADER_HEIGHT = 40
ROW_HEIGHT = 30
PADDING = 20

# Colors
BG_COLOR = "white"
TABLE_HEADER_BG = "#4f81bd"
TABLE_HEADER_TEXT = "white"
BORDER_COLOR = "#95b3d7"
TEXT_COLOR = "black"

def load_font(size):
    """Load a nice font, fallback to default."""
    try:
        # Try common Windows fonts
        return ImageFont.truetype("arial.ttf", size)
    except:
        try:
            return ImageFont.truetype("seguiemj.ttf", size)
        except:
            # Fallback to default (ugly but works)
            return ImageFont.load_default()

def run(args):
    reports = args.get("reports", {})
    output_path = args.get("output_path", "qmc_report_pil.png")
    
    # Dates
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    months = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    date_str = f"{yesterday.day}.{months[yesterday.month - 1]}"
    time_str = now.strftime("%I:%M%p").lower()
    
    # 1. Prepare Data Rows (Sorted)
    priority_order = [
         "FE_INTERFACES_DIARIA", "FE_HITOS_DIARIO", "FE_CALIDADCARTERA_DIARIO", 
         "FE_PRODUCCION", "FE_PASIVOS", "FE_COBRANZAS_DIARIA"
    ]
    
    final_rows = []
    processed_keys = set()
    
    # Process Priority Items
    for key in priority_order:
        match_key = None
        if key in reports:
            match_key = key
        else:
             for rk in reports.keys():
                 if rk in key or key in rk:
                     match_key = rk
                     break
        
        if match_key and match_key not in processed_keys:
             status_key = reports[match_key].get("status", "No Run")
             name_display = PROCESS_ALIAS.get(key, key) # Use config alias
             final_rows.append((name_display, status_key))
             processed_keys.add(match_key)
             
    # Add Remaining
    for key, data in reports.items():
        if key not in processed_keys:
             status_key = data.get("status", "No Run")
             name_display = PROCESS_ALIAS.get(key, key)
             final_rows.append((name_display, status_key))
    
    # 2. Calculate Image Dimensions
    num_rows = len(final_rows)
    # Header + Table Header + Rows + Padding
    total_height = HEADER_HEIGHT + ROW_HEIGHT + (num_rows * ROW_HEIGHT) + (PADDING * 2)
    
    # 3. Draw Image
    img = Image.new('RGB', (WIDTH, total_height), color=BG_COLOR)
    d = ImageDraw.Draw(img)
    
    # Fonts
    font_bold = load_font(16)
    font_normal = load_font(14)
    # Hack for bold if strictly loading default? No, just use same logic.
    # For default font, size is ignored.
    
    # Draw Top Header (Date/Time)
    # "Carga al : [date]" ------ "Corte: [time]"
    d.text((PADDING, PADDING), f"Carga al: {date_str}", font=font_bold, fill="black")
    
    # Calculate right alignment for time
    # Check text width
    if hasattr(d, 'textbbox'): # Newer Pillow
        bbox = d.textbbox((0, 0), f"Corte: {time_str}", font=font_bold)
        text_w = bbox[2] - bbox[0]
    else:
        text_w = d.textlength(f"Corte: {time_str}", font=font_bold)
        
    d.text((WIDTH - PADDING - text_w, PADDING), f"Corte: {time_str}", font=font_bold, fill="black")
    
    # Draw Table Header
    table_start_y = PADDING + HEADER_HEIGHT
    # Header Row Box
    d.rectangle([PADDING, table_start_y, WIDTH - PADDING, table_start_y + ROW_HEIGHT], fill=TABLE_HEADER_BG)
    
    # Header Text
    d.text((PADDING + 5, table_start_y + 5), "Tareas", font=font_bold, fill=TABLE_HEADER_TEXT)
    # Center "QS"
    col2_x = WIDTH // 2 + 50 # Approximate start of col 2
    d.text((col2_x, table_start_y + 5), "QS", font=font_bold, fill=TABLE_HEADER_TEXT)
    
    # Draw Rows
    y = table_start_y + ROW_HEIGHT
    
    for process_name, status_key in final_rows:
        # Row Box (Border only)
        # d.rectangle([PADDING, y, WIDTH - PADDING, y + ROW_HEIGHT], outline=BORDER_COLOR)
        
        # We draw borders manually for cleaner look
        # Bottom Line
        d.line([(PADDING, y + ROW_HEIGHT), (WIDTH - PADDING, y + ROW_HEIGHT)], fill=BORDER_COLOR)
        # Vertical Line Middle
        # d.line([(col2_x - 10, y), (col2_x - 10, y + ROW_HEIGHT)], fill=BORDER_COLOR)
        # Left/Right Borders
        d.line([(PADDING, y), (PADDING, y + ROW_HEIGHT)], fill=BORDER_COLOR)
        d.line([(WIDTH - PADDING, y), (WIDTH - PADDING, y + ROW_HEIGHT)], fill=BORDER_COLOR)
        
        # Text Col 1 (Name)
        d.text((PADDING + 5, y + 5), process_name, font=font_normal, fill="black")
        
        # Text Col 2 (Status)
        st_config = STATUS_MAP.get(status_key, STATUS_MAP["Failed"])
        st_text = st_config["text"]
        st_color = st_config["color"]
        
        # Center align status text roughly
        # d.text((col2_x, y + 5), st_text, font=font_bold, fill=st_color)
        
        # Improve centering if possible
        if hasattr(d, 'textbbox'):
             st_w = d.textbbox((0,0), st_text, font=font_bold)[2]
        else:
             st_w = d.textlength(st_text, font=font_bold)
             
        # Center of remaining space? Let's just indent fixed
        d.text((col2_x, y + 5), st_text, font=font_bold, fill=st_color)
        
        y += ROW_HEIGHT
        
    img.save(output_path)
    return {"success": True, "output_path": output_path}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Test mode
        print("Running test mode...")
        res = run({"reports": {"FE_HITOS": {"status": "Success"}, "FE_TEST": {"status": "Running"}}})
        print(res)
    else:
        try:
            args_input = json.loads(sys.argv[1])
            result = run(args_input)
            print(json.dumps(result))
        except Exception as e:
            print(json.dumps({"success": False, "error": str(e)}))
