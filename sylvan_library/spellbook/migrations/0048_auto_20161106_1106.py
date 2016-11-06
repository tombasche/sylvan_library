# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-11-06 00:06
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('spellbook', '0047_auto_20160801_2251'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cardlink',
            name='card_from',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='card_from', to='spellbook.Card'),
        ),
        migrations.AlterField(
            model_name='cardlink',
            name='card_to',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='card_to', to='spellbook.Card'),
        ),
    ]