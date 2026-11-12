from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .permissions import UserManagementPermission
from .serializers import LoginSerializer, UserCreateSerializer, UserSerializer


@method_decorator(csrf_protect, name="post")
class LoginView(APIView):
    """
    Authenticate credentials and establish a session.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    """Invalidate the active session."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)  # flushes the session server-side
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """Return the authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


@method_decorator(ensure_csrf_cookie, name="get")
class SessionView(APIView):
    """Report session validity and seed the CSRF cookie.

    Angular calls this first: ensure_csrf_cookie sets the (non-HttpOnly) csrftoken
    cookie so the frontend can echo it in the X-CSRFToken header on later writes.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        if request.user.is_authenticated:
            return Response({"authenticated": True, "user": UserSerializer(request.user).data})
        return Response({"authenticated": False})


class UserViewSet(viewsets.ModelViewSet):
    """User management: Admin/Manager can view; only Admin can create/modify."""

    queryset = User.objects.all().order_by("id")
    permission_classes = [UserManagementPermission]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer
