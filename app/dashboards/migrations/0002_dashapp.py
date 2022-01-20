# Generated by Django 3.2.5 on 2021-08-12 16:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("dashboards", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DashApp",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "instance_name",
                    models.CharField(blank=True, max_length=100, unique=True),
                ),
                ("slug", models.SlugField(blank=True, max_length=110, unique=True)),
                ("base_state", models.TextField(default="{}")),
                ("creation", models.DateTimeField(auto_now_add=True)),
                ("update", models.DateTimeField(auto_now=True)),
                ("save_on_change", models.BooleanField(default=False)),
                (
                    "stateless_app",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="dashboards.statelessproteomicsdashboardapp",
                    ),
                ),
            ],
        ),
    ]
