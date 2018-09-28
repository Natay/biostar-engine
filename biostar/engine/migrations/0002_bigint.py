# Generated by Django 2.0.1 on 2018-09-28 13:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='analysis',
            name='security',
            field=models.IntegerField(choices=[(1, 'All users may run recipe'), (2, 'Only moderators may run recipe')], default=2),
        ),
        migrations.AlterField(
            model_name='data',
            name='size',
            field=models.BigIntegerField(default=0),
        ),
    ]