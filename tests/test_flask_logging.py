from unittest.mock import Mock

from flask import Flask

from dis_python_logger import DisLogger
from dis_python_logger.context import get_context_fields

STATUS_CODE_OK = 200


def test_init_flask_logging_logs_request_and_clears_context():
    app = Flask("test")
    logger = Mock()
    dis_logger = DisLogger("test", logger)
    dis_logger.init_flask_logging(app, "test-app")

    context_seen_in_route = {}

    @app.get("/someurl")
    def datasets():
        context_seen_in_route.update(get_context_fields())
        return "ok", STATUS_CODE_OK

    response = app.test_client().get("/someurl")

    assert response.status_code == STATUS_CODE_OK
    assert context_seen_in_route["method"] == "GET"
    assert context_seen_in_route["path"] == "/someurl"

    logger.log.assert_called_once()
    assert logger.log.call_args.kwargs["event"] == "HTTP request received"

    logger.info.assert_called_once()
    completed_event = logger.info.call_args.kwargs
    assert completed_event["event"] == "HTTP request completed"
    assert completed_event["http"]["status_code"] == STATUS_CODE_OK
    assert completed_event["http"]["path"] == "/someurl"

    assert get_context_fields() == {}

    response = app.test_client().get(
        "/someurl?limit=10",
        base_url="https://example.org:8443",
    )

    http = logger.info.call_args.kwargs["http"]
    assert http["scheme"] == "https"
    assert http["port"] == "8443"
    assert http["query"] == "limit=10"
