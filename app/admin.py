from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    EmailVerification,
    PasswordReset,
    UserProfile,
    PaymentRequest,
    Passage,
    SubscriptionPlan,
    SiteSettings,
)


# ═══════════════════════════════════════════════════
#  SUBSCRIPTION PLAN ADMIN
#  Admin iska se price, duration, sab control karega
#  list_editable = list page pe SEEDHA price edit
# ═══════════════════════════════════════════════════
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):

    list_display        = [
        'plan_name',
        'plan_key',
        'price_display',
        'price',            # editable column
        'duration_days',    # editable column
        'is_active',        # editable column
        'is_popular',       # editable column
        'display_order',    # editable column
        'updated_at',
    ]
    list_editable       = ['price', 'duration_days', 'is_active', 'is_popular', 'display_order']
    list_display_links  = ['plan_name']
    ordering            = ['display_order']
    readonly_fields     = ['plan_key', 'created_at', 'updated_at']

    fieldsets = (
        ('📋 Plan Information', {
            'fields': ('plan_key', 'plan_name', 'description'),
        }),
        ('💰 Pricing & Duration', {
            'fields': ('price', 'duration_days'),
            'description': '⚠️ Price sirf rupees mein (integer). Duration days mein.',
        }),
        ('🎨 Display Settings', {
            'fields': ('is_active', 'is_popular', 'display_order'),
        }),
        ('🕐 Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def price_display(self, obj):
        color = '#16a34a' if obj.is_active else '#9ca3af'
        return format_html(
            '<strong style="color:{};font-size:15px;">₹{}</strong>',
            color,
            obj.price
        )
    price_display.short_description = '💰 Current Price'

    # Admin mein plan_key delete/add nahi hoga — sirf edit
    def has_add_permission(self, request):
        # 4 se zyada plans allowed nahi (week/month/3month/6month)
        return SubscriptionPlan.objects.count() < 4

    # Plan key change nahi karne deta
    def get_readonly_fields(self, request, obj=None):
        if obj:  # edit mode
            return ['plan_key', 'created_at', 'updated_at']
        return ['created_at', 'updated_at']


# ═══════════════════════════════════════════════════
#  SITE SETTINGS ADMIN
#  UPI ID, UPI Name, Domain — sab yahan se control
# ═══════════════════════════════════════════════════
@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):

    list_display = ['upi_id', 'upi_name', 'site_domain']

    fieldsets = (
        ('💳 UPI Payment Settings', {
            'fields': ('upi_id', 'upi_name'),
            'description': '⚠️ UPI ID change karne ke baad test zaroor karo.',
        }),
        ('🌐 Site Settings', {
            'fields': ('site_domain',),
            'description': 'Production mein https:// se shuru karo.',
        }),
    )

    def has_add_permission(self, request):
        # Sirf ek row allowed hai
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Delete mat karo — settings hamesha rahni chahiye
        return False


# ═══════════════════════════════════════════════════
#  PAYMENT REQUEST ADMIN
#  Admin yahan se payment approve karta hai
# ═══════════════════════════════════════════════════
@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):

    list_display   = [
        'id',
        'user',
        'plan',
        'amount_display',
        'transaction_ref',
        'status',
        'created_at',
        'approve_button',
    ]
    list_filter    = ['status', 'plan', 'created_at']
    search_fields  = ['user__username', 'user__email', 'transaction_ref']
    ordering       = ['-created_at']
    readonly_fields = [
        'user', 'plan', 'base_amount', 'unique_paise',
        'unique_amount', 'created_at', 'expires_at',
    ]

    fieldsets = (
        ('👤 User & Plan', {
            'fields': ('user', 'plan'),
        }),
        ('💰 Amount Details', {
            'fields': ('base_amount', 'unique_paise', 'unique_amount'),
        }),
        ('📄 Transaction', {
            'fields': ('transaction_ref', 'status'),
        }),
        ('🕐 Timestamps', {
            'fields': ('created_at', 'expires_at'),
        }),
    )

    def amount_display(self, obj):
        color = '#16a34a' if obj.status == 'approved' else '#0f1235'
        return format_html('<strong style="color:{};">₹{}</strong>', color, obj.unique_amount)
    amount_display.short_description = '₹ Amount'

    def approve_button(self, obj):
        if obj.status == 'pending':
            return format_html(
                '<a href="/payment-approve/{}/" '
                'style="background:#00c9a7;color:#fff;padding:5px 14px;'
                'border-radius:7px;text-decoration:none;font-weight:700;'
                'font-size:12px;">✅ Approve</a>',
                obj.id
            )
        elif obj.status == 'approved':
            return format_html('<span style="color:#16a34a;font-weight:700;">✅ Approved</span>')
        elif obj.status == 'expired':
            return format_html('<span style="color:#f59e0b;font-weight:700;">⏰ Expired</span>')
        else:
            return format_html('<span style="color:#dc2626;font-weight:700;">❌ Rejected</span>')
    approve_button.short_description = '🔧 Action'


# ═══════════════════════════════════════════════════
#  USER PROFILE ADMIN
# ═══════════════════════════════════════════════════
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display   = ['user', 'plan_display', 'is_paid', 'paid_date', 'expiry_date', 'days_left_display']
    list_filter    = ['is_paid', 'plan']
    search_fields  = ['user__username', 'user__email']
    readonly_fields = ['user']
    ordering       = ['-paid_date']

    def plan_display(self, obj):
        if obj.is_paid:
            return format_html(
                '<span style="background:#00c9a7;color:#fff;padding:3px 10px;'
                'border-radius:999px;font-weight:700;font-size:11px;">⭐ {}</span>',
                (obj.plan or 'N/A').upper()
            )
        return format_html('<span style="color:#9ca3af;">FREE</span>')
    plan_display.short_description = 'Plan'

    def days_left_display(self, obj):
        days = obj.days_left()
        if days > 7:
            color = '#16a34a'
        elif days > 0:
            color = '#d97706'
        else:
            color = '#dc2626'
        return format_html('<strong style="color:{};">{} din</strong>', color, days)
    days_left_display.short_description = 'Days Left'


# ═══════════════════════════════════════════════════
#  PASSAGE ADMIN 
# ═══════════════════════════════════════════════════
@admin.register(Passage)
class PassageAdmin(admin.ModelAdmin):

    list_display   = ['title', 'language', 'difficulty', 'is_free', 'order', 'word_count']
    list_editable  = ['is_free', 'order']
    list_filter    = ['language', 'difficulty', 'is_free']
    search_fields  = ['title', 'content']
    ordering       = ['language', 'order']

    fieldsets = (
        ('📄 Passage Info', {
            'fields': ('title', 'language', 'difficulty'),
        }),
        ('📝 Content', {
            'fields': ('content',),
        }),
        ('⚙️ Settings', {
            'fields': ('is_free', 'order'),
        }),
    )

    def word_count(self, obj):
        count = len(obj.content.split())
        return format_html('<span style="color:#4a4e8a;">{} words</span>', count)
    word_count.short_description = 'Words'


# ═══════════════════════════════════════════════════
#  EMAIL VERIFICATION ADMIN
# ═══════════════════════════════════════════════════
@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display  = ['user', 'is_verified', 'created_at']
    list_filter   = ['is_verified']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['user', 'token', 'created_at']


# ═══════════════════════════════════════════════════
#  PASSWORD RESET ADMIN
# ═══════════════════════════════════════════════════
@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display  = ['user', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['user', 'token', 'created_at']