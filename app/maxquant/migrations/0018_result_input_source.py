from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("maxquant", "0017_result_task_submitted_timestamps"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE maxquant_result "
                        "ADD COLUMN IF NOT EXISTS input_source varchar(32) "
                        "NOT NULL DEFAULT 'upload';"
                    ),
                    reverse_sql=(
                        "ALTER TABLE maxquant_result "
                        "DROP COLUMN IF EXISTS input_source;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="result",
                    name="input_source",
                    field=models.CharField(default="upload", max_length=32),
                ),
            ],
        ),
    ]
