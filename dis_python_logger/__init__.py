import logging
import time
import traceback
from datetime import datetime
from typing import cast
from urllib.parse import urlsplit

import structlog
from flask import Flask, Response, g, request

from dis_python_logger.event import HTTP, Auth, Error, EventData

from .context import pop_context, push_context


def setup_logging(namespace: str) -> structlog.BoundLogger:
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True,
    )
    return cast(structlog.BoundLogger, structlog.get_logger(namespace))


class DisLogger:
    def __init__(self: DisLogger, namespace: str, logger: structlog.BoundLogger):
        """Simple python logger to create structured logs.
        In keeping with https://github.com/ONSdigital/dp-standards/blob/main/LOGGING_STANDARDS.md.

        :param namespace: (required) The namespace for the application.
        """
        self.namespace = namespace
        self.logger = logger

    def init_flask_logging(self: DisLogger, app: Flask) -> Flask:
        @app.before_request
        def _start_request_logging() -> None:
            g._log_context_token = push_context(
                method=request.method,
                path=request.path,
                remote_addr=request.remote_addr,
            )
            g._request_start_date = datetime.now()
            g._request_start_time = time.time()
            self.info("HTTP request received")

        @app.after_request
        def _log_request_completed(response: Response) -> Response:
            duration_ms = 0.0
            start_date = getattr(g, "_request_start_date", None)
            if start_date is None:
                start_date = datetime.now()
            start_time = getattr(g, "_request_start_time", None)
            if start_time is not None:
                duration_ms = round((time.time() - start_time) * 1000, 2)

            port = urlsplit(f"//{request.host}").port
            auth_info = Auth(identity="some-service", identity_type="service")
            http = HTTP(
                duration=duration_ms,
                host=request.host,
                method=request.method,
                path=request.path,
                port=str(port),
                scheme=request.scheme,
                query=request.query_string.decode("utf-8"),
                started_at=start_date,
                ended_at=datetime.now(),
                response_content_length=response.content_length,
                status_code=response.status_code,
            )
            event_data = EventData(
                auth=auth_info,
                trace_id="trace-id",
                namespace=self.namespace,
                event="HTTP request completed",
                severity=3,
                http=http,
            )
            self.logger.info(**event_data.asdict())
            return response

        @app.teardown_request
        def _end_request_logging(exc: BaseException | None) -> None:
            if exc is not None and isinstance(exc, Exception):
                self.error("request failed with unhandled exception", error=exc)
            token = getattr(g, "_log_context_token", None)
            if token is not None:
                pop_context(token)

        return app

    def level_to_severity(self, level: int) -> int:
        """Helper to convert logging level to severity.
        Please see: https://github.com/ONSdigital/dp-standards/blob/main/LOGGING_STANDARDS.md#severity-levels.
        """
        if level > logging.ERROR:
            return 0
        elif level > logging.WARNING:
            return 1
        elif level > logging.INFO:
            return 2
        else:
            return 3

    def _log(
        self: DisLogger,
        event: str,
        level: int,
        error: Exception | None = None,
        data: dict | None = None,
        raw: str | None = None,
    ) -> None:
        data_dict = data if data is not None else {}

        errors, data_dict = self.get_error_and_data_dicts(error, data_dict)

        level_int = self.level_to_severity(level)
        log_event = EventData(
            event=event, namespace=self.namespace, severity=level_int, data=data_dict, errors=errors, raw=raw
        )
        self.logger.log(**log_event.asdict())

    def get_error_and_data_dicts(self, error: Exception | None, data_dict: dict) -> tuple[Error | None, dict]:
        """Converts error (if any)to dictionary.
        Adds additional error data from the exception to the data dictionary.

        :param error:.
        :param data_dict:.

        :return: Tuple of dictionaries; [0] == error, [1] == data_dict.
        """
        if error is None:
            return (None, data_dict)

        error_dict = self.create_error_dict(error)
        return (error_dict, data_dict)

    @staticmethod
    def create_error_dict(error: Exception) -> Error:
        """Take a python Exception and create a sub dict/document
        matching DP logging standards expression of a captured
        error.

        https://github.com/ONSdigital/dp-standards/blob/main/LOGGING_STANDARDS.md#error-event-data
        """
        if error.__traceback__ is None:
            return Error(message=str(error))

        return Error(
            data=traceback.format_exception(error),
            message=str(error),
        )

    def debug(
        self,
        event: str,
        raw: str | None = None,
        data: dict | None = None,
    ) -> None:
        """Log at the debug level.

        :param event: The event description.
        :param raw: Raw log data for a third party library.
        :param data: Additional context data such as arbitrary key-value pairs that may be of use in providing context.
        :param response: Optional HTTP response to include in the log.
        """
        self._log(event, logging.DEBUG, raw=raw, data=data)

    def info(
        self,
        event: str,
        raw: str | None = None,
        data: dict | None = None,
    ) -> None:
        """Log at the info level.

        :param event: The event description.
        :param raw: Raw log data for a third party library.
        :param data: Additional context data such as arbitrary key-value pairs that may be of use in providing context.
        """
        self._log(event, logging.INFO, raw=raw, data=data)

    def warning(
        self,
        event: str,
        raw: str | None = None,
        data: dict | None = None,
    ) -> None:
        """Log at the warning level.

        :param event: The event description.
        :param raw: Raw log data for a third party library.
        :param data: Additional context data such as arbitrary key-value pairs that may be of use in providing context.
        :param response: Optional HTTP response to include in the log.
        """
        self._log(event, logging.WARNING, raw=raw, data=data)

    def error(
        self,
        event: str,
        error: Exception,
        raw: str | None = None,
        data: dict | None = None,
    ) -> None:
        """Log at the error level.

        :param event: The event description.
        :param error: A python Exception.
        :param raw: Raw log data for a third party library.
        :param data: Additional context data such as arbitrary key-value pairs that may be of use in providing context.
        :param response: Optional HTTP response to include in the log.
        """
        self._log(event, logging.ERROR, error=error, raw=raw, data=data)

    def critical(
        self,
        event: str,
        error: Exception,
        raw: str | None = None,
        data: dict | None = None,
    ) -> None:
        """IMPORTANT: You should only be logging at the critical level during
        application failure, i.e. if your app is in the process of failing
        over you should log at critical level.

        Log at the critical level.

        :param event: The event description.
        :param error: A python Exception.
        :param raw: Raw log data for a third party library.
        :param data: Additional context data such as arbitrary key-value pairs that may be of use in providing context.
        :param response: Optional HTTP response to include in the log.
        """
        self._log(event, logging.CRITICAL, error=error, raw=raw, data=data)
