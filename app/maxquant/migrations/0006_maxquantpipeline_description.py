# Generated by Django 3.2.5 on 2021-08-12 16:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("maxquant", "0005_maxquantexecutable_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="maxquantpipeline",
            name="description",
            field=models.TextField(default="", max_length=10000),
        ),
    ]
