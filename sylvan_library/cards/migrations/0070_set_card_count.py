# Generated by Django 2.2.1 on 2019-06-15 18:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("cards", "0069_auto_20190601_1431")]

    operations = [
        migrations.AddField(
            model_name="set",
            name="card_count",
            field=models.IntegerField(default=0),
            preserve_default=False,
        )
    ]
