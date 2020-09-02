from django.db import migrations, models

from djangocms_picture.models import get_alignment


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_picture', '0006_remove_null_values'),
    ]

    operations = [
        migrations.AlterField(
            model_name='picture',
            name='alignment',
            field=models.CharField(blank=True, help_text='Aligns the image according to the selected option.', max_length=255, verbose_name='Alignment', choices=get_alignment()),
        ),
    ]
