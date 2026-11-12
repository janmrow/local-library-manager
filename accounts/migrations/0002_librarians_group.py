"""Create the staff group (slice 2: librarian role)."""

from django.db import migrations


def create_librarians_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="Librarians")


def remove_librarians_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Librarians").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_librarians_group, remove_librarians_group),
    ]
