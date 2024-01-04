# Generated by Django 4.2.4 on 2024-01-01 14:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenditure', '0006_remove_expendituregroup_user_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='expenditure',
            name='attachment',
            field=models.CharField(blank=True, max_length=256, null=True, verbose_name='Attachment'),
        ),
        migrations.AddField(
            model_name='expenditure',
            name='category',
            field=models.CharField(default='others', max_length=256, verbose_name='Category'),
        ),
        migrations.AlterField(
            model_name='expenditure',
            name='location',
            field=models.CharField(blank=True, max_length=256, null=True, verbose_name='Location'),
        ),
    ]
