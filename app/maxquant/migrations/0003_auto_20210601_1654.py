# Generated by Django 3.2.2 on 2021-06-01 16:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("maxquant", "0002_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="maxquantexecutable",
            options={
                "verbose_name": "MaxQuant Executable",
                "verbose_name_plural": "MaxQuant Executables",
            },
        ),
        migrations.AlterModelOptions(
            name="maxquantparameter",
            options={
                "verbose_name": "MaxQuant Parameter",
                "verbose_name_plural": "MaxQuant Parameters",
            },
        ),
        migrations.AlterModelOptions(
            name="maxquantpipeline",
            options={
                "verbose_name": "MaxQuant Pipeline",
                "verbose_name_plural": "MaxQuant Pipelines",
            },
        ),
        migrations.AlterModelOptions(
            name="maxquantresult",
            options={
                "verbose_name": "MaxQuant Result",
                "verbose_name_plural": "MaxQuant Results",
            },
        ),
        migrations.AlterModelOptions(
            name="rawfile",
            options={"verbose_name": "RawFile", "verbose_name_plural": "RawFiles"},
        ),
    ]
