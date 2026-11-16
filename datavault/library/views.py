import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    CustomFieldDefinitionForm,
    DocumentEditForm,
    DocumentUploadForm,
    SubtopicForm,
    TagForm,
    TopicForm,
)
from .models import (
    CustomFieldDefinition,
    Document,
    DocumentFieldValue,
    SavedFilter,
    Subtopic,
    Tag,
    Topic,
    categorize_extension,
)

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


@login_required
def dashboard(request):
    documents = Document.objects.all()
    total = documents.count()
    untagged = documents.filter(topic__isnull=True).count()
    duplicate_hashes = (
        Document.objects.exclude(file_hash="")
        .values("file_hash")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
    )
    duplicate_count = sum(d["count"] - 1 for d in duplicate_hashes)

    by_category = documents.values("file_category").annotate(count=Count("id")).order_by("-count")
    by_topic = (
        Topic.objects.annotate(doc_count=Count("documents")).order_by("-doc_count", "name")[:8]
    )
    recent = documents.select_related("topic", "subtopic")[:8]

    context = {
        "total": total,
        "untagged": untagged,
        "duplicate_count": duplicate_count,
        "by_category": by_category,
        "by_topic": by_topic,
        "recent": recent,
        "topic_count": Topic.objects.count(),
        "tag_count": Tag.objects.count(),
    }
    return render(request, "library/dashboard.html", context)


def _build_sidebar_context():
    topics = (
        Topic.objects.annotate(doc_count=Count("documents"))
        .prefetch_related("subtopics")
    )
    for topic in topics:
        topic.sub_list = list(
            topic.subtopics.annotate(doc_count=Count("documents"))
        )

    year_months = (
        Document.objects.exclude(year=0)
        .values("year", "month")
        .annotate(count=Count("id"))
        .order_by("-year", "-month")
    )
    years = {}
    for row in year_months:
        years.setdefault(row["year"], []).append(
            {"month": row["month"], "month_name": MONTH_NAMES[row["month"]], "count": row["count"]}
        )

    top_tags = Tag.objects.annotate(doc_count=Count("documents")).order_by("-doc_count", "name")[:25]
    categories = (
        Document.objects.values("file_category")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    return {
        "sidebar_topics": topics,
        "sidebar_years": sorted(years.items(), key=lambda x: -x[0]),
        "sidebar_tags": top_tags,
        "sidebar_categories": categories,
    }


@login_required
def document_list(request):
    qs = Document.objects.select_related("topic", "subtopic").prefetch_related("tags")

    q = request.GET.get("q", "").strip()
    topic_slug = request.GET.get("topic", "")
    subtopic_slug = request.GET.get("subtopic", "")
    tag_slug = request.GET.get("tag", "")
    year = request.GET.get("year", "")
    month = request.GET.get("month", "")
    category = request.GET.get("category", "")
    view_mode = request.GET.get("view", "grid")
    sort = request.GET.get("sort", "-document_date")

    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(original_filename__icontains=q)
            | Q(tags__name__icontains=q)
        ).distinct()
    if topic_slug:
        qs = qs.filter(topic__slug=topic_slug)
    if subtopic_slug:
        qs = qs.filter(subtopic__slug=subtopic_slug)
    if tag_slug:
        qs = qs.filter(tags__slug=tag_slug)
    if year:
        qs = qs.filter(year=year)
    if month:
        qs = qs.filter(month=month)
    if category:
        qs = qs.filter(file_category=category)

    allowed_sorts = {"-document_date", "document_date", "title", "-created_at", "-file_size"}
    if sort in allowed_sorts:
        qs = qs.order_by(sort)

    paginator = Paginator(qs, 24 if view_mode == "grid" else 40)
    page_obj = paginator.get_page(request.GET.get("page"))

    querystring_no_page = request.GET.copy()
    querystring_no_page.pop("page", None)

    context = {
        "page_obj": page_obj,
        "documents": page_obj.object_list,
        "q": q,
        "topic_slug": topic_slug,
        "subtopic_slug": subtopic_slug,
        "tag_slug": tag_slug,
        "year": year,
        "month": month,
        "category": category,
        "view_mode": view_mode,
        "sort": sort,
        "category_choices": Document.CATEGORY_CHOICES,
        "saved_filters": SavedFilter.objects.filter(user=request.user),
        "querystring": querystring_no_page.urlencode(),
    }
    context.update(_build_sidebar_context())
    return render(request, "library/document_list.html", context)


