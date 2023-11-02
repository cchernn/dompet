from django.urls import path
from . import apis

urlpatterns = [
    path("register", apis.RegisterAPI.as_view(), name="register"),
    path("me", apis.UserAPI.as_view(), name="me"),
    path("logout", apis.LogoutAPI.as_view(), name="logout"),
]
