from django.db import migrations


DISTRICTS = [
    '1st Settlement',
    'Suuq Asyir',
    'Madrasah Asyir',
    'Musallas Asyir',
    "Gami' Asyir",
    'Bawabat Asyir',
    'Hafez Badawy Hayy 7',
    'Abdul Qahir Al Gargawy Hayy 7',
    'Omar El Mokhtar Hayy 7',
    'Mohamed Farid Abou Hadid Hayy 7',
    'Taha Dinary Hayy 7',
    'El Shafy Mohammed Hayy 7',
    'Ibrahim Abou El Naga Hayy 7',
    'Fateh Allah refaat Hayy 7',
    'Al Mahdi Ibn Baraka Hayy 7',
    'Abou Hayan Al Tawhid Hayy 7',
    'Ahmed Hasan El Zayyad Hayy 7',
    'Ismail Zohdy Hayy 7',
    'Gamal Al Din Al Shayal Hayy 7',
    'Dr Mohammed Al Nabawy Hayy 7',
    'Mohamed Hamid Hayy 7',
    'Mohammed Faheem Hayy 7',
    'Mohammed El Saedy Hayy 7',
    'Taher Al Gazairy Hayy 7',
    'Abou Ramy Hayy 7',
    'Misr wa Sudan Hayy 7',
    'Awwal Sabea Hayy 7',
    'Hadiqoh Dauliyyah Hayy 7',
    'Hayy Tsamin',
    "Hayy Tasi'",
    'Gamaliya',
    'Khadrawy Darrasah',
    'Darb Ad Dalil Darrasah',
    "Rifa'i Darrasah",
    'Juwaini Darrasah',
    'Aslan Darrasah',
    'Sayyidah Fathimah Darrasah',
    'Tanbugho Darrasah',
    'Darbul Ansiyyah Darrasah',
    'Bab Zuwaila Darrasah',
    'Ghurriyah Darrasah',
    'Dardir Darrasah',
    'Simpang X Darrasah',
    'Kanisah Darrasah',
    'Belakang Azhar Darrasah',
    "Bab Sya'riah",
    'Muqattam',
]

SCHOOL_ORIGINS = [
    "Ma'had Al-Azhar Mesir",
    'SMA IT Insan Cendekia',
    'MA Ar-Risalah',
    'MAN 2 kota Padang Panjang',
    'MA Sumatera Thawalib Parabek',
    'PonPes Diniyah Limo Jurai',
    'PPM Diniyah Pasia',
    'MA Daarul Muwahhidiin',
    'PPTQ Muallimin Muhammadiyah Sawah Dangka',
    'Perguruan Thawalib Putera Padang Panjang',
    'MAS KMI Diniyyah Putri',
    'MAN 2 Kota Padang',
    'MAN 2 Kota Payakumbuh',
    'MAN 3 Kota Padang Panjang',
    'MAN 2 Tanah Datar',
    'MAN 3 Tanah Datar',
    'MAN 1 Bukittinggi',
    'MAN 2 Bukittinggi',
    'MAN 1 Solok Selatan',
    'MAN 1 Pasaman',
    'MAN 5 Pasaman Barat',
    'PonPes Nurul Yaqin Ringan-Ringan',
    'MTI Canduang',
    'PPM Darussalam Gontor',
    "Bai'turridhwan Bukittinggi",
    'Pesantren Darul Ulum Lintau',
    'Pesantren Darul Ulum Padang',
    'Yarsi',
    'MA Jabal Rahmah',
    'SMA Terpadu Darul Amal',
    'Ponpes Ashabul Yamin',
    'MAN 1 Pasaman',
    'MAS Taman Raya Balingja',
    'Ponpes Madinah Al-Hijrah',
    'MA Al-Ikhwan',
    'PPTQ Syech Ahmad Khatib Al-Minangkabawi',
    'SMA Adzkia',
    'PonPes Kauman Muhammadiyah Padang Panjang',
    'MAN 1 Solok',
    'SMAN 1 Payakumbuh',
    "Ma'had Al-Hufaz",
    'MAS PPI Haji Miskin',
    'MA ST Guguak Randah',
    'PonPes Istiqamah Ombilin',
    'MTI Syeikh Muhammad Djamil Jaho',
    'PonPes Prof Dr Hamka Maninjau',
    'MAS TI Lubeg Padang',
    'SMA Dian Andalas Padang',
    'PP Thawalib Tanjung Limau Batusangkar',
    'Ponpes Abi Center',
]

SCHOLARSHIP_SOURCES = [
    'Beasiswa Buuts Dakhili',
    'Beasiswa Buuts Khariji',
    "Beasiswa Majlis A'la",
    'Beasiswa Baznas',
    'Beasiswa ASFA',
    'Beasiswa Bait Zakat Kuwait',
]


def seed_data(apps, schema_editor):
    District = apps.get_model('data_management', 'District')
    SchoolOrigin = apps.get_model('data_management', 'SchoolOrigin')
    ScholarshipSource = apps.get_model('data_management', 'ScholarshipSource')

    for i, name in enumerate(DISTRICTS):
        District.objects.get_or_create(name=name, defaults={'order': i})

    for i, name in enumerate(SCHOOL_ORIGINS):
        SchoolOrigin.objects.get_or_create(name=name, defaults={'order': i})

    for i, name in enumerate(SCHOLARSHIP_SOURCES):
        ScholarshipSource.objects.get_or_create(name=name, defaults={'order': i})


def reverse_seed(apps, schema_editor):
    District = apps.get_model('data_management', 'District')
    SchoolOrigin = apps.get_model('data_management', 'SchoolOrigin')
    ScholarshipSource = apps.get_model('data_management', 'ScholarshipSource')
    District.objects.filter(name__in=DISTRICTS).delete()
    SchoolOrigin.objects.filter(name__in=SCHOOL_ORIGINS).delete()
    ScholarshipSource.objects.filter(name__in=SCHOLARSHIP_SOURCES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('data_management', '0024_choices_to_fk_models'),
    ]

    operations = [
        migrations.RunPython(seed_data, reverse_seed),
    ]
