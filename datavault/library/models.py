import hashlib
import mimetypes
import os

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


EXTENSION_CATEGORIES = {
    "image": {"jpg", "jpeg", "png", "gif", "bmp", "webp", "tif", "tiff", "heic"},
    "video": {"mp4", "mov", "avi", "mkv", "webm", "m4v"},
    "pdf": {"pdf"},
    "presentation": {"ppt", "pptx", "key", "odp"},
    "spreadsheet": {"xls", "xlsx", "csv", "ods"},
    "document": {"doc", "docx", "txt", "rtf", "odt"},
}


def categorize_extension(filename):
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    for category, extensions in EXTENSION_CATEGORIES.items():
        if ext in extensions:
            return category
    return "other"


def document_upload_path(instance, filename):
    date = instance.document_date or timezone.now().date()
    safe_name = filename.replace("/", "_").replace("\\", "_")
    return f"documents/{date.year}/{date.month:02d}/{safe_name}"


class Topic(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    color = models.CharField(max_length=7, default="#4f46e5", help_text="Hex colour used for this topic's badge")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Subtopic(models.Model):
    topic = models.ForeignKey(Topic, related_name="subtopics", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=110, blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("topic", "name")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.topic.name} / {self.name}"


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @classmethod
    def parse_tag_names(cls, raw):
        """Turn a comma-separated string into a clean, de-duplicated list of names."""
        seen = []
        for part in (raw or "").split(","):
            name = part.strip()
            if name and name.lower() not in [s.lower() for s in seen]:
                seen.append(name)
        return seen

    @classmethod
    def get_or_create_many(cls, raw):
        tags = []
        for name in cls.parse_tag_names(raw):
            tag, _ = cls.objects.get_or_create(name__iexact=name, defaults={"name": name})
            tags.append(tag)
        return tags


class CustomFieldDefinition(models.Model):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    CHOICE = "choice"
    BOOLEAN = "boolean"
    FIELD_TYPES = [
        (TEXT, "Text"),
        (NUMBER, "Number"),
        (DATE, "Date"),
        (CHOICE, "Choice"),
        (BOOLEAN, "Yes / No"),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    field_type = models.CharField(max_length=10, choices=FIELD_TYPES, default=TEXT)
    choices = models.CharField(
        max_length=500, blank=True,
        help_text="Comma-separated options (only used for Choice fields)",
    )
    topic = models.ForeignKey(
        Topic, null=True, blank=True, on_delete=models.CASCADE, related_name="custom_fields",
        help_text="Leave blank to show this field for every topic",
    )
    required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_choice_list(self):
        return [c.strip() for c in self.choices.split(",") if c.strip()]

    def __str__(self):
        return self.name


class Document(models.Model):
    CATEGORY_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
        ("pdf", "PDF"),
        ("presentation", "Presentation"),
        ("spreadsheet", "Spreadsheet"),
        ("document", "Document"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to=document_upload_path, max_length=500)
    original_filename = models.CharField(max_length=255, blank=True)
    file_category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")
    file_size = models.PositiveBigIntegerField(default=0)
    file_hash = models.CharField(max_length=64, blank=True, db_index=True)

    topic = models.ForeignKey(Topic, null=True, blank=True, on_delete=models.SET_NULL, related_name="documents")
    subtopic = models.ForeignKey(Subtopic, null=True, blank=True, on_delete=models.SET_NULL, related_name="documents")
    tags = models.ManyToManyField(Tag, blank=True, related_name="documents")

    document_date = models.DateField(
        default=timezone.now,
        help_text="The date this item belongs to — used to file it under a month/year",
    )
    year = models.PositiveIntegerField(editable=False, db_index=True, default=0)
    month = models.PositiveIntegerField(editable=False, db_index=True, default=0)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="documents"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-document_date", "-created_at"]

    def save(self, *args, **kwargs):
        if self.document_date:
            self.year = self.document_date.year
            self.month = self.document_date.month
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("library:document_detail", args=[self.pk])

    @property
    def extension(self):
        name = self.original_filename or (self.file.name if self.file else "")
        return os.path.splitext(name)[1].lower().lstrip(".")

    @property
    def mime_type(self):
        name = self.original_filename or (self.file.name if self.file else "")
        guessed, _ = mimetypes.guess_type(name)
        return guessed or "application/octet-stream"

    @property
    def is_previewable_image(self):
        return self.file_category == "image"

    @property
    def is_previewable_video(self):
        return self.file_category == "video"

    @property
    def is_previewable_pdf(self):
        return self.file_category == "pdf"

    def applicable_custom_fields(self):
        return CustomFieldDefinition.objects.filter(
            models.Q(topic__isnull=True) | models.Q(topic=self.topic)
        ).order_by("order", "name")

    def field_value_map(self):
        return {fv.field_id: fv.value for fv in self.field_values.all()}

    def __str__(self):
        return self.title

    @staticmethod
    def compute_file_hash(file_obj):
        hasher = hashlib.sha256()
        for chunk in file_obj.chunks():
            hasher.update(chunk)
        file_obj.seek(0)
        return hasher.hexdigest()


class DocumentFieldValue(models.Model):
    document = models.ForeignKey(Document, related_name="field_values", on_delete=models.CASCADE)
    field = models.ForeignKey(CustomFieldDefinition, related_name="values", on_delete=models.CASCADE)
    value = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = ("document", "field")

    def __str__(self):
        return f"{self.document.title}: {self.field.name}={self.value}"


class SavedFilter(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_filters")
    name = models.CharField(max_length=100)
    query_string = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("user", "name")

    def __str__(self):
        return self.name
