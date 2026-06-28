import random
import secrets
import string

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from faker import Faker

from data_management.forms import get_region_origin_choices
from data_management.models import Student


def generate_random_password(length=12):
    """Generate a random password using the secrets module."""
    characters = string.ascii_letters + string.digits + string.punctuation
    password = "".join(secrets.choice(characters) for i in range(length))
    return password


def generate_living_cost(minimum=1500000, maximum=5000000):
    return random.randint(minimum, maximum)


class Command(BaseCommand):
    help = "Seed 100 student records linked to users, create or update as needed with Faker data (username & email faker)"

    def handle(self, *args, **kwargs):
        fake = Faker("id_ID")
        fake.unique.clear()
        User = get_user_model()
        degree_levels = ["D3", "S1", "S2", "S3"]
        genders = ["M", "F"]
        marital_statuses = ["single", "married"]
        levels = ["maba", "regular", "alumni"]
        disease_statuses = ["sembuh", "belum"]
        region_origin_choices = [value for value, _ in get_region_origin_choices()]

        total_created = 0
        total_updated = 0

        for _ in range(100):
            username = fake.unique.user_name()
            email = fake.unique.email()
            student_email = fake.unique.email()
            password = generate_random_password()

            # Buat user jika belum ada
            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "is_active": True,
                },
            )
            if user_created:
                user.set_password(password)
                user.save()

            # Buat/Update student untuk user ini
            # Hapus field 'education_funding' dan 'living_cost' JIKA TIDAK ADA di models.Student
            student_defaults = {
                "full_name": fake.name(),
                "passport_number": fake.unique.bothify(text="##########"),
                "lapdik_number": fake.unique.bothify(text="LPDK#######"),
                "birth_place": fake.city(),
                "birth_date": fake.date_of_birth(minimum_age=17, maximum_age=30),
                "gender": random.choice(genders),
                "arrival_date": fake.date_this_decade(),
                "school_origin": fake.company(),
                "marital_status": random.choice(marital_statuses),
                "region_origin": (
                    random.choice(region_origin_choices) if region_origin_choices else fake.city()
                ),
                "whatsapp_number": fake.unique.phone_number(),
                "email": student_email,
                "institution": fake.company(),
                "faculty": fake.word(),
                "major": fake.job(),
                "degree_level": random.choice(degree_levels),
                "semester_level": random.randint(1, 14),
                "latest_grade": round(random.uniform(2.00, 4.00), 2),
                "home_name": fake.street_name(),
                "home_location": fake.address(),
                "parents_name": fake.name(),
                "level": random.choice(levels),
                "disease_history": fake.sentence(),
                "disease_status": random.choice(disease_statuses),
                "sport_interest": fake.word(),
                "sport_achievement": fake.sentence(),
                "art_interest": fake.word(),
                "art_achievement": fake.sentence(),
                "literacy_interest": fake.word(),
                "literacy_achievement": fake.sentence(),
                "science_interest": fake.word(),
                "science_achievement": fake.sentence(),
                "mtq_interest": fake.word(),
                "mtq_achievement": fake.sentence(),
                "media_interest": fake.word(),
                "media_achievement": fake.sentence(),
                "organization_history": fake.paragraph(),
            }
            student, created = Student.objects.update_or_create(
                user=user, defaults=student_defaults
            )

            if created:
                total_created += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Student baru untuk user "{username}" berhasil dibuat.')
                )
            else:
                total_updated += 1
                self.stdout.write(
                    self.style.WARNING(f'Student untuk user "{username}" berhasil diperbarui.')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Total student dibuat: {total_created}, diperbarui: {total_updated}"
            )
        )
