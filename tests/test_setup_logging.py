from typing import cast
from unittest.mock import Mock, patch

import structlog

from dis_python_logger import setup_logging


def test_setup_logging_returns_logger() -> None:
    expected_logger = Mock()

    with patch("structlog.configure"), patch("structlog.get_logger", return_value=expected_logger):
        logger = setup_logging("test")

    assert logger is expected_logger


def test_setup_logging_uses_created_at_timestamp_key() -> None:
    captured_config: dict[str, object] = {}

    def fake_configure(**kwargs: object) -> None:
        captured_config.update(kwargs)

    with patch("structlog.configure", side_effect=fake_configure), patch("structlog.get_logger", return_value=Mock()):
        setup_logging("test")

    processors = cast(list[object], captured_config["processors"])
    timestamper = processors[0]
    assert isinstance(timestamper, structlog.processors.TimeStamper)
    assert timestamper.key == "created_at"
