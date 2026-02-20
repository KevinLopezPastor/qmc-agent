"""
QMC Agent - Visual Report Generator (Unified Version)
Generates a PNG status report for QMC + NPrinting data.
"""

import sys
import json
import os
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

# ============ Configuration ============

# QMC Process Aliases
QMC_ALIAS = {
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

# NPrinting uses aliases directly from config (h. -> Hitos, etc.)

STATUS_MAP = {
    "Success": {"text": "Procesado", "color": "#002060"},     # Blue
    "Running": {"text": "En proceso", "color": "#e46c0a"},    # Orange
    "Failed": {"text": "Fallido", "color": "red"},            # Red
    "Pending": {"text": "Pendiente", "color": "#7f7f7f"},     # Grey
    "No Run": {"text": "Sin datos", "color": "#7f7f7f"},      # Grey
    "No Data": {"text": "Sin datos", "color": "#7f7f7f"},     # Grey
    "Mixed": {"text": "Mixto", "color": "#9b59b6"},           # Purple
    "Error": {"text": "Error", "color": "red"}                # Red
}

# Layout Config
WIDTH = 600
HEADER_HEIGHT = 50
SECTION_HEADER_HEIGHT = 30
ROW_HEIGHT = 28
PADDING = 15
COL1_WIDTH = 280  # Process name column
COL2_WIDTH = 100  # QMC status
COL3_WIDTH = 100  # NPrinting status

# Colors
BG_COLOR = "#f5f5f5"
TABLE_HEADER_BG = "#2c3e50"
SECTION_BG = "#34495e"
TABLE_HEADER_TEXT = "white"
BORDER_COLOR = "#bdc3c7"
TEXT_COLOR = "#2c3e50"
OVERALL_SUCCESS_BG = "#27ae60"
OVERALL_FAILED_BG = "#e74c3c"
OVERALL_RUNNING_BG = "#f39c12"
OVERALL_PENDING_BG = "#95a5a6"


def load_font(size, bold=False):
    """Load a nice font, fallback to default."""
    fonts_to_try = [
        "arialbd.ttf" if bold else "arial.ttf",
        "seguiemj.ttf",
        "calibri.ttf"
    ]
    for font_name in fonts_to_try:
        try:
            return ImageFont.truetype(font_name, size)
        except:
            continue
    return ImageFont.load_default()


def get_status_display(status_key):
    """Get display text and color for status."""
    config = STATUS_MAP.get(status_key, STATUS_MAP.get("No Data"))
    return config["text"], config["color"]


def run(args):
    """Generate unified report image."""
    qmc_reports = args.get("qmc_reports") or args.get("reports") or {}
    nprinting_reports = args.get("nprinting_reports") or {}
    combined_report = args.get("combined_report") or {}
    output_path = args.get("output_path", "unified_report.png")
    
    # Dates
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    months = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", 
              "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    date_str = f"{yesterday.day}.{months[yesterday.month - 1]}"
    time_str = now.strftime("%I:%M%p").lower()
    
    # Prepare unified rows
    # Merge QMC and NPrinting by common process names
    process_names = set()
    
    # Collect all process names
    for key, val in qmc_reports.items():
        alias = QMC_ALIAS.get(key, val.get("alias", key))
        process_names.add(alias)
    
    for key, val in nprinting_reports.items():
        # NPrinting uses alias directly as key (Hitos, Cobranzas, etc.)
        process_names.add(key)
    
    # Priority order for display
    priority = ["Hitos", "Calidad Cartera", "Produccion", "Pasivos", "Cobranzas", "Interfaces"]
    sorted_names = []
    for p in priority:
        if p in process_names:
            sorted_names.append(p)
            process_names.discard(p)
    sorted_names.extend(sorted(process_names))
    
    # Build rows: (name, qmc_status, nprinting_status)
    rows = []
    for name in sorted_names:
        qmc_status = "No Data"
        nprinting_status = "No Data"
        
        # Find QMC status
        for key, val in qmc_reports.items():
            alias = QMC_ALIAS.get(key, val.get("alias", key))
            if alias == name:
                qmc_status = val.get("status", "No Data")
                break
        
        # Find NPrinting status
        if name in nprinting_reports:
            nprinting_status = nprinting_reports[name].get("status", "No Data")
        
        rows.append((name, qmc_status, nprinting_status))
    
    # Calculate dimensions
    num_rows = len(rows)
    total_height = (
        PADDING +                      # Top padding
        HEADER_HEIGHT +                # Main header
        SECTION_HEADER_HEIGHT +        # Overall status
        SECTION_HEADER_HEIGHT +        # Table header
        (num_rows * ROW_HEIGHT) +      # Data rows
        PADDING                        # Bottom padding
    )
    
    # Create image
    img = Image.new('RGB', (WIDTH, total_height), color=BG_COLOR)
    d = ImageDraw.Draw(img)
    
    # Fonts
    font_title = load_font(18, bold=True)
    font_header = load_font(14, bold=True)
    font_normal = load_font(12)
    font_status = load_font(11, bold=True)
    
    y = PADDING
    
    # ========== Header ==========
    d.text((PADDING, y + 5), f"📊 Reporte Unificado - {date_str}", font=font_title, fill=TEXT_COLOR)
    
    # Time on right
    time_text = f"Corte: {time_str}"
    if hasattr(d, 'textbbox'):
        tw = d.textbbox((0, 0), time_text, font=font_normal)[2]
    else:
        tw = d.textlength(time_text, font=font_normal)
    d.text((WIDTH - PADDING - tw, y + 8), time_text, font=font_normal, fill=TEXT_COLOR)
    
    y += HEADER_HEIGHT
    
    # ========== Overall Status Bar ==========
    overall_status = combined_report.get("overall_status", "No Data")
    status_text, _ = get_status_display(overall_status)
    
    # Choose background color based on status
    if overall_status == "Success":
        bar_bg = OVERALL_SUCCESS_BG
    elif overall_status == "Failed":
        bar_bg = OVERALL_FAILED_BG
    elif overall_status == "Running":
        bar_bg = OVERALL_RUNNING_BG
    else:
        bar_bg = OVERALL_PENDING_BG
    
    d.rectangle([PADDING, y, WIDTH - PADDING, y + SECTION_HEADER_HEIGHT], fill=bar_bg)
    overall_label = f"Estado General: {status_text.upper()}"
    d.text((PADDING + 10, y + 6), overall_label, font=font_header, fill="white")
    
    y += SECTION_HEADER_HEIGHT + 5
    
    # ========== Table Header ==========
    d.rectangle([PADDING, y, WIDTH - PADDING, y + SECTION_HEADER_HEIGHT], fill=TABLE_HEADER_BG)
    
    # Column headers
    col1_x = PADDING + 10
    col2_x = PADDING + COL1_WIDTH
    col3_x = col2_x + COL2_WIDTH
    
    d.text((col1_x, y + 7), "Proceso", font=font_header, fill=TABLE_HEADER_TEXT)
    d.text((col2_x + 15, y + 7), "QMC", font=font_header, fill=TABLE_HEADER_TEXT)
    d.text((col3_x + 10, y + 7), "NPrinting", font=font_header, fill=TABLE_HEADER_TEXT)
    
    y += SECTION_HEADER_HEIGHT
    
    # ========== Data Rows ==========
    for i, (name, qmc_status, np_status) in enumerate(rows):
        # Alternating row background
        row_bg = "white" if i % 2 == 0 else "#ecf0f1"
        d.rectangle([PADDING, y, WIDTH - PADDING, y + ROW_HEIGHT], fill=row_bg)
        
        # Draw borders
        d.line([(PADDING, y + ROW_HEIGHT), (WIDTH - PADDING, y + ROW_HEIGHT)], fill=BORDER_COLOR)
        d.line([(col2_x, y), (col2_x, y + ROW_HEIGHT)], fill=BORDER_COLOR)
        d.line([(col3_x, y), (col3_x, y + ROW_HEIGHT)], fill=BORDER_COLOR)
        
        # Process name
        d.text((col1_x, y + 6), name, font=font_normal, fill=TEXT_COLOR)
        
        # QMC Status
        qmc_text, qmc_color = get_status_display(qmc_status)
        d.text((col2_x + 10, y + 6), qmc_text, font=font_status, fill=qmc_color)
        
        # NPrinting Status
        np_text, np_color = get_status_display(np_status)
        d.text((col3_x + 10, y + 6), np_text, font=font_status, fill=np_color)
        
        y += ROW_HEIGHT
    
    # Draw outer border
    d.rectangle([PADDING, PADDING + HEADER_HEIGHT, WIDTH - PADDING, y], outline=BORDER_COLOR, width=1)
    
    # Save
    img.save(output_path)
    return {"success": True, "output_path": output_path}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Test mode
        print("Running test mode...")
        test_args = {
            "qmc_reports": {
                "FE_HITOS_DIARIO": {"status": "Success"},
                "FE_COBRANZAS_DIARIA": {"status": "Running"},
                "FE_PASIVOS": {"status": "Failed"}
            },
            "nprinting_reports": {
                "Hitos": {"status": "Success"},
                "Cobranzas": {"status": "Pending"},
                "Calidad Cartera": {"status": "Running"}
            },
            "combined_report": {
                "overall_status": "Failed"
            },
            "output_path": "test_unified_report.png"
        }
        res = run(test_args)
        print(res)
    else:
        try:
            args_input = json.loads(sys.argv[1])
            result = run(args_input)
            print(json.dumps(result))
        except Exception as e:
            print(json.dumps({"success": False, "error": str(e)}))
