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
    TIMEOUT_MS: int = int(os.getenv("TIMEOUT_MS", "60000")) # Increased timeout
    
    # Search/Pagination
    PAGINATION_MAX_CLICKS: int = int(os.getenv("PAGINATION_MAX_CLICKS", "10"))
    
    # Process Monitoring
    # Format: tag_name:alias (optional)
    MONITORED_PROCESSES = {
        "FE_HITOS_DIARIO": "Hitos",
        "FE_COBRANZAS_DIARIA": "Cobranzas",
        "FE_PASIVOS": "Pasivos", 
        "FE_PRODUCCION": "Produccion",
        "FE_CALIDADCARTERA_DIARIO": "Calidad Cartera"
    }

    # CSS Selectors
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
