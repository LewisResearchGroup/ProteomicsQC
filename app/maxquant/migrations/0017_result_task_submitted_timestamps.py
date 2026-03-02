from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("maxquant", "0016_result_cancel_tracking"),
    ]

    operations = [
        migrations.AddField(
            model_name="result",
            name="maxquant_task_submitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="result",
            name="rawtools_metrics_task_submitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="result",
            name="rawtools_qc_task_submitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
