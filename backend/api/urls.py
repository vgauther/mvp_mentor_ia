from django.urls import path

from .views import (
    AdminView,
    FirstNameListView,
    MeView,
    NameDecisionListCreateView,
    NameSearchListCreateView,
    PublicView,
)


urlpatterns = [
    path("public/", PublicView.as_view(), name="public"),
    path("me/", MeView.as_view(), name="me"),
    path("admin/", AdminView.as_view(), name="admin"),
    path(
        "first-names/",
        FirstNameListView.as_view(),
        name="first-name-list",
    ),
    path(
        "searches/",
        NameSearchListCreateView.as_view(),
        name="name-search-list-create",
    ),
    path(
        "searches/<int:search_id>/decisions/",
        NameDecisionListCreateView.as_view(),
        name="name-decision-list-create",
    ),
]