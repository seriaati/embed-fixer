from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from loguru import logger

from embed_fixer.utils.logging import InterceptHandler

if TYPE_CHECKING:
    from collections.abc import Iterator

    from loguru import Message


@pytest.fixture
def standard_logger() -> Iterator[logging.Logger]:
    standard = logging.getLogger(__name__)
    original = standard.handlers[:], standard.level, standard.propagate, standard.disabled
    standard.handlers = [InterceptHandler()]
    standard.setLevel(logging.DEBUG)
    standard.propagate = False
    standard.disabled = False
    try:
        yield standard
    finally:
        standard.handlers, standard.level, standard.propagate, standard.disabled = original


@pytest.mark.parametrize(
    ("level", "expected_name"),
    [(logging.INFO, "INFO"), (logging.WARNING, "WARNING"), (55, "Level 55")],
)
def test_intercept_handler_formats_record_and_preserves_level(
    standard_logger: logging.Logger, level: int, expected_name: str
) -> None:
    messages: list[Message] = []
    sink = logger.add(messages.append, format="{message}")
    try:
        standard_logger.log(level, "message %s", "argument")
    finally:
        logger.remove(sink)
    assert len(messages) == 1
    assert messages[0].record["message"] == "message argument"
    assert messages[0].record["level"].name == expected_name
    assert messages[0].record["level"].no == level
    assert (
        messages[0].record["function"]
        == "test_intercept_handler_formats_record_and_preserves_level"
    )


def test_intercept_handler_preserves_exception_info(standard_logger: logging.Logger) -> None:
    messages: list[Message] = []
    sink = logger.add(messages.append, format="{message}")
    failure = ValueError("broken")
    try:
        try:
            raise failure
        except ValueError:
            standard_logger.exception("failure")
    finally:
        logger.remove(sink)
    assert len(messages) == 1
    exception = messages[0].record["exception"]
    assert exception is not None
    assert exception.value is failure


def test_intercept_handler_handles_missing_frame() -> None:
    record = logging.makeLogRecord({"msg": "message", "levelname": "INFO", "levelno": logging.INFO})
    with (
        patch("embed_fixer.utils.logging.inspect.currentframe", return_value=None),
        patch("embed_fixer.utils.logging.logger") as loguru,
    ):
        loguru.level.return_value.name = "INFO"
        InterceptHandler().emit(record)
    loguru.opt.assert_called_once_with(depth=0, exception=None)
    loguru.opt.return_value.log.assert_called_once_with("INFO", "message")
