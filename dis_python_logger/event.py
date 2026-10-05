import dataclasses
from datetime import datetime


@dataclasses.dataclass
class EventData:
    # Mandatory Fields
    namespace: str
    event: str
    severity: int

    # Optional fields
    trace_id: str | None = None
    span_id: str | None = None
    classification: str | None = None
    raw: str | None = None
    spec_version: str | None = None
    auth: Auth | None = None
    data: dict | None = None
    http: HTTP | None = None
    errors: Error | None = None

    def asdict(self) -> dict:
        return {key: value for key, value in dataclasses.asdict(self).items() if value is not None}


@dataclasses.dataclass
class Auth:
    identity: str
    identity_type: str


@dataclasses.dataclass
class Error:
    message: str
    data: list[str] | None = None
    stack_trace: StackTrace | None = None


@dataclasses.dataclass
class StackTrace:
    line: int
    file: str
    function: str


@dataclasses.dataclass
class HTTP:
    duration: float
    ended_at: datetime
    host: str
    method: str
    path: str
    port: str
    query: str
    response_content_length: int
    scheme: str
    started_at: datetime
    status_code: int
