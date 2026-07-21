from django.urls import path

from .views import AdminView, MeView, PublicView


urlpatterns = [
    path("public/", PublicView.as_view(), name="public"),
    path("me/", MeView.as_view(), name="me"),
    path("admin/", AdminView.as_view(), name="admin"),
]