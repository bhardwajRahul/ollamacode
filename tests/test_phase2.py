"""Tests for Phase 2 features: advanced tools, context, and error handling."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from ollamacode.tools import GitOperations, SearchOperations, BashOperations
from ollamacode.context import ContextManager
from ollamacode.config import Config
from ollamacode.error_handler import OllamaCodeError, handle_errors


class TestSearchOperations:
    def test_grep_files(self):
        """Test grep functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def hello():\n    print('Hello, world!')\n")
            
            results = SearchOperations.grep_files("def ", temp_dir)
            assert len(results) == 1
            assert results[0]["line"] == 1
            assert "def hello" in results[0]["content"]
    
    def test_find_files(self):
        """Test file finding."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            (Path(temp_dir) / "test.py").touch()
            (Path(temp_dir) / "test.js").touch()
            
            py_files = SearchOperations.find_files("*.py", temp_dir)
            assert len(py_files) == 1
            assert py_files[0].endswith("test.py")


class TestBashOperations:
    def test_run_safe_command(self):
        """Test safe command execution."""
        result = BashOperations.run_command("echo 'hello'")
        assert result["success"] is True
        assert "hello" in result["stdout"]
    
    def test_unsafe_command_blocked(self):
        """Test that unsafe commands are blocked."""
        result = BashOperations.run_command("rm -rf /")
        assert result["success"] is False
        assert "not allowed" in result["error"]
    
    def test_get_system_info(self):
        """Test system info retrieval."""
        info = BashOperations.get_system_info()
        assert "user" in info
        assert "pwd" in info


class TestContextManager:
    def test_context_creation(self):
        """Test context manager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ctx = ContextManager(temp_dir)
            assert ctx.project_root == Path(temp_dir).absolute()
            assert ctx.context_dir.exists()
    
    def test_project_type_detection(self):
        """Test project type detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Python project indicator
            (Path(temp_dir) / "pyproject.toml").touch()
            
            ctx = ContextManager(temp_dir)
            project_type = ctx.detect_project_type()
            assert project_type == "python"
    
    def test_note_management(self):
        """Test adding and retrieving notes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ctx = ContextManager(temp_dir)
            ctx.add_note("Test note")
            
            summary = ctx.get_project_summary()
            assert "Test note" in summary
    
    def test_conversation_save_load(self):
        """Test conversation persistence."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ctx = ContextManager(temp_dir)
            
            messages = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
            
            ctx.save_conversation("test_conv", messages)
            loaded = ctx.load_conversation("test_conv")
            
            assert loaded == messages


class TestConfig:
    def test_config_defaults(self):
        """Test default configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Use temporary config directory
            config = Config()
            config.config_dir = Path(temp_dir)
            config.config_file = config.config_dir / "config.json"
            config._config = config._load_config()
            
            assert config.get("default_model") == "gemma3"
            assert config.get("ollama_url") == "http://localhost:11434"
    
    def test_config_set_get(self):
        """Test setting and getting config values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            config.config_dir = Path(temp_dir)
            config.config_file = config.config_dir / "config.json"
            config._config = config._load_config()
            
            config.set("test_key", "test_value")
            assert config.get("test_key") == "test_value"


class TestErrorHandler:
    def test_error_decorator(self):
        """Test error handling decorator."""
        @handle_errors
        def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(SystemExit):
            failing_function()
    
    def test_keyboard_interrupt_handling(self):
        """Test graceful keyboard interrupt handling."""
        @handle_errors
        def interrupted_function():
            raise KeyboardInterrupt()
        
        with pytest.raises(SystemExit) as exc_info:
            interrupted_function()
        
        assert exc_info.value.code == 0  # Should exit with code 0 for user cancellation