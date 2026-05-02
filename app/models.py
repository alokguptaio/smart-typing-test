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
#  SUBSCRIPTION PLAN  ← NAYA MODEL
#  Admin panel se price, duration, sab control hoga
#  Price change = sirf Admin panel mein jaao
# ═══════════════════════════════════════════════════
class SubscriptionPlan(models.Model):
    PLAN_KEY_CHOICES = [
        ('week',   '1 Week'),
        ('month',  '1 Month'),
        ('3month', '3 Months'),
        ('6month', '6 Months'),
    ]

    plan_key      = models.CharField(
                        max_length=20,
                        choices=PLAN_KEY_CHOICES,
                        unique=True,
                        help_text="Plan ka unique ID — change mat karna"
                    )
    plan_name     = models.CharField(
                        max_length=100,
                        help_text="Display name, e.g. '1 Week Plan'"
                    )
    price         = models.PositiveIntegerField(
                        help_text="Plan ki price sirf rupees mein (e.g. 9, 19, 49, 99)"
                    )
    duration_days = models.PositiveIntegerField(
                        help_text="Kitne din ka access milega (e.g. 7, 30, 90, 180)"
                    )
    description   = models.CharField(
                        max_length=200,
                        blank=True,
                        help_text="Short description, e.g. '7 din ka access'"
                    )
    is_active     = models.BooleanField(
                        default=True,
                        help_text="False karo to yeh plan payment page pe nahi dikhega"
                    )
    is_popular    = models.BooleanField(
                        default=False,
                        help_text="True karo to POPULAR badge dikhega"
                    )
    display_order = models.PositiveIntegerField(
                        default=0,
                        help_text="Kaun sa plan pehle dikhega — chota number = pehle"
                    )
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering      = ['display_order', 'price']
        verbose_name  = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'

    def __str__(self):
        status = '✅' if self.is_active else '❌'
        return f"{status} {self.plan_name} — ₹{self.price} / {self.duration_days} days"


# ═══════════════════════════════════════════════════
#  SITE SETTINGS  ← NAYA MODEL
#  Admin se UPI ID, UPI Name, Domain control hoga
#  Sirf ek row hogi is table mein (singleton)
# ═══════════════════════════════════════════════════
class SiteSettings(models.Model):
    upi_id      = models.CharField(
                      max_length=100,
                      help_text="Apna UPI ID (e.g. yourname@paytm)"
                  )
    upi_name    = models.CharField(
                      max_length=100,
                      default="Smart Typing Test",
                      help_text="Payment mein dikhne wala naam"
                  )
    site_domain = models.CharField(
                      max_length=200,
                      default="http://127.0.0.1:8000",
                      help_text="Production mein apna domain (e.g. https://yoursite.com)"
                  )

    class Meta:
        verbose_name        = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return f"Site Settings — UPI: {self.upi_id}"

    @classmethod
    def get_settings(cls):
        """
        Hamesha pehla (ya default) settings object return karta hai.
        Ek baar bhi row nahi hai to auto-create karta hai.
        """
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'upi_id':      'yourname@paytm',
                'upi_name':    'Smart Typing Test',
                'site_domain': 'http://127.0.0.1:8000',
            }
        )
        return obj


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

    # NOTE: PLAN_CHOICES aur PLAN_PRICES ab SubscriptionPlan model mein hain
    # Yahan sirf status choices hain
    STATUS_CHOICES = [
        ('pending',  'Pending — Verify Karo'),
        ('approved', 'Approved ✅'),
        ('expired',  'Expired ⏰'),
        ('rejected', 'Rejected ❌'),
    ]

    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_requests')
    plan            = models.CharField(max_length=20)   # plan_key store hoti hai e.g. 'week'
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