# DataVault

A standalone app for organising and cleaning up files — documents, images,
videos, presentations, scans, PDFs, anything — so they're easy to find again.

It is intentionally separate from any other system in this repository: its
own Django project, own database, own login. It doesn't touch or depend on
anything else here.

## What it does

- **Upload** one or many files at once (drag in a whole folder's worth of scans/photos).
- **Organise by topic and subtopic** — you create your own categories, not a fixed list
  (e.g. Topic "Billing" → Subtopics "Invoices", "Receipts").
- **Organise by month/year** automatically, from a date you assign to each file — browse
  the sidebar by year → month.
- **Tags** — free-form, create as many as you like, filter by them.
- **Custom fields** — define your own extra fields (text, number, date, yes/no, or a
  choice list) globally or scoped to one topic, and fill them in per file.
- **Search** across titles, descriptions, filenames and tags.
- **Saved views** — save a combination of filters under a name and reopen it in one click.
- **Grid or list** view, sortable.
- **Clean-up tools**: a *Duplicates* page finds files with byte-identical content (by
  checksum) so you can delete the extra copies; the dashboard flags files with no topic
  assigned yet.
- Inline preview for images, video and PDF; everything else gets a download link.

## Running it locally

```bash
cd datavault
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py createsuperuser
./.venv/bin/python manage.py seed_demo   # optional: adds a few starter topics
./.venv/bin/python manage.py runserver
```

Then open http://127.0.0.1:8000/ and log in with the superuser account you created.

By default it uses SQLite and stores uploaded files under `datavault/media/` — nothing
else to configure for personal/single-clinic use.

## Configuration (environment variables, all optional)

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | a dev-only placeholder | set a real secret key in production |
| `DEBUG` | `True` | set to `False` in production |
| `ALLOWED_HOSTS` | `*` | comma-separated list of hostnames in production |
| `TIME_ZONE` | `Asia/Kolkata` | affects how "month/year" is computed from timestamps |

## Running with Docker

```bash
cd datavault
docker build -t datavault .
docker run -p 8000:8000 \
  -e SECRET_KEY=change-me \
  -e ALLOWED_HOSTS=yourdomain.com \
  -v datavault_media:/app/media \
  -v datavault_db:/app \
  datavault
```

Then exec in once to create your first login:

```bash
docker exec -it <container> python manage.py createsuperuser
```

For anything beyond single-user/small-team use, put this behind Postgres instead of
SQLite and a real reverse proxy (nginx/Caddy) serving `/media/` — the Dockerfile ships
Gunicorn + Whitenoise for static files (CSS/JS), but media files are served by Django
directly only when `DEBUG=True`.

## Customising it

- **Topics & Subtopics** — manage page at `/topics/`: add, rename (edit), delete, add
  subtopics inline. Deleting a topic doesn't delete its files, they just become unfiled.
- **Tags** — manage page at `/tags/`, or just type new tag names (comma-separated) on any
  upload/edit form and they're created automatically.
- **Custom fields** — manage page at `/fields/`. Each field can be text, number, date,
  yes/no, or a choice list (comma-separated options), and can be global or restricted to
  one topic. They show up automatically on that topic's upload and edit pages.
- **Saved views** — on the Browse page, set up filters (topic/tag/year/month/etc.), then
  click "Save view" and give it a name; it reappears in the sidebar.

## Project layout

```
datavault/
  config/        Django project settings/urls
  library/       the app: models, views, forms, admin, migrations
  templates/     all page templates
  static/        CSS and JS
  manage.py
```

The Django admin (`/admin/`) also works, if you ever want bulk edits or a raw data view.
