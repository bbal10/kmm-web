from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


class District(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="Nama Distrik")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Distrik"
        verbose_name_plural = "Distrik"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class SchoolOrigin(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="Nama Sekolah")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Asal Sekolah"
        verbose_name_plural = "Asal Sekolah"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class ScholarshipSource(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="Nama Sumber Beasiswa")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Sumber Beasiswa"
        verbose_name_plural = "Sumber Beasiswa"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Student(models.Model):
    DEGREE_LEVEL_CHOICES = [
        ("mahad", "Mahad"),
        ("DL", "Daurah Lughah"),
        ("S1", "S1"),
        ("S2", "S2"),
        ("S3", "S3"),
    ]
    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
    ]
    MARITAL_STATUS_CHOICES = [
        ("single", "Single"),
        ("married", "Married"),
    ]
    EDUCATION_FUNDING_CHOICES = [
        ("beasiswa", "Beasiswa"),
        ("non-beasiswa", "Non-Beasiswa"),
    ]
    LEVEL_CHOICES = [
        ("maba", "Mahasiswa Baru"),
        ("regular", "Reguler"),
        ("alumni", "Alumni"),
    ]
    MEMBERSHIP_STATUS_CHOICES = [
        ("biasa", "Biasa"),
        ("luar_biasa", "Luar Biasa"),
        ("istimewa", "Istimewa"),
    ]
    INSTITUTION_CHOICES = [
        ("al_azhar", "Al-Azhar University"),
        ("mahad_al_azhar", "Ma'had Al Azhar"),
        ("markaz_zayed", "Markaz Syeikh Zayed"),
        ("dirasah_khassah", "Dirasah Khassah (Markaz Tatwir)"),
        ("other", "Lainnya"),
    ]
    FACULTY_CHOICES = [
        ("dakwah", "Dakwah Islamiyyah"),
        ("dirasat_insaniyyah", "Dirasat Insaniyyah"),
        ("dirasat_banat", "Dirasat Islamiyah wa Arabiyyah Banat"),
        ("dirasat_banin", "Dirasat Islamiyah wa Arabiyyah Banin"),
        ("dirasat_ulya", "Dirasat Ulya"),
        ("dirasat_ulum", "Dirasat Ulum"),
        ("handasah", "Handasah"),
        ("ilam", "Ilam"),
        ("ilmu_quran", "Ilmu Al-Quran"),
        ("kedokteran", "Kedokteran"),
        ("lughah_arabiyyah", "Lughah Arabiyyah"),
        ("syariah_qanun", "Syariah wa Qanun"),
        ("tarbiyyah", "Tarbiyyah"),
        ("tijarah", "Tijarah"),
        ("ushuluddin", "Ushuluddin"),
        ("other", "Lainnya"),
    ]
    MAJOR_CHOICES = [
        ("adab_naqd", "Adab wa Naqd"),
        ("akuntansi", "Akuntansi"),
        ("aqidah", "Aqidah"),
        ("balaghah_naqd", "Balaghah wa Naqd"),
        ("dakwah", "Dakwah"),
        ("fiqh_aam", "Fiqh Aam"),
        ("fiqh_muqaran", "Fiqh Muqaran"),
        ("hadis", "Hadis"),
        ("ilmu_quran", "Ilmu Alquran"),
        ("ilmu_nafs", "Ilmu Nafs"),
        ("kedokteran_gigi", "Kedokteran Gigi"),
        ("kedokteran_umum", "Kedokteran Umum"),
        ("lughah_almaniyyah", "Lughah Almaniyyah"),
        ("lughah_arabiyyah", "Lughah Arabiyyah"),
        ("riyadhah", "Riyadhah"),
        ("shahafah_ilam", "Shahafah wa Ilam"),
        ("syariah_islamiyyah", "Syariah Islamiyyah"),
        ("syariah_qanun", "Syariah wa Qanun"),
        ("tafsir", "Tafsir"),
        ("tarikh", "Tarikh"),
        ("tarikh_hadharah", "Tarikh wa Hadharah"),
        ("umum", "Umum"),
        ("ushul_fiqh", "Ushul Fiqh"),
        ("ushul_lughah", "Ushul Lughah"),
        ("other", "Lainnya"),
    ]
    TINGKAT_CHOICES = [
        ("1", "1"),
        ("2", "2"),
        ("3", "3"),
        ("4", "4"),
        ("5", "5"),
        ("6", "6"),
        ("7", "7"),
        ("tamhidi_1", "Tamhidi 1"),
        ("tamhidi_2", "Tamhidi 2"),
        ("magister", "Magister"),
        ("doktoral", "Doktoral"),
    ]
    LATEST_GRADE_CHOICES = [
        ("mumtaz", "Mumtaz"),
        ("jayyid_jiddan", "Jayyid Jiddan"),
        ("jayyid", "Jayyid"),
        ("maqbul", "Maqbul"),
        ("manqul", "Manqul"),
        ("manqulain", "Manqulain"),
        ("rosib", "Rosib"),
    ]
    LIVING_COST_CHOICES = [
        ("lt_1jt", "< 1 Jt"),
        ("1_2jt", "1-2 Jt"),
        ("2_3jt", "2-3 Jt"),
        ("gt_3jt", "> 3 Jt"),
    ]
    MONTHLY_INCOME_CHOICES = [
        ("lt_1jt", "< 1 Jt"),
        ("1_2jt", "1-2 Jt"),
        ("2_3jt", "2-3 Jt"),
        ("gt_3jt", "> 3 Jt"),
    ]

    user = models.OneToOneField(
        get_user_model(), on_delete=models.CASCADE, related_name="student_profile"
    )
    passport_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    lapdik_number = models.CharField(max_length=30, blank=True)
    birth_place = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    arrival_date = models.DateField(null=True, blank=True)
    school_origin = models.ForeignKey(
        SchoolOrigin, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Asal Sekolah"
    )
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, db_index=True)
    membership_status = models.CharField(
        max_length=20,
        choices=MEMBERSHIP_STATUS_CHOICES,
        blank=True,
        verbose_name="Status Keanggotaan",
    )
    region_origin = models.CharField(max_length=150, blank=True, verbose_name="Kabupaten/Kota Asal")
    whatsapp_number = models.CharField(max_length=20, blank=True)
    institution = models.CharField(
        max_length=50, choices=INSTITUTION_CHOICES, blank=True, verbose_name="Institusi"
    )
    institution_custom = models.CharField(max_length=200, blank=True, verbose_name="Institusi")
    faculty = models.CharField(
        max_length=50, choices=FACULTY_CHOICES, blank=True, verbose_name="Fakultas"
    )
    faculty_custom = models.CharField(max_length=200, blank=True, verbose_name="Fakultas")
    major = models.CharField(
        max_length=50, choices=MAJOR_CHOICES, blank=True, verbose_name="Jurusan"
    )
    major_custom = models.CharField(max_length=200, blank=True, verbose_name="Jurusan")
    degree_level = models.CharField(max_length=20, choices=DEGREE_LEVEL_CHOICES, db_index=True)
    semester_level = models.CharField(
        max_length=20, choices=TINGKAT_CHOICES, blank=True, verbose_name="Tingkat"
    )
    latest_grade = models.CharField(
        max_length=20, choices=LATEST_GRADE_CHOICES, blank=True, verbose_name="Nilai Terakhir"
    )
    home_name = models.CharField(max_length=200, blank=True)
    home_location = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Distrik"
    )
    parents_name = models.CharField(max_length=150, blank=True)
    parents_phone = models.CharField(
        max_length=50, blank=True, verbose_name="Nomor Telepon Orang Tua"
    )
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="maba", db_index=True)
    is_draft = models.BooleanField(default=False)

    # Health Information
    DISEASE_STATUS_CHOICES = [
        ("sembuh", "Sembuh"),
        ("belum", "Belum Sembuh"),
    ]
    disease_history = models.CharField(max_length=255, blank=True, verbose_name="Riwayat Penyakit")
    disease_status = models.CharField(max_length=10, choices=DISEASE_STATUS_CHOICES, blank=True)

    # Interests and Talents
    sport_interest = models.CharField(max_length=150, blank=True, verbose_name="Minat Olahraga")
    sport_achievement = models.TextField(blank=True, verbose_name="Prestasi Olahraga")
    art_interest = models.CharField(max_length=150, blank=True, verbose_name="Minat Kesenian")
    art_achievement = models.TextField(blank=True, verbose_name="Prestasi Kesenian")
    literacy_interest = models.CharField(max_length=150, blank=True, verbose_name="Minat Literasi")
    literacy_achievement = models.TextField(blank=True, verbose_name="Prestasi Literasi")
    science_interest = models.CharField(max_length=150, blank=True, verbose_name="Minat Keilmuan")
    science_achievement = models.TextField(blank=True, verbose_name="Prestasi Keilmuan")
    mtq_interest = models.CharField(max_length=150, blank=True, verbose_name="Minat MTQ")
    mtq_achievement = models.TextField(blank=True, verbose_name="Prestasi MTQ")
    media_interest = models.CharField(max_length=150, blank=True, verbose_name="Minat Media")
    media_achievement = models.TextField(blank=True, verbose_name="Prestasi Media")

    # Structured Interests (M2M)
    interests = models.ManyToManyField(
        "Interest",
        through="StudentInterest",
        blank=True,
        verbose_name="Minat",
    )

    # Organizational History
    organization_history = models.TextField(blank=True, verbose_name="Riwayat Organisasi")

    # Financial Information
    education_funding = models.CharField(
        max_length=20,
        choices=EDUCATION_FUNDING_CHOICES,
        blank=True,
        verbose_name="Sumber Pendanaan Pendidikan",
    )
    scholarship_source = models.ForeignKey(
        ScholarshipSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Sumber Beasiswa",
    )
    living_cost = models.CharField(
        max_length=20, choices=LIVING_COST_CHOICES, blank=True, verbose_name="Biaya Hidup Bulanan"
    )
    monthly_income = models.CharField(
        max_length=20, choices=MONTHLY_INCOME_CHOICES, blank=True, verbose_name="Pendapatan Bulanan"
    )

    # Guardian Information (Wali)
    photo = models.ImageField(
        upload_to="student_photos/",
        blank=True,
        null=True,
        verbose_name="Foto Profil",
    )
    photo_url = models.URLField(max_length=500, blank=True, verbose_name="Link Foto (Google Drive)")
    guardian_name = models.CharField(max_length=150, blank=True, verbose_name="Nama Wali/Umdah")
    guardian_phone = models.CharField(max_length=20, blank=True, verbose_name="Nomor HP Wali/Umdah")

    @property
    def email(self):
        """Get email from related user model"""
        return self.user.email if self.user else ""

    @property
    def full_name(self):
        """Get full name from related user model"""
        if self.user:
            full = f"{self.user.first_name} {self.user.last_name}".strip()
            return full or self.user.username
        return ""

    @property
    def institution_display(self):
        if self.institution == "other" and self.institution_custom:
            return self.institution_custom
        return self.get_institution_display() if self.institution else ""

    @property
    def faculty_display(self):
        if self.faculty == "other" and self.faculty_custom:
            return self.faculty_custom
        return self.get_faculty_display() if self.faculty else ""

    @property
    def major_display(self):
        if self.major == "other" and self.major_custom:
            return self.major_custom
        return self.get_major_display() if self.major else ""

    @property
    def scholarship_source_display(self):
        return str(self.scholarship_source) if self.scholarship_source else ""

    def __str__(self):
        return self.full_name


