import json
import logging

from app.core.logging import JsonFormatter


def test_log_lines_are_single_line_json_with_level_logger_and_message():
    record = logging.LogRecord("app.x", logging.INFO, __file__, 1, "queued %s", ("o/r#7",), None)

    line = JsonFormatter().format(record)

    assert "\n" not in line
    assert json.loads(line) | {"time": None} == {
        "time": None,
        "level": "INFO",
        "logger": "app.x",
        "message": "queued o/r#7",
    }


def test_http_client_request_urls_are_not_logged():
    from app.core.logging import setup_logging

    setup_logging()

    # httpx logs full URLs at INFO; codeload redirect URLs can carry a token.
    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
