from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ia", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="consultaia",
            name="sesion",
            field=models.CharField(blank=True, db_index=True, max_length=40),
        ),
        migrations.AddField(
            model_name="consultaia",
            name="modulo",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name="consultaia",
            name="conversacion",
            field=models.CharField(blank=True, db_index=True, max_length=36),
        ),
        migrations.AddField(
            model_name="consultaia",
            name="resultado",
            field=models.TextField(blank=True),
        ),
    ]
