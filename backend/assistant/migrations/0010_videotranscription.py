# Generated migration for VideoTranscription model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('assistant', '0009_todoitem'),
    ]

    operations = [
        migrations.CreateModel(
            name='VideoTranscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.CharField(help_text='Original video filename', max_length=500)),
                ('transcription_text', models.TextField(help_text='Full transcription text with timestamps and speakers')),
                ('language', models.CharField(default='pt', help_text='Detected or selected language', max_length=10)),
                ('diarization_enabled', models.BooleanField(default=True, help_text='Whether speaker diarization was enabled')),
                ('speaker_mappings', models.JSONField(blank=True, default=dict, help_text='Mapping of speaker IDs (User1, User2, etc.) to actual names')),
                ('summary', models.TextField(blank=True, help_text='AI-generated summary of the meeting/conversation', null=True)),
                ('summary_generating', models.BooleanField(default=False, help_text='Whether summary generation is in progress')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='video_transcriptions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='videotranscription',
            index=models.Index(fields=['user', 'created_at'], name='assistant_vt_user_created_idx'),
        ),
        migrations.AddIndex(
            model_name='videotranscription',
            index=models.Index(fields=['user', 'updated_at'], name='assistant_vt_user_updated_idx'),
        ),
    ]
