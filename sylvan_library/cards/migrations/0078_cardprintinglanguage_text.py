# Generated by Django 2.2.1 on 2019-08-11 10:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("cards", "0077_card_face_cmc")]

    operations = [
        migrations.AddField(
            model_name="cardprintinglanguage",
            name="text",
            field=models.CharField(blank=True, max_length=1000, null=True),
        )
    ]