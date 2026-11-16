from django import forms

from .models import CustomFieldDefinition, Subtopic, Tag, Topic


class SubtopicSelect(forms.Select):
    """A <select> whose <option>s carry data-topic so JS can filter them by the chosen topic."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value:
            try:
                subtopic = Subtopic.objects.select_related("topic").get(pk=value.value if hasattr(value, "value") else value)
                option["attrs"]["data-topic"] = subtopic.topic_id
            except Subtopic.DoesNotExist:
                pass
        return option


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultiFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return [single_file_clean(data, initial)]


class DocumentUploadForm(forms.Form):
    """Upload one or many files at once, applying the same metadata to each."""

    files = MultiFileField(label="Files")
    topic = forms.ModelChoiceField(
        queryset=Topic.objects.all(), required=False, empty_label="(no topic)",
        widget=forms.Select(attrs={"id": "id_topic"}),
    )
    subtopic = forms.ModelChoiceField(
        queryset=Subtopic.objects.all(), required=False, empty_label="(no subtopic)",
        widget=SubtopicSelect(attrs={"id": "id_subtopic"}),
    )
    document_date = forms.DateField(
        required=True, widget=forms.DateInput(attrs={"type": "date"}), label="Date (for month/year filing)"
    )
    tags = forms.CharField(required=False, help_text="Comma-separated, e.g. x-ray, insurance, 2024")
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))


class DocumentEditForm(forms.Form):
    title = forms.CharField(max_length=255)
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    topic = forms.ModelChoiceField(
        queryset=Topic.objects.all(), required=False, empty_label="(no topic)",
        widget=forms.Select(attrs={"id": "id_topic"}),
    )
    subtopic = forms.ModelChoiceField(
        queryset=Subtopic.objects.all(), required=False, empty_label="(no subtopic)",
        widget=SubtopicSelect(attrs={"id": "id_subtopic"}),
    )
    document_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    tags = forms.CharField(required=False, help_text="Comma-separated")
    replacement_file = forms.FileField(required=False, label="Replace file (optional)")


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ["name", "description", "color", "order"]
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}


class SubtopicForm(forms.ModelForm):
    class Meta:
        model = Subtopic
        fields = ["topic", "name"]


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name"]


class CustomFieldDefinitionForm(forms.ModelForm):
    class Meta:
        model = CustomFieldDefinition
        fields = ["name", "field_type", "choices", "topic", "required", "order"]
        widgets = {"choices": forms.TextInput(attrs={"placeholder": "Option 1, Option 2, Option 3"})}
