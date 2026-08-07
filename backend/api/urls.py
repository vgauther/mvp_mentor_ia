from django.urls import path

from .liked_first_names import SearchLikedFirstNameListView
from .participant_removal import (
    SearchParticipantLeaveView,
    SearchParticipantRemovalView,
)
from .search_lifecycle import (
    LifecycleNameDecisionListCreateView,
    LifecycleNextFirstNameView,
    LifecycleSearchInvitationResponseView,
    SearchStatusUpdateView,
)
from .search_update import NameSearchUpdateView
from .views import (
    AdminView,
    FirstNameListView,
    MeView,
    NameSearchListCreateView,
    ProfileLookupView,
    PublicView,
    SearchInvitationCreateView,
    SearchInvitationListView,
    SearchMatchListView,
    FirstNameOriginListView,
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
        "searches/<int:search_id>/",
        NameSearchUpdateView.as_view(),
        name="name-search-update",
    ),
    path(
        "searches/<int:search_id>/status/",
        SearchStatusUpdateView.as_view(),
        name="search-status-update",
    ),
    path(
        "searches/<int:search_id>/invitations/",
        SearchInvitationCreateView.as_view(),
        name="search-invitation-create",
    ),
    path(
        "searches/<int:search_id>/participants/me/",
        SearchParticipantLeaveView.as_view(),
        name="search-participant-leave",
    ),
    path(
        "searches/<int:search_id>/participants/<int:participant_id>/",
        SearchParticipantRemovalView.as_view(),
        name="search-participant-removal",
    ),
    path(
        "invitations/",
        SearchInvitationListView.as_view(),
        name="search-invitation-list",
    ),
    path(
        "invitations/<int:invitation_id>/",
        LifecycleSearchInvitationResponseView.as_view(),
        name="search-invitation-response",
    ),
    path(
        "searches/<int:search_id>/next-first-name/",
        LifecycleNextFirstNameView.as_view(),
        name="next-first-name",
    ),
    path(
        "searches/<int:search_id>/decisions/",
        LifecycleNameDecisionListCreateView.as_view(),
        name="name-decision-list-create",
    ),
    path(
        "searches/<int:search_id>/liked-first-names/",
        SearchLikedFirstNameListView.as_view(),
        name="search-liked-first-name-list",
    ),
    path(
    "first-name-origins/",
    FirstNameOriginListView.as_view(),
    name="first-name-origin-list",
    ),
    path(
        "searches/<int:search_id>/matches/",
        SearchMatchListView.as_view(),
        name="search-match-list",
    ),
]