"""Context-local fields that get merged into every log record.

Useful for things like request IDs, user IDs, or trace IDs that you
want attached to every log line for the duration of a request/task,
without having to pass `extra=...` on every single logging call.
"""

import contextvars
from collections.abc import Iterator
from contextlib import contextmanager

_context_fields: contextvars.ContextVar[dict | None] = contextvars.ContextVar("log_context_fields", default=None)


def get_context_fields() -> dict:
    """Return a copy of the fields currently bound to this context."""
    fields = _context_fields.get()
    return dict(fields) if fields is not None else {}


@contextmanager
def log_context(**fields: object) -> Iterator[None]:
    """Temporarily attach fields to every log record emitted within this
    block (including from nested function calls / awaited coroutines).

        with log_context(request_id="abc-123", user_id=42):
            logger.info("handling request")   # includes request_id & user_id
        logger.info("outside block")          # does not
    """
    current = get_context_fields()
    token = _context_fields.set({**current, **fields})
    try:
        yield
    finally:
        _context_fields.reset(token)


def bind_context(**fields: object) -> None:
    """Attach fields to the current context indefinitely (until cleared
    or the context ends). Prefer `log_context` where possible since it
    cleans up after itself automatically.
    """
    current = get_context_fields()
    _context_fields.set({**current, **fields})


def clear_context() -> None:
    """Remove all fields bound to the current context."""
    _context_fields.set({})


def push_context(**fields: object) -> contextvars.Token:
    """Lower-level alternative to log_context() for cases where a `with`
    block doesn't line up with your control flow (e.g. framework
    before_request/teardown_request hooks). Returns a token that must
    be passed to pop_context() to restore the prior state - always do
    this in a teardown/finally handler so context doesn't leak across
    requests on the same thread.

        token = push_context(request_id="abc-123")
        try:
            ...
        finally:
            pop_context(token)
    """
    current = get_context_fields()
    return _context_fields.set({**current, **fields})


def pop_context(token: contextvars.Token) -> None:
    """Restore context state saved by a prior push_context() call."""
    _context_fields.reset(token)
