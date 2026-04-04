from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_management', '0025_seed_district_school_scholarship'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='student',
            name='citizenship_status',
        ),
        migrations.AlterField(
            model_name='student',
            name='region_origin',
            field=models.CharField(blank=True, max_length=150, verbose_name='Kabupaten/Kota Asal'),
        ),
    ]