@login_required
def duplicates(request):
    duplicate_groups = []
    hashes = (
        Document.objects.exclude(file_hash="")
        .values("file_hash")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .order_by("-count")
    )
    for row in hashes:
        docs = Document.objects.filter(file_hash=row["file_hash"]).select_related("topic")
        duplicate_groups.append({"hash": row["file_hash"], "count": row["count"], "documents": docs})

    return render(request, "library/duplicates.html", {"duplicate_groups": duplicate_groups})


@login_required
def document_upload(request):
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist("files")
            tags = Tag.get_or_create_many(form.cleaned_data["tags"])
            created = 0
            for f in files:
                file_hash = Document.compute_file_hash(f)
                doc = Document(
                    title=os.path.splitext(f.name)[0],
                    description=form.cleaned_data["description"],
                    file=f,
                    original_filename=f.name,
                    file_category=categorize_extension(f.name),
                    file_size=f.size,
                    file_hash=file_hash,
                    topic=form.cleaned_data["topic"],
                    subtopic=form.cleaned_data["subtopic"],
                    document_date=form.cleaned_data["document_date"],
                    uploaded_by=request.user,
                )
                doc.save()
                if tags:
                    doc.tags.set(tags)
                created += 1
            messages.success(request, f"Uploaded {created} file(s).")
            return redirect("library:document_list")
    else:
        form = DocumentUploadForm(initial={"document_date": timezone.now().date()})

    return render(request, "library/document_form.html", {"form": form, "mode": "upload"})


def _save_custom_fields(request, document):
    for field in document.applicable_custom_fields():
        key = f"field_{field.id}"
        if key in request.POST:
            value = request.POST.get(key, "").strip()
            if value:
                DocumentFieldValue.objects.update_or_create(
                    document=document, field=field, defaults={"value": value}
                )
            else:
                DocumentFieldValue.objects.filter(document=document, field=field).delete()


@login_required
def document_detail(request, pk):
    document = get_object_or_404(Document.objects.select_related("topic", "subtopic"), pk=pk)
    applicable_fields = list(document.applicable_custom_fields())
    value_map = document.field_value_map()
    for field in applicable_fields:
        field.current_value = value_map.get(field.id, "")

    if request.method == "POST" and request.POST.get("action") == "save_fields":
        _save_custom_fields(request, document)
        messages.success(request, "Custom field values updated.")
        return redirect("library:document_detail", pk=document.pk)

    return render(
        request,
        "library/document_detail.html",
        {"document": document, "applicable_fields": applicable_fields},
    )


@login_required
def document_edit(request, pk):
    document = get_object_or_404(Document, pk=pk)
    applicable_fields = list(document.applicable_custom_fields())
    value_map = document.field_value_map()

    if request.method == "POST":
        form = DocumentEditForm(request.POST, request.FILES)
        if form.is_valid():
            document.title = form.cleaned_data["title"]
            document.description = form.cleaned_data["description"]
            document.topic = form.cleaned_data["topic"]
            document.subtopic = form.cleaned_data["subtopic"]
            document.document_date = form.cleaned_data["document_date"]
            new_file = form.cleaned_data.get("replacement_file")
            if new_file:
                document.file = new_file
                document.original_filename = new_file.name
                document.file_category = categorize_extension(new_file.name)
                document.file_size = new_file.size
                document.file_hash = Document.compute_file_hash(new_file)
            document.save()
            document.tags.set(Tag.get_or_create_many(form.cleaned_data["tags"]))
            _save_custom_fields(request, document)
            messages.success(request, "Document updated.")
            return redirect("library:document_detail", pk=document.pk)
    else:
        form = DocumentEditForm(initial={
            "title": document.title,
            "description": document.description,
            "topic": document.topic,
            "subtopic": document.subtopic,
            "document_date": document.document_date,
            "tags": ", ".join(t.name for t in document.tags.all()),
        })

    for field in applicable_fields:
        field.current_value = value_map.get(field.id, "")

    return render(
        request,
        "library/document_form.html",
        {"form": form, "mode": "edit", "document": document, "applicable_fields": applicable_fields},
    )


@login_required
@require_POST
def document_delete(request, pk):
    document = get_object_or_404(Document, pk=pk)
    title = document.title
    document.file.delete(save=False)
    document.delete()
    messages.success(request, f"Deleted “{title}”.")
    return redirect("library:document_list")


# ---- Topics ----

