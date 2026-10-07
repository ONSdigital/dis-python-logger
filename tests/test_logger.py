from unittest.mock import Mock

from dis_python_logger import DisLogger

WARNING_SEVERITY = 2
data = {"something": 3}
exp = Exception("Sorry, no numbers below zero")


def test_severity_rating() -> None:
    logger = Mock()
    dis_logger = DisLogger("test", logger)
    severity = dis_logger.level_to_severity(50)
    assert severity == 0

    severity = dis_logger.level_to_severity(35)
    assert severity == 1

    severity = dis_logger.level_to_severity(21)
    assert severity == WARNING_SEVERITY


def test_get_error_and_data_dicts() -> None:
    logger = Mock()
    dis_logger = DisLogger("test", logger)
    get_error = dis_logger.get_error_and_data_dicts(exp, {})
    assert get_error[0].message == "Sorry, no numbers below zero"


def test_create_error_dict_after_exception_handler() -> None:
    try:
        raise ValueError("bad input")
    except ValueError as exc:
        caught = exc

    result = DisLogger.create_error_dict(caught)

    assert result.message == "bad input"
    assert result.data is not None
    assert any("ValueError: bad input" in line for line in result.data)


def test_debug_logging() -> None:
    logger = Mock()
    dis_logger = DisLogger("test", logger)
    dis_logger.debug("some debug thing", raw="debug details", data=data)

    logger.log.assert_called_once_with(
        event="some debug thing",
        namespace="test",
        severity=3,
        raw="debug details",
        data=data,
    )


def test_error_logging() -> None:
    logger = Mock()
    dis_logger = DisLogger("test", logger)
    expected_error = {"message": "Sorry, no numbers below zero", "data": None, "stack_trace": None}
    dis_logger.error("error thing", error=exp, raw="error details", data=data)

    logger.log.assert_called_once_with(
        event="error thing",
        namespace="test",
        severity=1,
        raw="error details",
        errors=expected_error,
        data=data,
    )
