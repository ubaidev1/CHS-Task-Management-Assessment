from django.urls import path

from .views import LoginView, LogoutView, MeView, SessionView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("session/", SessionView.as_view(), name="session"),
]
