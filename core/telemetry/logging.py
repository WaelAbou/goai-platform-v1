"""
Structured Logging System.
JSON-formatted logs with context propagation.
"""

import sys
import json
import time
import threading
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import traceback


class LogLevel(Enum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class LogRecord:
    """Structured log record."""
    timestamp: str
    level: str
    message: str
    logger: str = "goai"
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "timestamp": self.timestamp,
            "level": self.level,
            "logger": self.logger,
            "message": self.message
        }
        
        if self.trace_id:
            data["trace_id"] = self.trace_id
        if self.span_id:
            data["span_id"] = self.span_id
        if self.attributes:
            data["attributes"] = self.attributes
        if self.exception:
            data["exception"] = self.exception
        
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class StructuredLogger:
    """
    Structured logger with JSON output.
    """
    
    def __init__(
        self,
        name: str = "goai",
        level: LogLevel = LogLevel.INFO,
        output: str = "console",  # console, file, both
        file_path: str = "logs/goai.log"
    ):
        self.name = name
        self.level = level
        self.output = output
        self.file_path = file_path
        self._records: List[LogRecord] = []
        self._max_records = 10000
        self._lock = threading.Lock()
        self._context: Dict[str, Any] = {}
        
        # Setup file handler if needed
        if output in ("file", "both"):
            import os
            os.makedirs(os.path.dirname(file_path) or "logs", exist_ok=True)
    
    def set_context(self, **kwargs):
        """Set context that will be included in all logs."""
        self._context.update(kwargs)
    
    def clear_context(self):
        """Clear logging context."""
        self._context.clear()
    
    def _get_trace_context(self) -> tuple:
        """Get current trace and span IDs."""
        try:
            from .tracing import tracer
            span = tracer.get_current_span()
            if span:
                return span.trace_id, span.span_id
        except:
            pass
        return None, None
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        exc_info: bool = False,
        **kwargs
    ):
        """Internal log method."""
        if level.value < self.level.value:
            return
        
        trace_id, span_id = self._get_trace_context()
        
        # Merge context and kwargs
        attributes = {**self._context, **kwargs}
        
        # Get exception info
        exception = None
        if exc_info:
            exception = traceback.format_exc()
        
        record = LogRecord(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=level.name,
            logger=self.name,
            message=message,
            trace_id=trace_id,
            span_id=span_id,
            attributes=attributes,
            exception=exception
        )
        
        # Store record
        with self._lock:
            self._records.append(record)
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records:]
        
        # Output
        self._output(record)
    
    def _output(self, record: LogRecord):
        """Output log record."""
        json_str = record.to_json()
        
        if self.output in ("console", "both"):
            # Colorize console output
            color = self._get_color(record.level)
            print(f"{color}{json_str}\033[0m", file=sys.stderr)
        
        if self.output in ("file", "both"):
            with open(self.file_path, "a") as f:
                f.write(json_str + "\n")
    
    def _get_color(self, level: str) -> str:
        """Get ANSI color for level."""
        colors = {
            "DEBUG": "\033[36m",     # Cyan
            "INFO": "\033[32m",      # Green
            "WARNING": "\033[33m",   # Yellow
            "ERROR": "\033[31m",     # Red
            "CRITICAL": "\033[35m"   # Magenta
        }
        return colors.get(level, "")
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs):
        """Log error message."""
        self._log(LogLevel.ERROR, message, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, exc_info: bool = False, **kwargs):
        """Log critical message."""
        self._log(LogLevel.CRITICAL, message, exc_info=exc_info, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self._log(LogLevel.ERROR, message, exc_info=True, **kwargs)
    
    def get_recent_logs(
        self,
        limit: int = 100,
        level: str = None,
        trace_id: str = None
    ) -> List[Dict[str, Any]]:
        """Get recent log records."""
        with self._lock:
            records = self._records[-limit:]
            
            if level:
                records = [r for r in records if r.level == level.upper()]
            
            if trace_id:
                records = [r for r in records if r.trace_id == trace_id]
            
            return [r.to_dict() for r in records]
    
    def stats(self) -> Dict[str, Any]:
        """Get logging statistics."""
        with self._lock:
            level_counts = {}
            for record in self._records:
                level_counts[record.level] = level_counts.get(record.level, 0) + 1
            
            return {
                "total_records": len(self._records),
                "max_records": self._max_records,
                "by_level": level_counts
            }


# Global logger instance
logger = StructuredLogger()


def get_logger(name: str = None) -> StructuredLogger:
    """Get logger instance."""
    if name:
        return StructuredLogger(name=name)
    return logger


# Standard logging integration
class JSONLogHandler(logging.Handler):
    """
    Logging handler that outputs JSON.
    Integrates with Python's standard logging.
    """
    
    def __init__(self, structured_logger: StructuredLogger = None):
        super().__init__()
        self.structured_logger = structured_logger or logger
    
    def emit(self, record: logging.LogRecord):
        level_map = {
            logging.DEBUG: LogLevel.DEBUG,
            logging.INFO: LogLevel.INFO,
            logging.WARNING: LogLevel.WARNING,
            logging.ERROR: LogLevel.ERROR,
            logging.CRITICAL: LogLevel.CRITICAL
        }
        
        level = level_map.get(record.levelno, LogLevel.INFO)
        
        kwargs = {}
        if hasattr(record, "trace_id"):
            kwargs["trace_id"] = record.trace_id
        
        self.structured_logger._log(
            level,
            record.getMessage(),
            exc_info=record.exc_info is not None,
            module=record.module,
            function=record.funcName,
            line=record.lineno,
            **kwargs
        )


def setup_logging(level: str = "INFO", output: str = "console"):
    """
    Setup structured logging for the application.
    Integrates with Python's standard logging.
    """
    global logger
    
    log_level = LogLevel[level.upper()]
    logger = StructuredLogger(level=log_level, output=output)
    
    # Setup root logger
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    
    # Add JSON handler
    root.addHandler(JSONLogHandler(logger))
    
    return logger

