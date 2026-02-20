"""
QMC Agent - Configuration Module
Loads environment variables and provides configuration constants.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for QMC Agent."""
    
    # QMC Connection
    QMC_URL: str = os.getenv("QMC_URL", "https://apqs.grupoefe.pe/qmc/tasks")
    QMC_USERNAME: str = os.getenv("QMC_USERNAME", "")
    QMC_PASSWORD: str = os.getenv("QMC_PASSWORD", "")
    
    # Groq LLM
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    # Scraping Configuration
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"
    TIMEOUT_MS: int = int(os.getenv("TIMEOUT_MS", "60000"))
    
    # Search/Pagination
    PAGINATION_MAX_CLICKS: int = int(os.getenv("PAGINATION_MAX_CLICKS", "10"))
    
    # Process Monitoring
    # Format: tag_name:alias (optional)
    MONITORED_PROCESSES = {
        "FE_HITOS_DIARIO": "Hitos",
        "FE_COBRANZAS_DIARIA": "Cobranzas",
        "FE_PASIVOS": "Pasivos", 
        "FE_PRODUCCION": "Reporte de Producción",
        "FE_CALIDADCARTERA_DIARIO": "Calidad de Cartera"
    }

    # CSS Selectors (QMC)
    SELECTORS = {
        # Login
        "username_input": "input[type='text'], input[name='username'], #username",
        "password_input": "input[type='password'], input[name='password'], #password",
        "login_button": "button[type='submit'], .login-button",
        
        # General
        "spinner": ".qv-loader, .spinner, .loading-indicator, .lui-spinner",
        
        # Filters
        "last_execution_filter": "th:has-text('Last execution'), .header-cell:has-text('Last'), [data-tid*='last']",
        "today_option": ".lui-select-option:has-text('Today'), option:has-text('Today'), div:has-text('Today')",
        
        # Pagination
        "show_more_button": "button:has-text('Show more'), .lui-button:has-text('Show more'), [title='Show more']",
        
        # Data Extraction
        "table_rows": "tbody tr, .lui-list-item, .qmc-row"
    }
    
    # ==================== NPrinting Configuration ====================
    
    # NPrinting Connection
    NPRINTING_URL: str = os.getenv("NPRINTING_URL", "https://10.142.16.45:4993/#/tasks/executions")
    NPRINTING_EMAIL: str = os.getenv("NPRINTING_EMAIL", "")
    NPRINTING_PASSWORD: str = os.getenv("NPRINTING_PASSWORD", "")
    
    # NPrinting Process Monitoring (prefix patterns)
    # Format: prefix_pattern: alias
    NPRINTING_MONITORED = {
        "h.": "Hitos",                     # e.g., h. Tablero Eficiencia Comercial
        "q1.": "Calidad de Cartera",       # e.g., q1. Reporte Calidad
        "k.": "Reporte de Producción",     # e.g., k. Reporte Produccion
        "x.": "Cobranzas",                 # e.g., x.Cobranza Diaria
    }
    
    # NPrinting CSS Selectors
    NPRINTING_SELECTORS = {
        # Login
        "email_input": "input[type='email'], input[name='email'], input[placeholder*='mail']",
        "password_input": "input[type='password']",
        "login_button": "button[type='submit'], button:has-text('Log in'), button:has-text('Sign in')",
        
        # Date Filter
        "date_filter_dropdown": "select, .dropdown, [role='listbox'], .filter-dropdown",
        "today_option": "option:has-text('Today'), [role='option']:has-text('Today'), li:has-text('Today')",
        
        # Pagination
        "pagination_100": "button:has-text('100'), .pagination button:has-text('100'), [aria-label='100']",
        
        # Table
        "table": "table, .data-table, [role='grid']",
        "table_rows": "tbody tr, .task-row, [role='row']",
        "table_headers": "thead th, .header-cell, [role='columnheader']"
    }
    
    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration files."""
        missing = []
        if not cls.QMC_USERNAME:
            missing.append("QMC_USERNAME")
        if not cls.QMC_PASSWORD:
            missing.append("QMC_PASSWORD")
        if not cls.GROQ_API_KEY:
            missing.append("GROQ_API_KEY")
        return missing
    
    @classmethod
    def validate_nprinting(cls) -> list[str]:
        """Validate NPrinting configuration."""
        missing = []
        if not cls.NPRINTING_EMAIL:
            missing.append("NPRINTING_EMAIL")
        if not cls.NPRINTING_PASSWORD:
            missing.append("NPRINTING_PASSWORD")
        return missing
