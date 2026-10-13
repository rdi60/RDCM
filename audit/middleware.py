import contextvars

_current_request = contextvars.ContextVar("current_request", default=None)


class CurrentRequestMiddleware:
    """
    Stashes the in-flight request so model signal handlers (which Django
    calls with no request at all) can still attribute a create/update/
    delete to a user and IP for the audit log. Request-scoped and
    thread/async-safe via contextvars; reset in `finally` so nothing leaks
    into the next request handled by the same worker.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _current_request.set(request)
        try:
            return self.get_response(request)
        finally:
            _current_request.reset(token)


def get_current_request():
    return _current_request.get()
