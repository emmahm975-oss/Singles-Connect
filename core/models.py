from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female')]
    INTENTION_CHOICES = [('marriage', 'Marriage'), ('longterm', 'Long-term'), ('friendship', 'Friendship')]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    hobbies = models.CharField(max_length=300, blank=True)
    intention = models.CharField(max_length=20, choices=INTENTION_CHOICES, default='longterm')
    pref_gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='F')
    pref_min_age = models.PositiveIntegerField(default=18)
    pref_max_age = models.PositiveIntegerField(default=40)
    pref_country = models.CharField(max_length=100, blank=True)
    profile_photo = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.full_name

# SECTION 8 & 10: The Checkout and Admin Payment Details
class CheckoutSession(models.Model):
    STATUS_CHOICES = [
        ('pending_admin', 'Waiting for Admin Details'),
        ('pending_payment', 'Awaiting User Payment'),
        ('pending_verification', 'Pending Verification'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]
    
    member = models.ForeignKey(User, on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_checkouts', on_delete=models.CASCADE)
    reference = models.CharField(max_length=20, unique=True)
    country = models.CharField(max_length=100)
    currency = models.CharField(max_length=10)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_admin')
    
    # Admin supplied details
    payment_provider = models.CharField(max_length=200, blank=True, null=True)
    recipient_name = models.CharField(max_length=200, blank=True, null=True)
    payment_number = models.CharField(max_length=200, blank=True, null=True)
    admin_instructions = models.TextField(blank=True, null=True)
    
    # User submitted evidence
    evidence_screenshot = models.ImageField(upload_to='evidence/', blank=True, null=True)
    evidence_text = models.TextField(blank=True)
    transaction_ref = models.CharField(max_length=100, blank=True)
    payment_date = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

# SECTION 14: Connections unlocked after approval
class Connection(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_connections')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_connections')
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    connection = models.ForeignKey(Connection, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.username}: {self.content[:20]}"

class SuccessStory(models.Model):
    couple_names = models.CharField(max_length=200)
    countries = models.CharField(max_length=100)
    testimonial = models.TextField()
    photo = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.couple_names
class BlockedUser(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_users')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by')
    created_at = models.DateTimeField(auto_now_add=True)

class Meta:
        unique_together = ('blocker', 'blocked')