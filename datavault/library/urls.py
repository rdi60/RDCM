from django.urls import path

from . import views

app_name = "library"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("documents/", views.document_list, name="document_list"),
    path("documents/upload/", views.document_upload, name="document_upload"),
    path("documents/duplicates/", views.duplicates, name="duplicates"),
    path("documents/<int:pk>/", views.document_detail, name="document_detail"),
    path("documents/<int:pk>/edit/", views.document_edit, name="document_edit"),
    path("documents/<int:pk>/delete/", views.document_delete, name="document_delete"),

    path("topics/", views.topic_list, name="topic_list"),
    path("topics/<int:pk>/edit/", views.topic_edit, name="topic_edit"),
    path("topics/<int:pk>/delete/", views.topic_delete, name="topic_delete"),
    path("topics/<int:topic_pk>/subtopics/add/", views.subtopic_add, name="subtopic_add"),
    path("subtopics/<int:pk>/delete/", views.subtopic_delete, name="subtopic_delete"),

    path("tags/", views.tag_list, name="tag_list"),
    path("tags/<int:pk>/delete/", views.tag_delete, name="tag_delete"),

    path("fields/", views.field_list, name="field_list"),
    path("fields/add/", views.field_add, name="field_add"),
    path("fields/<int:pk>/edit/", views.field_edit, name="field_edit"),
    path("fields/<int:pk>/delete/", views.field_delete, name="field_delete"),

    path("filters/save/", views.saved_filter_create, name="saved_filter_create"),
    path("filters/<int:pk>/delete/", views.saved_filter_delete, name="saved_filter_delete"),

    path("ajax/subtopics/", views.ajax_subtopics, name="ajax_subtopics"),
]
