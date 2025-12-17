"""
Migration to enable pgvector extension and create Memory model.
Run this SQL manually on your PostgreSQL database first:
CREATE EXTENSION IF NOT EXISTS vector;
"""
from django.db import migrations
from django.contrib.postgres.operations import CreateExtension


class Migration(migrations.Migration):
    dependencies = [
        ('assistant', '0003_agendaevent_send_notification_and_more'),
    ]

    operations = [
        # Note: CreateExtension requires superuser privileges
        # If you don't have superuser, run this SQL manually:
        # CREATE EXTENSION IF NOT EXISTS vector;
        # CreateExtension(name='vector'),
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="DROP EXTENSION IF EXISTS vector;"
        ),
    ]

