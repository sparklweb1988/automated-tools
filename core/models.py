from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_paid = models.BooleanField(default=False)  # Assuming this is for paid users
    subscription_end_date = models.DateTimeField(null=True, blank=True)  # Track subscription end date
    
    # This method will check if the subscription is still active based on the end date
    @property
    def is_subscription_active(self):
        if self.subscription_end_date:
            return self.subscription_end_date > datetime.now()
        return False
    
    def __str__(self):
        return self.user.username
