from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile
from producers.models import Producer

User = get_user_model()
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(
            user=instance,
            role="customer"
        )

# When a UserProfile is saved, check if the role is "producer". 
# If so, create a Producer profile if it doesn't exist. 
# If the role is changed to something else, delete any existing Producer profile.
@receiver(post_save, sender=UserProfile)
def manage_producer_profile(sender, instance, **kwargs):
    if instance.role == "producer":
        Producer.objects.get_or_create(
            user=instance.user,
            defaults={
                "display_name": instance.user.username,
                "bio": "",
                "location": "",
                "phone": "",
                "website": "",
            },
        )
    else:
        Producer.objects.filter(user=instance.user).delete()