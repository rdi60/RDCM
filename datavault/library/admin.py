from django.contrib import admin

from .models import CustomFieldDefinition, Document, DocumentFieldValue, SavedFilter, Subtopic, Tag, Topic


class SubtopicInline(admin.TabularInline):
    model = Subtopic
    extra = 1


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "color")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SubtopicInline]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(CustomFieldDefinition)
class CustomFieldDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "field_type", "topic", "required", "order")
    prepopulated_fields = {"slug": ("name",)}


class DocumentFieldValueInline(admin.TabularInline):
    model = DocumentFieldValue
    extra = 0


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "topic", "subtopic", "file_category", "document_date", "uploaded_by")
    list_filter = ("file_category", "topic", "year")
    search_fields = ("title", "description", "original_filename")
    inlines = [DocumentFieldValueInline]


@admin.register(SavedFilter)
class SavedFilterAdmin(admin.ModelAdmin):
    list_display = ("name", "user")
