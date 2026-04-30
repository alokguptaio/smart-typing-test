from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


# ═══════════════════════════════════════════════════
#  EMAIL VERIFICATION
#  Register hone ke baad email verify karne ke liye
# ═══════════════════════════════════════════════════
class EmailVerification(models.Model):
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_verification')
    token       = models.CharField(max_length=255, default=uuid.uuid4, unique=True)
    is_verified = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = '✅ Verified' if self.is_verified else '❌ Not Verified'
        return f"{self.user.email} — {status}"


# ═══════════════════════════════════════════════════
#  PASSWORD RESET
#  Forgot password ke liye token — 24 ghante valid
# ═══════════════════════════════════════════════════
class PasswordReset(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_resets')
    token      = models.CharField(max_length=255, default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        """Token 24 ghante mein expire hota hai."""
        return timezone.now() > self.created_at + timezone.timedelta(hours=24)

    def __str__(self):
        return f"Reset — {self.user.email}"


# ═══════════════════════════════════════════════════
#  USER PROFILE
#  Har user ka payment/plan data
#  is_paid     → Free ya Paid
#  plan        → week/month/3month/6month
#  expiry_date → Plan kab expire hoga
# ═══════════════════════════════════════════════════
class UserProfile(models.Model):
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_paid     = models.BooleanField(default=False)
    plan        = models.CharField(max_length=20, null=True, blank=True)
    paid_date   = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True)

    def is_active(self):
        """Plan active hai ya expire ho gaya — auto reset karta hai."""
        if not self.is_paid:
            return False
        if self.expiry_date and timezone.now() > self.expiry_date:
            self.is_paid     = False
            self.plan        = None
            self.expiry_date = None
            self.save()
            return False
        return True

    def days_left(self):
        """Kitne din baaki hain plan mein."""
        if not self.expiry_date:
            return 0
        delta = self.expiry_date - timezone.now()
        return max(0, delta.days)

    def __str__(self):
        return f"{self.user.username} — {self.plan or 'Free'}"


# ═══════════════════════════════════════════════════
#  PAYMENT REQUEST
#  Har payment attempt ka record
#  unique_amount = base + random paise (e.g. 9.47)
#  QR 60 seconds mein expire hota hai
#  Admin approve karta hai
# ═══════════════════════════════════════════════════
class PaymentRequest(models.Model):

    PLAN_CHOICES = [
        ('week',   '1 Week — ₹9'),
        ('month',  '1 Month — ₹19'),
        ('3month', '3 Months — ₹49'),
        ('6month', '6 Months — ₹99'),
    ]
    STATUS_CHOICES = [
        ('pending',  'Pending — Verify Karo'),
        ('approved', 'Approved ✅'),
        ('expired',  'Expired ⏰'),
        ('rejected', 'Rejected ❌'),
    ]
    PLAN_PRICES = {'week': 9, 'month': 19, '3month': 49, '6month': 99}
    PLAN_DAYS   = {'week': 7, 'month': 30, '3month': 90, '6month': 180}

    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_requests')
    plan            = models.CharField(max_length=20, choices=PLAN_CHOICES)
    base_amount     = models.IntegerField()
    unique_paise    = models.IntegerField()
    unique_amount   = models.DecimalField(max_digits=6, decimal_places=2)
    transaction_ref = models.CharField(max_length=100, blank=True, default='')
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at      = models.DateTimeField(auto_now_add=True)
    expires_at      = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    def is_expired(self):
        return timezone.now() > self.expires_at

    def seconds_left(self):
        delta = self.expires_at - timezone.now()
        return max(0, int(delta.total_seconds()))

    def __str__(self):
        return f"{self.user.username} | {self.plan} | ₹{self.unique_amount} | {self.status}"


# ═══════════════════════════════════════════════════
#  PASSAGE
#  Typing test ke passages
#  is_free = True  → Free users ko milega
#  is_free = False → Sirf Paid users ko (Lock 🔒)
# ═══════════════════════════════════════════════════
class Passage(models.Model):
    LANGUAGE_CHOICES = [
        ('english', 'English'),
        ('hindi',   'Hindi'),
    ]
    DIFFICULTY_CHOICES = [
        ('easy',   'Easy'),
        ('medium', 'Medium'),
        ('hard',   'Hard'),
    ]

    title      = models.CharField(max_length=200)
    content    = models.TextField()
    language   = models.CharField(max_length=10, choices=LANGUAGE_CHOICES)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    is_free    = models.BooleanField(default=False)
    order      = models.IntegerField(default=0)

    class Meta:
        ordering = ['language', 'order']

    def __str__(self):
        lock = '🔓 FREE' if self.is_free else '🔒 PAID'
        return f"[{self.language.upper()}] {self.title} — {lock}"