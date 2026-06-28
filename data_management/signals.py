import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Student

User = get_user_model()
logger = logging.getLogger("data_management")


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        logger.info("Creating profile for user: %s", instance)
        Student.objects.create(
            user=instance,
            gender="M",
            marital_status="single",
            degree_level="S1",
            semester_level="1",
        )
