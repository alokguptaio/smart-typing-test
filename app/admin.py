from django.contrib import admin
from .models import (
    EmailVerification,
    PasswordReset,
    SubscriptionPlan,
    SiteSettings,
    UserProfile,
    PaymentRequest,
    Passage,
)


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display  = ('user', 'is_verified', 'created_at')
    list_filter   = ('is_verified',)
    search_fields = ('user__email', 'user__username')


@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display  = ('user', 'created_at')
    search_fields = ('user__email',)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display  = ('plan_name', 'plan_key', 'price', 'duration_days', 'is_active', 'is_popular', 'display_order')
    list_editable = ('price', 'is_active', 'is_popular', 'display_order')
    list_filter   = ('is_active', 'is_popular')


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('upi_id', 'upi_name', 'site_domain')

    def has_add_permission(self, request):
        # Sirf ek row allow karo
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'is_paid', 'plan', 'paid_date', 'expiry_date')
    list_filter   = ('is_paid', 'plan')
    search_fields = ('user__username', 'user__email')


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display  = ('user', 'plan', 'unique_amount', 'transaction_ref', 'status', 'created_at')
    list_filter   = ('status', 'plan')
    search_fields = ('user__username', 'transaction_ref')
    list_editable = ('status',)

    def approve_payment(self, request, queryset):
        from django.utils import timezone
        from .models import SubscriptionPlan
        for pay_req in queryset.filter(status='pending'):
            try:
                plan_obj = SubscriptionPlan.objects.get(plan_key=pay_req.plan)
                days     = plan_obj.duration_days
            except SubscriptionPlan.DoesNotExist:
                days = 30
            profile, _ = UserProfile.objects.get_or_create(user=pay_req.user)
            profile.is_paid     = True
            profile.plan        = pay_req.plan
            profile.paid_date   = timezone.now()
            profile.expiry_date = timezone.now() + timezone.timedelta(days=days)
            profile.save()
            pay_req.status = 'approved'
            pay_req.save()
        self.message_user(request, "Selected payments approved!")

    approve_payment.short_description = "✅ Approve selected payments"
    actions = ['approve_payment']


@admin.register(Passage)
class PassageAdmin(admin.ModelAdmin):
    list_display  = ('title', 'language', 'difficulty', 'is_free', 'order')
    list_filter   = ('language', 'difficulty', 'is_free')
    list_editable = ('is_free', 'order', 'difficulty')
    search_fields = ('title',)