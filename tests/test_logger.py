import logging
from unittest.mock import patch, MagicMock

import pytest

from app.logger import LOG_DIR, get_logger, setup_logging


def test_log_dir_creation():
    """Проверяет, что директория logs/ создаётся при импорте модуля."""
    assert LOG_DIR.exists()
    assert LOG_DIR.is_dir()


def test_setup_logging_creates_handlers():
    """Проверяет, что setup_logging настраивает обработчики."""
    # Очищаем обработчики перед тестом
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    setup_logging()
    
    # Проверяем, что добавлено два обработчика
    assert len(root_logger.handlers) == 2
    
    # Проверяем типы обработчиков
    handler_types = [type(h) for h in root_logger.handlers]
    assert logging.StreamHandler in handler_types
    assert logging.FileHandler in handler_types


def test_setup_logging_sets_levels():
    """Проверяет, что setup_logging устанавливает правильные уровни логирования."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    setup_logging(level=logging.DEBUG)
    
    assert root_logger.level == logging.DEBUG
    for handler in root_logger.handlers:
        assert handler.level == logging.DEBUG


def test_setup_logging_configures_formatter():
    """Проверяет, что обработчики используют правильный формат."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    setup_logging()
    
    for handler in root_logger.handlers:
        assert isinstance(handler.formatter, logging.Formatter)
        assert "%(asctime)s" in handler.formatter._fmt
        assert "[%(levelname)-7s]" in handler.formatter._fmt
        assert "%(name)s" in handler.formatter._fmt
        assert "%(message)s" in handler.formatter._fmt


def test_get_logger_returns_logger():
    """Проверяет, что get_logger возвращает экземпляр logging.Logger."""
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"


def test_setup_logging_silences_noisy_loggers():
    """Проверяет, что setup_logging понижает уровень логирования для шумных библиотек."""
    # Сохраняем исходные уровни
    sqlalchemy_level = logging.getLogger("sqlalchemy.engine").level
    uvicorn_level = logging.getLogger("uvicorn.access").level
    
    setup_logging()
    
    # Проверяем, что уровни изменены
    assert logging.getLogger("sqlalchemy.engine").level == logging.WARNING
    assert logging.getLogger("uvicorn.access").level == logging.WARNING
    
    # Восстанавливаем исходные уровни
    logging.getLogger("sqlalchemy.engine").setLevel(sqlalchemy_level)
    logging.getLogger("uvicorn.access").setLevel(uvicorn_level)