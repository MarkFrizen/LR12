"""
Модуль настройки логирования приложения.

Обеспечивает единую конфигурацию логирования для всех компонентов:
- Вывод в stdout (для Docker / systemd)
- Запись в файл logs/app.log
- Автоматическое создание директории logs/ при инициализации

Использование:
    from app.logger import get_logger, setup_logging

    setup_logging()
    logger = get_logger(__name__)
    logger.info("Приложение запущено")
"""

import logging
import sys
from pathlib import Path

# Директория для файлов логов (создаётся при первом импорте)
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def setup_logging(level: int = logging.INFO) -> None:
    """
    Настроить корневой логгер приложения.

    Конфигурирует два обработчика:
    - StreamHandler: цветной вывод в stdout (для консоли / Docker)
    - FileHandler: ротация по дням (logs/app.log)

    Args:
        level: Уровень логирования (по умолчанию logging.INFO).
               Для отладки используйте logging.DEBUG.
    """
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Обработчик для stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(level)
    stdout_handler.setFormatter(formatter)

    # Обработчик для файла
    file_handler = logging.FileHandler(
        filename=LOG_DIR / "app.log",
        encoding="utf-8",
        mode="a",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(stdout_handler)
    root_logger.addHandler(file_handler)

    # Тихий режим для библиотек
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Получить логгер для указанного модуля.

    Args:
        name: Имя логгера (обычно __name__).

    Returns:
        logging.Logger — настроенный экземпляр логгера.
    """
    return logging.getLogger(name)
