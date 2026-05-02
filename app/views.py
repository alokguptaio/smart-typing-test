import uuid
import random
import qrcode
import io
import base64
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils import timezone
from .models import (
    EmailVerification,
    PasswordReset,
    UserProfile,
    PaymentRequest,
    Passage,
    SubscriptionPlan,   # ← Naya
    SiteSettings,       # ← Naya
)
from django.conf import settings


# ═══════════════════════════════════════════════════
#  GOOGLE LOGIN REDIRECT
# ═══════════════════════════════════════════════════
def google_redirect(request):
    if request.user.is_authenticated:
        request.session['user_id'] = request.user.id
    return redirect('/index/')


# ═══════════════════════════════════════════════════
#  HELPER — Session se current user laao
# ═══════════════════════════════════════════════════
def get_logged_user(request):
    """Session se current user laata hai."""
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


# ═══════════════════════════════════════════════════
#  HELPER — Plans DB se laao (HARDCODING HATAO)
#  Pehle PLANS = {...} hardcoded tha views.py mein
#  Ab DB se aata hai — Admin se directly control
# ═══════════════════════════════════════════════════
def get_plans_dict():
    """
    SubscriptionPlan table se active plans laata hai.
    Views mein sirf yeh function call karo — kabhi hardcode mat karo.
    """
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order')
    return {
        p.plan_key: {
            'label':       p.plan_name,
            'days':        p.duration_days,
            'price':       p.price,
            'desc':        p.description,
            'is_popular':  p.is_popular,
        }
        for p in plans
    }


# ═══════════════════════════════════════════════════
#  HELPER — UPI QR Code banao
# ═══════════════════════════════════════════════════
def make_qr_base64(upi_id, name, amount, note):
    """
    UPI QR Code banata hai.
    Jab user scan karega to amount auto-fill ho jaayega.
    """
    upi_url = (
        f"upi://pay?pa={upi_id}"
        f"&pn={name}"
        f"&am={amount}"
        f"&cu=INR"
        f"&tn={note}"
    )
    qr = qrcode.QRCode(version=1, box_size=8, border=3)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img    = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')


