# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-12-22 01:30
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0006_cardlegality_restriction'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='cardlegality',
            unique_together=set([('card', 'format', 'restriction')]),
        ),
    ]
