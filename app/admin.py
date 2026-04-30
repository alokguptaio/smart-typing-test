from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import UserProfile, EmailVerification, PasswordReset, PaymentRequest, Passage


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'is_paid', 'plan', 'paid_date', 'expiry_date', 'days_left_col']
    list_filter   = ['is_paid', 'plan']
    search_fields = ['user__username', 'user__email']
    list_editable = ['is_paid']

    def days_left_col(self, obj):
        d = obj.days_left()
        if d > 7:   return format_html('<b style="color:green;">{} din</b>', d)
        elif d > 0: return format_html('<b style="color:orange;">{} din</b>', d)
        return format_html('<b style="color:red;">Expired/Free</b>')
    days_left_col.short_description = "Days Left"


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display  = ['user', 'is_verified', 'created_at']
    list_filter   = ['is_verified']
    search_fields = ['user__username', 'user__email']


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display    = ['user', 'plan', 'unique_amount', 'transaction_ref', 'status', 'created_at', 'approve_btn']
    list_filter     = ['status', 'plan']
    search_fields   = ['user__username', 'transaction_ref']
    readonly_fields = ['user', 'plan', 'base_amount', 'unique_amount', 'unique_paise', 'created_at', 'expires_at']
    ordering        = ['-created_at']

    def approve_btn(self, obj):
        if obj.status == 'pending':
            url = reverse('payment_approve', args=[obj.id])
            return format_html(
                '<a href="{}" style="background:linear-gradient(135deg,#00c9a7,#6d28d9);'
                'color:#fff;padding:5px 14px;border-radius:6px;font-weight:700;'
                'text-decoration:none;font-size:12px;">✅ APPROVE</a>', url
            )
        elif obj.status == 'approved':
            return format_html('<b style="color:green;">✅ Approved</b>')
        elif obj.status == 'expired':
            return format_html('<span style="color:gray;">⏰ Expired</span>')
        return format_html('<span style="color:red;">❌ Rejected</span>')
    approve_btn.short_description = "Action"


@admin.register(Passage)
class PassageAdmin(admin.ModelAdmin):
    list_display  = ['title', 'language', 'difficulty', 'is_free', 'order']
    list_filter   = ['language', 'difficulty', 'is_free']
    search_fields = ['title']
    list_editable = ['is_free', 'order', 'difficulty']
    ordering      = ['language', 'order']


@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']
    ordering     = ['-created_at']