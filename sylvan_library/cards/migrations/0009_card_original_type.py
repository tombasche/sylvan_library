# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-12-22 02:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0008_card_original_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='card',
            name='original_type',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
