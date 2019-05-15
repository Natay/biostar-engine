# Generated by Django 2.2 on 2019-05-11 20:48

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('message', '0004_html'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='recipient_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='message',
            name='sender_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='message',
            name='spam',
            field=models.IntegerField(choices=[(0, 'Spam'), (1, 'Not spam'), (2, 'Unknown')], default=2),
        ),
        migrations.CreateModel(
            name='BlockList',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(default='', max_length=10000)),
                ('uid', models.CharField(default='229ae4b1-4', max_length=32, unique=True)),
                ('blocked', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='blocked', to=settings.AUTH_USER_MODEL)),
                ('source_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='source', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]