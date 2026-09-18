import uuid

import apps.accounts.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # Only need auth.Group/auth.Permission (for PermissionsMixin's M2M
        # fields below) to exist, which 0001_initial already creates — this
        # is deliberately the first auth migration, not "whatever the
        # latest happens to be", so it doesn't break on a Django version
        # whose auth app has a different migration count.
        ("auth", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.SmallAutoField(primary_key=True, serialize=False)),
                ("code", models.CharField(max_length=32, unique=True)),
            ],
            options={"db_table": "roles"},
        ),
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(
                    default=False,
                    help_text="Designates that this user has all permissions without explicitly assigning them.",
                    verbose_name="superuser status",
                )),
                ("name", models.CharField(max_length=200)),
                ("phone", models.CharField(max_length=20, unique=True)),
                ("email", models.EmailField(blank=True, max_length=254, null=True, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("is_staff", models.BooleanField(default=False)),
                ("date_joined", models.DateTimeField(auto_now_add=True)),
                ("groups", models.ManyToManyField(
                    blank=True,
                    help_text="The groups this user belongs to.",
                    related_name="user_set",
                    related_query_name="user",
                    to="auth.group",
                    verbose_name="groups",
                )),
                ("role", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="users",
                    to="accounts.role",
                )),
                ("user_permissions", models.ManyToManyField(
                    blank=True,
                    help_text="Specific permissions for this user.",
                    related_name="user_set",
                    related_query_name="user",
                    to="auth.permission",
                    verbose_name="user permissions",
                )),
            ],
            options={"db_table": "users"},
            managers=[
                ("objects", apps.accounts.models.UserManager()),
            ],
        ),
    ]