@login_required
def topic_list(request):
    topics = Topic.objects.annotate(doc_count=Count("documents")).prefetch_related("subtopics")
    if request.method == "POST":
        form = TopicForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Topic created.")
            return redirect("library:topic_list")
    else:
        form = TopicForm()
    return render(request, "library/topic_list.html", {"topics": topics, "form": form})


@login_required
def topic_edit(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    if request.method == "POST":
        form = TopicForm(request.POST, instance=topic)
        if form.is_valid():
            form.save()
            messages.success(request, "Topic updated.")
            return redirect("library:topic_list")
    else:
        form = TopicForm(instance=topic)
    return render(request, "library/topic_form.html", {"form": form, "topic": topic})


@login_required
@require_POST
def topic_delete(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    topic.delete()
    messages.success(request, "Topic deleted. Its documents are kept, now unfiled.")
    return redirect("library:topic_list")


@login_required
@require_POST
def subtopic_add(request, topic_pk):
    topic = get_object_or_404(Topic, pk=topic_pk)
    form = SubtopicForm({"topic": topic.pk, "name": request.POST.get("name", "")})
    if form.is_valid():
        form.save()
        messages.success(request, "Subtopic added.")
    else:
        messages.error(request, "Could not add subtopic: " + str(form.errors))
    return redirect("library:topic_list")


@login_required
@require_POST
def subtopic_delete(request, pk):
    subtopic = get_object_or_404(Subtopic, pk=pk)
    subtopic.delete()
    messages.success(request, "Subtopic deleted.")
    return redirect("library:topic_list")


# ---- Tags ----

@login_required
def tag_list(request):
    tags = Tag.objects.annotate(doc_count=Count("documents")).order_by("-doc_count", "name")
    if request.method == "POST":
        form = TagForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Tag created.")
            return redirect("library:tag_list")
    else:
        form = TagForm()
    return render(request, "library/tag_list.html", {"tags": tags, "form": form})


@login_required
@require_POST
def tag_delete(request, pk):
    tag = get_object_or_404(Tag, pk=pk)
    tag.delete()
    messages.success(request, "Tag deleted.")
    return redirect("library:tag_list")


# ---- Custom fields ----

@login_required
def field_list(request):
    fields = CustomFieldDefinition.objects.select_related("topic")
    return render(request, "library/field_list.html", {"fields": fields})


@login_required
def field_add(request):
    if request.method == "POST":
        form = CustomFieldDefinitionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Custom field created.")
            return redirect("library:field_list")
    else:
        form = CustomFieldDefinitionForm()
    return render(request, "library/field_form.html", {"form": form, "mode": "add"})


@login_required
def field_edit(request, pk):
    field = get_object_or_404(CustomFieldDefinition, pk=pk)
    if request.method == "POST":
        form = CustomFieldDefinitionForm(request.POST, instance=field)
        if form.is_valid():
            form.save()
            messages.success(request, "Custom field updated.")
            return redirect("library:field_list")
    else:
        form = CustomFieldDefinitionForm(instance=field)
    return render(request, "library/field_form.html", {"form": form, "mode": "edit", "field": field})


@login_required
@require_POST
def field_delete(request, pk):
    field = get_object_or_404(CustomFieldDefinition, pk=pk)
    field.delete()
    messages.success(request, "Custom field deleted.")
    return redirect("library:field_list")


# ---- Saved filters ----

@login_required
@require_POST
def saved_filter_create(request):
    name = request.POST.get("name", "").strip()
    query_string = request.POST.get("query_string", "")
    if name:
        SavedFilter.objects.update_or_create(
            user=request.user, name=name, defaults={"query_string": query_string}
        )
        messages.success(request, f"Saved view “{name}”.")
    base_url = reverse("library:document_list")
    return redirect(f"{base_url}?{query_string}")


@login_required
@require_POST
def saved_filter_delete(request, pk):
    saved_filter = get_object_or_404(SavedFilter, pk=pk, user=request.user)
    saved_filter.delete()
    messages.success(request, "Saved view removed.")
    return redirect("library:document_list")


@login_required
def ajax_subtopics(request):
    """Return <option> HTML for subtopics belonging to a given topic (used by the upload/edit forms)."""
    topic_id = request.GET.get("topic")
    subtopics = Subtopic.objects.filter(topic_id=topic_id) if topic_id else Subtopic.objects.none()
    return render(request, "library/_subtopic_options.html", {"subtopics": subtopics})
