"""Logging configuration for the application."""

import logging
import sys
from typing import Dict, Any

from .settings import get_settings

class LevelNameColorFormatter(logging.Formatter):
    """只对日志级别名称添加颜色的格式化器"""
    
    # ANSI 颜色代码
    LEVEL_COLORS = {
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        # DEBUG 不设置颜色，保持默认
    }
    RESET = '\033[0m'  # 重置颜色
    
    def format(self, record):
        # 备份原始的 levelname
        original_levelname = record.levelname
        
        # 如果该级别有颜色配置，就给 levelname 加上颜色
        if record.levelname in self.LEVEL_COLORS:
            colored_levelname = f"{self.LEVEL_COLORS[record.levelname]}{record.levelname}{self.RESET}"
            # 临时修改 record 的 levelname
            record.levelname = colored_levelname
        
        # 使用父类的 format 方法格式化消息
        formatted_message = super().format(record)
        
        # 恢复原始的 levelname（防止影响其他处理器）
        record.levelname = original_levelname
        
        return formatted_message

def setup_logging() -> None:
    """Setup application logging configuration."""
    settings = get_settings()

    # Create a more detailed formatter
    detailed_formatter = LevelNameColorFormatter(
        fmt='%(levelname)s:\t%(asctime)s - [%(message)s] - %(filename)s:%(lineno)d',
        datefmt='%m-%d %H:%M:%S'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Add console handler with detailed formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(console_handler)

    # Configure specific loggers
    configure_loggers(settings.log_level)

    # Log the logging configuration
    logger = get_logger(__name__)
    logger.info(f"Logging system initialized with level: {settings.log_level}")
    logger.debug("Detailed logging configuration applied")


def configure_loggers(log_level: str) -> None:
    """Configure specific loggers with appropriate levels."""
    level = getattr(logging, log_level)

    # Application loggers - main app logger
    logging.getLogger('app').setLevel(level)

    # Third-party loggers - keep quiet to reduce noise
    # SQLAlchemy - completely silence all non-warning/error logs
    # Force all SQLAlchemy loggers to WARNING level to prevent SQL query logging
    sqlalchemy_loggers = [
        'sqlalchemy',
        'sqlalchemy.engine',
        'sqlalchemy.engine.Engine',
        'sqlalchemy.pool',
        'sqlalchemy.pool.impl',
        'sqlalchemy.pool.Pool',
        'sqlalchemy.dialects',
        'sqlalchemy.orm',
        'sqlalchemy.sql',
        'sqlalchemy.schema'
    ]

    for logger_name in sqlalchemy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
        # Also disable propagation to prevent parent loggers from showing these messages
        logger.propagate = False
        # Re-enable propagation only for WARNING and above
        class WarningOnlyFilter(logging.Filter):
            def filter(self, record):
                return record.levelno >= logging.WARNING
        logger.addFilter(WarningOnlyFilter())
        logger.propagate = True
    logging.getLogger('pyrogram').setLevel(logging.WARNING)
    logging.getLogger('pyrogram.session').setLevel(logging.ERROR)
    logging.getLogger('pyrogram.connection').setLevel(logging.ERROR)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    # FastAPI and Uvicorn loggers
    # Disable default uvicorn access logs - we'll use our custom middleware
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.INFO)
    logging.getLogger('fastapi').setLevel(logging.INFO)

    # Configure application loggers based on level
    if log_level == 'DEBUG':
        # DEBUG level: Enable detailed logging for key components
        logging.getLogger('app.main').setLevel(logging.DEBUG)
        logging.getLogger('app.presentation.api').setLevel(logging.DEBUG)
        logging.getLogger('app.application.use_cases').setLevel(logging.DEBUG)
        logging.getLogger('app.infrastructure.telegram').setLevel(logging.DEBUG)
        logging.getLogger('app.infrastructure.telegram.manager').setLevel(logging.DEBUG)
        logging.getLogger('app.infrastructure.telegram.client').setLevel(logging.DEBUG)
        # Keep database operations at INFO level even in DEBUG mode to reduce noise
        logging.getLogger('app.infrastructure.database').setLevel(logging.INFO)

        # Enable request logging in DEBUG mode
        logging.getLogger('app.middleware.request_logging').setLevel(logging.DEBUG)
    else:
        # INFO and above: Standard logging levels
        logging.getLogger('app.presentation.api').setLevel(logging.INFO)
        logging.getLogger('app.application.use_cases').setLevel(logging.INFO)
        logging.getLogger('app.infrastructure.telegram').setLevel(logging.INFO)
        logging.getLogger('app.infrastructure.database').setLevel(logging.WARNING)

        # Request logging always at INFO level for API access logs
        logging.getLogger('app.middleware.request_logging').setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return logging.getLogger(name)
