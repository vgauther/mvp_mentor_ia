from django.urls import path

from .views import (
    AdminView,
    FirstNameListView,
    MeView,
    NameDecisionListCreateView,
    NameSearchListCreateView,
    NextFirstNameView,
    ProfileLookupView,
    PublicView,
    SearchInvitationCreateView,
    SearchInvitationListView,
    SearchInvitationResponseView,
)


urlpatterns = [
    path("public/", PublicView.as_view(), name="public"),
    path("me/", MeView.as_view(), name="me"),
    path(
        "profiles/lookup/",
        ProfileLookupView.as_view(),
        name="profile-lookup",
    ),
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
        "searches/<int:search_id>/invitations/",
        SearchInvitationCreateView.as_view(),
        name="search-invitation-create",
    ),
    path(
        "invitations/",
        SearchInvitationListView.as_view(),
        name="search-invitation-list",
    ),
    path(
        "invitations/<int:invitation_id>/",
        SearchInvitationResponseView.as_view(),
        name="search-invitation-response",
    ),
    path(
        "searches/<int:search_id>/next-first-name/",
        NextFirstNameView.as_view(),
        name="next-first-name",
    ),
    path(
        "searches/<int:search_id>/decisions/",
        NameDecisionListCreateView.as_view(),
        name="name-decision-list-create",
    ),
]