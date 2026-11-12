from rest_framework.authentication import SessionAuthentication


class SessionAuthentication401(SessionAuthentication):
    """Session auth that returns 401 (not 403) for unauthenticated requests.

    DRF's default SessionAuthentication provides no ``authenticate_header``, so an
    unauthenticated request to a protected view yields 403. By returning a header
    here, DRF maps ``NotAuthenticated`` to **401** (not logged in / session
    expired) while a genuine permission failure still yields **403** (forbidden).
    This lets the Angular interceptor redirect to login only on 401.
    """

    def authenticate_header(self, request):
        return "Session"
