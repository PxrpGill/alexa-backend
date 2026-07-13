from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='blogpost',
            old_name='cover',
            new_name='poster',
        ),
        migrations.AlterField(
            model_name='blogpost',
            name='poster',
            field=models.ImageField(blank=True, upload_to='blog/', verbose_name='Постер'),
        ),
        migrations.RenameField(
            model_name='blogpost',
            old_name='excerpt',
            new_name='description',
        ),
        migrations.AlterField(
            model_name='blogpost',
            name='description',
            field=models.TextField(verbose_name='Описание'),
        ),
        migrations.AddField(
            model_name='blogpost',
            name='preview_poster',
            field=models.ImageField(blank=True, upload_to='blog/', verbose_name='Превью постера'),
        ),
    ]
