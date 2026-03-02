from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("maxquant", "0015_auto_20220407_1715"),
    ]

    operations = [
        migrations.AddField(
            model_name="result",
            name="cancel_requested_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="result",
            name="maxquant_task_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="result",
            name="rawtools_metrics_task_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="result",
            name="rawtools_qc_task_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
