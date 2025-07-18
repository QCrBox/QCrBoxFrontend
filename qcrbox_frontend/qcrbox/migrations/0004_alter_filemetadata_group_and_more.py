# pylint: skip-file

# Generated by Django 5.2.1 on 2025-05-29 12:54

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("qcrbox", "0003_remove_processstep_group_remove_processstep_user_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="filemetadata",
            name="group",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="auth.group"
            ),
        ),
        migrations.AlterField(
            model_name="processstep",
            name="infile_uuid",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="processed_to",
                to="qcrbox.filemetadata",
            ),
        ),
        migrations.AlterField(
            model_name="processstep",
            name="outfile_uuid",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="processed_by",
                to="qcrbox.filemetadata",
            ),
        ),
        migrations.AlterField(
            model_name="processstep",
            name="parent",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="children",
                to="qcrbox.processstep",
            ),
        ),
    ]
