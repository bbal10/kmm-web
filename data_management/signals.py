from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Student

User = get_user_model()


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        print(f"Creating profile for user: {instance}")
        Student.objects.create(
            user=instance,  # <-- use the User instance, not username
            # full_name and email are now properties from User, don't set them
            gender='M',  # set default or logic as needed
            marital_status='single',
            degree_level='S1',
            semester_level='1',
        )
