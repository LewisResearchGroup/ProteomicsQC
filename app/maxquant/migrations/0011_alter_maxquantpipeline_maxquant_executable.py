# Generated by Django 3.2.5 on 2021-08-13 00:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("maxquant", "0010_auto_20210812_2239"),
    ]

    operations = [
        migrations.AlterField(
            model_name="maxquantpipeline",
            name="maxquant_executable",
            field=models.FilePathField(
                blank=True,
                help_text="If this field is empty the default MaxQuant version (1.6.10.43) will be used. To try a different version go to MaxQuant Executables. If this is changed, all MaxQuant jobs in this pipeline should be rerun.",
                match=".*MaxQuantCmd.exe",
                max_length=2000,
                null=True,
                path="/compute",
                recursive=True,
            ),
        ),
    ]
