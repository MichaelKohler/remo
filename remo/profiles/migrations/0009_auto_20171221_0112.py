# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0008_auto_20171025_2031'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='userprofile',
            options={'permissions': (('create_user', 'Can create new user'), ('can_edit_profiles', 'Can edit profiles'), ('can_delete_profiles', 'Can delete profiles'), ('can_change_mentor', 'Can change mentors'))},
        ),
    ]