class InterestCategory(models.Model):
    CATEGORY_CHOICES = [
        ("olahraga", "Minat Olahraga"),
        ("seni", "Minat Seni"),
        ("literasi", "Minat Literasi"),
        ("keilmuan", "Minat Keilmuan"),
        ("mtq", "MTQ"),
        ("media", "Media"),
    ]

    slug = models.CharField(max_length=50, unique=True, choices=CATEGORY_CHOICES)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Kategori Minat"
        verbose_name_plural = "Kategori Minat"
        ordering = ["id"]

    def __str__(self):
        return self.name


class Interest(models.Model):
    category = models.ForeignKey(
        InterestCategory,
        on_delete=models.CASCADE,
        related_name="interests",
    )
    name = models.CharField(max_length=150, verbose_name="Nama Minat")
    allow_custom = models.BooleanField(
        default=False,
        verbose_name="Bisa Isi Sendiri",
        help_text="Centang jika mahasiswa boleh mengisi nilai kustom untuk pilihan ini.",
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Minat"
        verbose_name_plural = "Minat"
        ordering = ["category", "order", "name"]
        unique_together = [("category", "name")]

    def __str__(self):
        return f"{self.category.name} — {self.name}"


class StudentInterest(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="student_interests",
    )
    interest = models.ForeignKey(
        Interest,
        on_delete=models.CASCADE,
        related_name="student_interests",
    )
    # Used when interest.allow_custom is True (i.e. "Isi Sendiri")
    custom_value = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Isi Sendiri",
    )

    class Meta:
        verbose_name = "Minat Mahasiswa"
        verbose_name_plural = "Minat Mahasiswa"
        unique_together = [("student", "interest")]

    def __str__(self):
        label = (
            self.custom_value
            if self.interest.allow_custom and self.custom_value
            else self.interest.name
        )
        return f"{self.student} — {label}"


class EmailVerification(models.Model):
    EXPIRY_MINUTES = 30
    RESEND_COOLDOWN_SECONDS = 60
    MAX_ATTEMPTS = 5

    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="email_verification",
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempt_count = models.PositiveSmallIntegerField(default=0)
    last_resend_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Verifikasi Email"
        verbose_name_plural = "Verifikasi Email"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def can_resend(self):
        if not self.last_resend_at:
            return True
        return timezone.now() - self.last_resend_at >= timedelta(
            seconds=self.RESEND_COOLDOWN_SECONDS
        )

    def seconds_until_resend(self):
        if not self.last_resend_at:
            return 0
        elapsed = (timezone.now() - self.last_resend_at).total_seconds()
        return max(0, self.RESEND_COOLDOWN_SECONDS - int(elapsed))

    def __str__(self):
        return f"EmailVerification for {self.user.username}"
