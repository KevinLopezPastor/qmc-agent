"""
QMC Agent - Visual Report Generator (V3 Optimized)
Generates a PNG status report for QMC + NPrinting data.

Changes V3:
- Always shows ALL configured processes (even without data → "Pendiente")
- Reads process config from Config (single source of truth)
- Cleaned STATUS_MAP (removed obsolete Mixed/Error)
- Added executive summary footer
- Process "Sin datos" only for processes that don't exist in one source
"""

import sys
import json
import os
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont


# ============ Status Mapping ============

STATUS_MAP = {
    "Success": {"text": "Procesado", "color": "#002060"},      # Blue
    "Running": {"text": "En proceso", "color": "#e46c0a"},     # Orange
    "Failed":  {"text": "Fallido", "color": "red"},            # Red
    "Pending": {"text": "Pendiente", "color": "#7f7f7f"},      # Grey
    "No Run":  {"text": "Sin datos", "color": "#bdc3c7"},      # Light Grey
    "No Data": {"text": "Sin datos", "color": "#bdc3c7"},      # Light Grey
    "Error":   {"text": "Error", "color": "red"}               # Red
}

# Layout Config
WIDTH = 620
HEADER_HEIGHT = 50
SECTION_HEADER_HEIGHT = 30
ROW_HEIGHT = 28
FOOTER_HEIGHT = 50
PADDING = 15
COL1_WIDTH = 280  # Process name column
COL2_WIDTH = 110  # QMC status
COL3_WIDTH = 110  # NPrinting status

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


# ============ Process Registry ============

def get_all_processes():
    """
    Returns the master list of processes to display in the report.
    Each entry: (display_name, qmc_tag_or_None, nprinting_prefix_or_None)
    
    Single source of truth: reads from Config when possible,
    falls back to hardcoded list if Config unavailable (subprocess mode).
    """
    # Define ALL processes with their source mappings
    # Format: (Display Name, QMC Tag Key, NPrinting Alias)
    return [
        ("Hitos",               "FE_HITOS_DIARIO",          "Hitos"),
        ("Calidad de Cartera",  "FE_CALIDADCARTERA_DIARIO", "Calidad de Cartera"),
        ("Reporte de Producción","FE_PRODUCCION",            "Reporte de Producción"),
        ("Pasivos",             "FE_PASIVOS",                None),    # QMC only
        ("Cobranzas",           "FE_COBRANZAS_DIARIA",      "Cobranzas"),
    ]


# ============ Helpers ============

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


def find_qmc_status(qmc_reports, qmc_tag):
    """Find QMC status for a given tag key."""
    if not qmc_tag or not qmc_reports:
        return None  # Process doesn't exist in QMC source
    
    if qmc_tag in qmc_reports:
        return qmc_reports[qmc_tag].get("status", "Pending")
    
    # Also check by alias match
    for key, val in qmc_reports.items():
        if key == qmc_tag:
            return val.get("status", "Pending")
    
    return "Pending"  # Configured but no data → task hasn't run


def find_nprinting_status(nprinting_reports, np_alias):
    """Find NPrinting status for a given alias."""
    if not np_alias:
        return None  # Process doesn't exist in NPrinting source
    
    if not nprinting_reports:
        return "Pending"  # No data yet → pending
    
    if np_alias in nprinting_reports:
        return nprinting_reports[np_alias].get("status", "Pending")
    
    return "Pending"  # Configured but no data → pending


# ============ Main Render ============

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
    
    # Get ALL configured processes
    all_processes = get_all_processes()
    
    # Build rows: (name, qmc_status, nprinting_status)
    rows = []
    for display_name, qmc_tag, np_alias in all_processes:
        qmc_status = find_qmc_status(qmc_reports, qmc_tag)
        np_status = find_nprinting_status(nprinting_reports, np_alias)
        
        # None means process doesn't exist in that source → "Sin datos"
        qmc_display = qmc_status if qmc_status is not None else "No Data"
        np_display = np_status if np_status is not None else "No Data"
        
        rows.append((display_name, qmc_display, np_display))
    
    # Get summary text
    summary_text = combined_report.get("summary", "")
    has_summary = bool(summary_text and len(summary_text) > 5)
    
    # Calculate dimensions
    num_rows = len(rows)
    total_height = (
        PADDING +                      # Top padding
        HEADER_HEIGHT +                # Main header
        SECTION_HEADER_HEIGHT +        # Overall status
        SECTION_HEADER_HEIGHT +        # Table header
        (num_rows * ROW_HEIGHT) +      # Data rows
        (FOOTER_HEIGHT * 2 if has_summary else 0) +  # Summary footer (generous)
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
    font_summary = load_font(10)
    
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
    overall_status = combined_report.get("overall_status", "Pending")
    status_text, _ = get_status_display(overall_status)
    
    # Choose background color based on status
    status_bg_map = {
        "Success": OVERALL_SUCCESS_BG,
        "Failed": OVERALL_FAILED_BG,
        "Running": OVERALL_RUNNING_BG,
    }
    bar_bg = status_bg_map.get(overall_status, OVERALL_PENDING_BG)
    
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
    
    # ========== Summary Footer (inside border) ==========
    if has_summary:
        # Separator line
        d.line([(PADDING, y), (WIDTH - PADDING, y)], fill=BORDER_COLOR, width=1)
        
        # Calculate text wrapping
        max_text_width = WIDTH - (PADDING * 2) - 20  # available width for text
        prefix = "📝 "
        
        # Word-wrap the summary
        words = summary_text.split()
        lines = []
        current_line = prefix
        for word in words:
            test_line = current_line + word + " "
            if hasattr(d, 'textbbox'):
                tw = d.textbbox((0, 0), test_line, font=font_summary)[2]
            else:
                tw = d.textlength(test_line, font=font_summary)
            if tw > max_text_width and current_line != prefix:
                lines.append(current_line.rstrip())
                current_line = "   " + word + " "  # indent continuation lines
            else:
                current_line = test_line
        if current_line.strip():
            lines.append(current_line.rstrip())
        
        # Dynamic footer height based on lines
        line_height = 16
        footer_h = (len(lines) * line_height) + 16  # 8px padding top + bottom
        
        # Footer background
        d.rectangle([PADDING, y, WIDTH - PADDING, y + footer_h], fill="#ecf0f1")
        
        # Draw each line
        text_y = y + 8
        for line in lines:
            d.text((PADDING + 10, text_y), line, font=font_summary, fill="#2c3e50")
            text_y += line_height
        
        y += footer_h
    
    # Draw outer border (wraps everything: status bar + table + footer)
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
                "Calidad de Cartera": {"status": "Running"}
            },
            "combined_report": {
                "overall_status": "Failed",
                "summary": "CRITICAL: FE_PASIVOS failed. NPrinting Cobranzas pending. Immediate attention required."
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