# ═══════════════════════════════════════════════════
#  REGISTER
#  URL      : /register/
#  Template : register.html
# ═══════════════════════════════════════════════════
def register(request):
    if get_logged_user(request):
        return redirect('index')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        if not username or not email or not password:
            messages.error(request, "All fields are required!")
            return redirect('register')

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long!")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered!")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "This username is already taken!")
            return redirect('register')

        # User create
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=True
        )

        # Profile create
        UserProfile.objects.create(user=user, is_paid=False)

        # Token generate
        token = str(uuid.uuid4())
        EmailVerification.objects.create(user=user, token=token, is_verified=False)

        # Domain DB se lo
        site_settings = SiteSettings.get_settings()
        verify_link = f"{site_settings.site_domain}/verify-email/{token}/"

        print("\n" + "="*60)
        print(f"EMAIL VERIFICATION LINK for {email}:")
        print(verify_link)
        print("="*60 + "\n")

        try:
            send_mail(
                subject="🎉 Welcome to Smart Typing Test!",
                message=(
                    f"Hi {username},\n\n"
                    "🎉 Congratulations! Your account has been successfully created.\n\n"
                    "👉 Please verify your email by clicking the link below:\n"
                    f"{verify_link}\n\n"
                    "🚀 After verification, you can log in here:\n"
                    f"{site_settings.site_domain}/login/\n\n"
                    "Best of luck 💯\n"
                    "Team Smart Typing Test"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
        except Exception as e:
            print(f"Email send error: {e}")
            messages.warning(request, "Account created, but email could not be sent!")

        messages.success(request, "🎉 Account created successfully! Please verify your email.")
        return redirect('login')

    return render(request, 'register.html')


# ═══════════════════════════════════════════════════
#  EMAIL VERIFY
#  URL : /verify-email/<token>/
# ═══════════════════════════════════════════════════
def verify_email(request, token):
    try:
        ev = EmailVerification.objects.get(token=token)
    except EmailVerification.DoesNotExist:
        messages.error(request, "❌ Invalid verification link!")
        return redirect('login')

    if ev.is_verified:
        messages.success(request, "✅ Email already verified !")
        return redirect('login')

    ev.is_verified = True
    ev.save()

    messages.success(request, "✅ Email verified! Ab login karein.")
    return redirect('login')


# ═══════════════════════════════════════════════════
#  LOGIN
#  URL      : /login/
#  Template : login.html
# ═══════════════════════════════════════════════════
def login(request):
    if get_logged_user(request):
        return redirect('index')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        user = User.objects.filter(email=email).first()

        if not user:
            messages.error(request, "Yeh email registered nahi hai!")
            return redirect('login')

        if not user.check_password(password):
            messages.error(request, "Password galat hai!")
            return redirect('login')

        request.session['user_id'] = user.id
        request.session.set_expiry(86400)  # 24 ghante

        messages.success(request, f"Welcome back, {user.username}! 🎉")
        return redirect('index')

    return render(request, 'login.html')


# ═══════════════════════════════════════════════════
#  LOGOUT
#  URL : /logout/
# ═══════════════════════════════════════════════════
def logout_view(request):
    request.session.flush()
    messages.success(request, "Successfully logout ho gaye!")
    return redirect('login')


# ═══════════════════════════════════════════════════
#  INDEX — Landing Page (Typing Test)
#  URL      : /index/
#  Template : index.html
# ═══════════════════════════════════════════════════
def index(request):
    # Google login support
    if request.user.is_authenticated:
        user = request.user
        request.session['user_id'] = user.id
    else:
        user = get_logged_user(request)

    if not user:
        return redirect('login')

    profile, _ = UserProfile.objects.get_or_create(user=user)

    return render(request, 'index.html', {
        'user':     user,
        'profile':  profile,
        'is_paid':  profile.is_active(),
    })


# ═══════════════════════════════════════════════════
#  DASHBOARD — Passage Select Page
#  URL      : /dashboard/
#  Template : dashboard.html
#  Kaam:
#    1. Login check
#    2. Plan expiry check
#    3. Free passages → sab ko
#    4. Locked passages → sirf paid ko
#    5. active_plans context → DB se (banner ke liye)
# ═══════════════════════════════════════════════════
def dashboard(request):
    user = get_logged_user(request)
    if not user:
        return redirect('login')

    profile, _ = UserProfile.objects.get_or_create(user=user)
    is_active  = profile.is_active()

    selected_lang = request.GET.get('lang', 'english')
    all_passages  = Passage.objects.filter(language=selected_lang).order_by('order')

    if is_active:
        visible_passages = all_passages
        locked_passages  = Passage.objects.none()
    else:
        visible_passages = all_passages.filter(is_free=True)
        locked_passages  = all_passages.filter(is_free=False)

    # ✅ Plans DB se lo — dashboard upgrade banner ke liye
    active_plans = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order')

    return render(request, 'dashboard.html', {
        'user':             user,
        'profile':          profile,
        'is_paid':          is_active,
        'days_left':        profile.days_left(),
        'visible_passages': visible_passages,
        'locked_passages':  locked_passages,
        'selected_lang':    selected_lang,
        'active_plans':     active_plans,   # ✅ Naya — template mein use hoga
    })


# ═══════════════════════════════════════════════════
#  PAYMENT — Plan Select + QR Generate
#  URL      : /payment/
#  Template : payment.html
#
#  GET  → Plan selection (Step 1)
#  POST → QR generate (Step 2)
# ═══════════════════════════════════════════════════
def payment(request):
    user = get_logged_user(request)
    if not user:
        return redirect('login')

    profile, _ = UserProfile.objects.get_or_create(user=user)

    # Already active plan?
    if profile.is_active():
        messages.success(
            request,
            f"✅ Aapka {profile.plan} plan already active hai! {profile.days_left()} din baaki hain."
        )
        return redirect('dashboard')

    # ✅ DB se plans lo (hardcoded PLANS dict nahi)
    PLANS = get_plans_dict()

    # ✅ DB se site settings lo (UPI ID, name)
    site_settings = SiteSettings.get_settings()

    # ── GET → Plan selection ──
    if request.method == 'GET':
        return render(request, 'payment.html', {
            'user':  user,
            'plans': PLANS,
            'step':  'select',
        })

    # ── POST → QR generate ──
    plan_key = request.POST.get('plan', '').strip()

    if plan_key not in PLANS:
        messages.error(request, "Galat plan! Dobara try karein.")
        return redirect('payment')

    plan_info  = PLANS[plan_key]
    base_price = plan_info['price']   # ✅ DB se aaya price

    # Unique paise generate (10-99)
    unique_paise  = random.randint(10, 99)
    unique_amount = float(f"{base_price}.{unique_paise}")

    # Purane expired requests mark karo
    PaymentRequest.objects.filter(
        user=user,
        status='pending',
        expires_at__lt=timezone.now()
    ).update(status='expired')

    # Naya PaymentRequest banao
    pay_req = PaymentRequest.objects.create(
        user          = user,
        plan          = plan_key,
        base_amount   = base_price,
        unique_paise  = unique_paise,
        unique_amount = unique_amount,
        expires_at    = timezone.now() + timezone.timedelta(minutes=1),
    )

    # ✅ QR mein DB se UPI ID use karo
    note   = f"SmartTyping-{pay_req.id}-{plan_key}"
    qr_b64 = make_qr_base64(
        site_settings.upi_id,
        site_settings.upi_name,
        unique_amount,
        note
    )

    return render(request, 'payment.html', {
        'user':          user,
        'plans':         PLANS,
        'step':          'qr',
        'plan_key':      plan_key,
        'plan_info':     plan_info,
        'pay_req':       pay_req,
        'qr_b64':        qr_b64,
        'unique_amount': unique_amount,
        'seconds_left':  pay_req.seconds_left(),
        'upi_id':        site_settings.upi_id,   # ✅ DB se
    })


# ═══════════════════════════════════════════════════
#  PAYMENT CONFIRM — User UTR Submit Karta Hai
#  URL : /payment-confirm/
# ═══════════════════════════════════════════════════
def payment_confirm(request):
    user = get_logged_user(request)
    if not user:
        return redirect('login')

    if request.method != 'POST':
        return redirect('payment')

    pay_req_id = request.POST.get('pay_req_id', '').strip()
    txn_ref    = request.POST.get('transaction_ref', '').strip()

    try:
        pay_req = PaymentRequest.objects.get(id=pay_req_id, user=user, status='pending')
    except PaymentRequest.DoesNotExist:
        messages.error(request, "❌ Payment request nahi mili ya expire ho gayi!")
        return redirect('payment')

    if pay_req.is_expired():
        pay_req.status = 'expired'
        pay_req.save()
        messages.error(request, "⏰ QR expire ho gaya! Dobara try karein.")
        return redirect('payment')

    pay_req.transaction_ref = txn_ref
    pay_req.save()

    messages.success(
        request,
        f"✅ Payment submit ho gayi! Admin verify karega. 24 ghante mein activate hoga. ID: #{pay_req.id}"
    )
    return redirect('dashboard')


# ═══════════════════════════════════════════════════
#  PAYMENT APPROVE — Sirf Admin Use Kare
#  URL : /payment-approve/<id>/
# ═══════════════════════════════════════════════════
def payment_approve(request, pay_req_id):
    user = get_logged_user(request)

    if not user or not user.is_staff:
        messages.error(request, "Access denied!")
        return redirect('login')

    try:
        pay_req = PaymentRequest.objects.get(id=pay_req_id)
    except PaymentRequest.DoesNotExist:
        messages.error(request, "Payment request nahi mili!")
        return redirect('/admin/')

    # ✅ Plan duration DB se lo (hardcoded nahi)
    try:
        plan_obj = SubscriptionPlan.objects.get(plan_key=pay_req.plan)
        days = plan_obj.duration_days
    except SubscriptionPlan.DoesNotExist:
        days = 30  # Fallback — agar plan DB mein nahi mila

    profile, _ = UserProfile.objects.get_or_create(user=pay_req.user)
    profile.is_paid     = True
    profile.plan        = pay_req.plan
    profile.paid_date   = timezone.now()
    profile.expiry_date = timezone.now() + timezone.timedelta(days=days)
    profile.save()

    pay_req.status = 'approved'
    pay_req.save()

    messages.success(
        request,
        f"✅ {pay_req.user.username} ka {pay_req.plan} plan activate! "
        f"Expiry: {profile.expiry_date.strftime('%d %b %Y')}"
    )
    return redirect('/admin/app/paymentrequest/')


# ═══════════════════════════════════════════════════
#  FORGOT PASSWORD
#  URL      : /forgot-password/
#  Template : forgot_password.html
# ═══════════════════════════════════════════════════
def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        user  = User.objects.filter(email=email).first()

        if not user:
            messages.error(request, "Yeh email registered nahi hai!")
            return redirect('forgot_password')

        PasswordReset.objects.filter(user=user).delete()

        token = str(uuid.uuid4())
        PasswordReset.objects.create(user=user, token=token)

        domain     = request.build_absolute_uri('/')[:-1]
        reset_link = f"{domain}/reset-password/{token}/"

        print(f"\n{'='*60}\nPASSWORD RESET LINK for {email}:\n{reset_link}\n{'='*60}\n")

        try:
            send_mail(
                subject="Smart Typing Test — Password Reset",
                message=(
                    f"Password reset karne ke liye yeh link click karein:\n\n"
                    f"{reset_link}\n\n"
                    "Yeh link 24 ghante valid hai."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
            messages.success(request, "✅ Reset link aapke email par bheja gaya!")
        except Exception as e:
            print(f"Email error: {e}")
            messages.error(request, f"❌ Email nahi gaya: {e}")

        return redirect('login')

    return render(request, 'forgot_password.html')


# ═══════════════════════════════════════════════════
#  RESET PASSWORD
#  URL      : /reset-password/<token>/
#  Template : reset_password.html
# ═══════════════════════════════════════════════════
def reset_password(request, token):
    reset_obj = PasswordReset.objects.filter(token=token).first()

    if not reset_obj:
        messages.error(request, "❌ Link invalid ya expire ho gaya hai!")
        return redirect('login')

    if reset_obj.is_expired():
        reset_obj.delete()
        messages.error(request, "⏰ Link expire ho gaya! Dobara forgot password try karein.")
        return redirect('forgot_password')

    if request.method == 'POST':
        new_pw  = request.POST.get('password', '')
        conf_pw = request.POST.get('confirm_password', '')

        if len(new_pw) < 6:
            messages.error(request, "Password kam se kam 6 characters!")
            return render(request, 'reset_password.html', {'token': token})

        if new_pw != conf_pw:
            messages.error(request, "Dono passwords match nahi kar rahe!")
            return render(request, 'reset_password.html', {'token': token})

        user = reset_obj.user
        user.set_password(new_pw)
        user.save()
        reset_obj.delete()

        messages.success(request, "✅ Password update ho gaya! Ab login karein.")
        return redirect('login')

    return render(request, 'reset_password.html', {'token': token})