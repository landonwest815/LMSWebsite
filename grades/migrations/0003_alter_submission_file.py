# Generated by Django 5.1 on 2024-10-26 02:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grades', '0002_rename_max_points_assignment_points'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='file',
            field=models.FileField(upload_to=''),
        ),
    ]
