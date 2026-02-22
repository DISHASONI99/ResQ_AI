"""
Logging Configuration - Centralized logging for the entire application

Provides detailed, colored logs with:
- Timestamps with milliseconds
- Log levels (INFO, SUCCESS, WARNING, ERROR, DB, EMBED, AGENT)
- Indentation for nested operations
- File + console output
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    COLORS = {
        "DEBUG": "\033[90m",     # Gray
        "INFO": "\033[94m",      # Blue
        "SUCCESS": "\033[92m",   # Green
        "WARNING": "\033[93m",   # Yellow
        "ERROR": "\033[91m",     # Red
        "CRITICAL": "\033[91m\033[1m",  # Bold Red
        "DB": "\033[96m",        # Cyan
        "EMBED": "\033[95m",     # Magenta
        "AGENT": "\033[93m",     # Yellow
        "RESET": "\033[0m",
    }
    
    def format(self, record):
        # Add color based on level
        color = self.COLORS.get(record.levelname, self.COLORS["INFO"])
        reset = self.COLORS["RESET"]
        
        # Format timestamp
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Get indent if set
        indent = getattr(record, "indent", 0)
        prefix = "  " * indent
        
        # Build message
        levelname = record.levelname[:7].ljust(7)
        formatted = f"{color}[{timestamp}] [{levelname}] {prefix}{record.getMessage()}{reset}"
        
        return formatted


class PlainFormatter(logging.Formatter):
    """Plain formatter for file output."""
    
    def format(self, record):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        indent = getattr(record, "indent", 0)
        prefix = "  " * indent
        levelname = record.levelname[:7].ljust(7)
        return f"[{timestamp}] [{levelname}] {prefix}{record.getMessage()}"


# Add custom log levels
SUCCESS = 25
DB = 26
EMBED = 27
AGENT = 28

logging.addLevelName(SUCCESS, "SUCCESS")
logging.addLevelName(DB, "DB")
logging.addLevelName(EMBED, "EMBED")
logging.addLevelName(AGENT, "AGENT")


class AppLogger(logging.Logger):
    """Extended logger with custom methods."""
    
    def success(self, msg, *args, indent=0, **kwargs):
        if self.isEnabledFor(SUCCESS):
            self._log(SUCCESS, msg, args, extra={"indent": indent}, **kwargs)
    
    def db(self, msg, *args, indent=0, **kwargs):
        if self.isEnabledFor(DB):
            self._log(DB, msg, args, extra={"indent": indent}, **kwargs)
    
    def embed(self, msg, *args, indent=0, **kwargs):
        if self.isEnabledFor(EMBED):
            self._log(EMBED, msg, args, extra={"indent": indent}, **kwargs)
    
    def agent(self, msg, *args, indent=0, **kwargs):
        if self.isEnabledFor(AGENT):
            self._log(AGENT, msg, args, extra={"indent": indent}, **kwargs)
    
    def info_indent(self, msg, *args, indent=0, **kwargs):
        if self.isEnabledFor(logging.INFO):
            self._log(logging.INFO, msg, args, extra={"indent": indent}, **kwargs)


# Set custom logger class
logging.setLoggerClass(AppLogger)


def setup_logging(
    name: str = "resq",
    level: int = logging.DEBUG,
    log_file: Optional[Path] = None,
) -> AppLogger:
    """
    Set up application logging.
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Optional file path for log output
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(PlainFormatter())
        logger.addHandler(file_handler)
    
    return logger


# Default logger instance
logger = setup_logging()


# Convenience functions for module-level usage
def info(msg, indent=0): logger.info_indent(msg, indent=indent)
def success(msg, indent=0): logger.success(msg, indent=indent)
def warning(msg, indent=0): logger.warning(msg, extra={"indent": indent})
def error(msg, indent=0): logger.error(msg, extra={"indent": indent})
def db(msg, indent=0): logger.db(msg, indent=indent)
def embed(msg, indent=0): logger.embed(msg, indent=indent)
def agent(msg, indent=0): logger.agent(msg, indent=indent)


# Export
__all__ = [
    "setup_logging",
    "logger",
    "info",
    "success",
    "warning",
    "error",
    "db",
    "embed",
    "agent",
]
