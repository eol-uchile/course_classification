# Generated by Django 2.2.24 on 2023-09-21 14:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course_classification', '0004_auto_20230921_1413'),
    ]

    operations = [
        migrations.AddField(
            model_name='maincourseclassification',
            name='visibility',
            field=models.IntegerField(choices=[(0, 'Portada'), (1, 'Buscador'), (2, 'Ambos')], default=2, verbose_name='Mostrar en'),
        ),
    ]
