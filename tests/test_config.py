"""
QMC Agent - Configuration Tests
"""

import pytest
import os
from unittest.mock import patch


class TestConfig:
    """Test configuration loading and validation."""
    
    def test_config_loads_defaults(self):
        """Test that Config loads default values."""
        from src.config import Config
        
        assert Config.QMC_URL == "https://apqs.grupoefe.pe/qmc/tasks"
        assert Config.MAX_RETRIES == 3
        assert Config.TIMEOUT_MS == 30000
    
    def test_config_has_selectors(self):
        """Test that Config has required CSS selectors."""
        from src.config import Config
        
        assert "username_input" in Config.SELECTORS
        assert "password_input" in Config.SELECTORS
        assert "spinner" in Config.SELECTORS
        assert "grid" in Config.SELECTORS
    
    def test_validate_missing_credentials(self):
        """Test validation reports missing credentials."""
        from src.config import Config
        
        # Clear env vars for test
        with patch.dict(os.environ, {
            "QMC_USERNAME": "",
            "QMC_PASSWORD": "",
            "GROQ_API_KEY": ""
        }, clear=True):
            # Re-import to pick up patched values
            import importlib
            import src.config
            importlib.reload(src.config)
            
            missing = src.config.Config.validate()
            assert "QMC_USERNAME" in missing or len(missing) > 0
    
    def test_validate_with_credentials(self):
        """Test validation passes with credentials."""
        with patch.dict(os.environ, {
            "QMC_USERNAME": "testuser",
            "QMC_PASSWORD": "testpass",
            "GROQ_API_KEY": "gsk_test"
        }):
            import importlib
            import src.config
            importlib.reload(src.config)
            
            missing = src.config.Config.validate()
            assert len(missing) == 0


class TestState:
    """Test state creation and structure."""
    
    def test_create_initial_state(self):
        """Test initial state has correct structure."""
        from src.state import create_initial_state
        
        state = create_initial_state()
        
        assert state["current_step"] == "init"
        assert state["retry_count"] == 0
        assert state["max_retries"] == 3
        assert state["session_cookies"] is None
        assert state["structured_data"] is None
        assert state["screenshots"] == []
        assert state["logs"] == []
    
    def test_state_is_dict(self):
        """Test that state is a proper dict."""
        from src.state import create_initial_state
        
        state = create_initial_state()
        
        assert isinstance(state, dict)
        assert "current_step" in state


class TestAnalyst:
    """Test analyst schema and utilities."""
    
    def test_qmc_task_schema(self):
        """Test QMCTask Pydantic model."""
        from src.analyst import QMCTask
        
        task = QMCTask(
            Name="Test Task",
            Status="Success",
            Last_execution="2024-01-26T14:30:00",
            Next_execution=None,
            Tags=["FE_HITOS"]
        )
        
        assert task.Name == "Test Task"
        assert task.Status == "Success"
        assert "FE_HITOS" in task.Tags
    
    def test_qmc_task_list_schema(self):
        """Test QMCTaskList Pydantic model."""
        from src.analyst import QMCTaskList
        
        task_list = QMCTaskList(tasks=[
            {"Name": "Task1", "Status": "Success", "Tags": []},
            {"Name": "Task2", "Status": "Failed", "Tags": ["TAG1"]}
        ])
        
        assert len(task_list.tasks) == 2
