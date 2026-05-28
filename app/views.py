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
    SubscriptionPlan,
    SiteSettings,
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
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


# ═══════════════════════════════════════════════════
#  HELPER — Plans DB se laao
# ═══════════════════════════════════════════════════
def get_plans_dict():
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order')
    return {
        p.plan_key: {
            'label':      p.plan_name,
            'days':       p.duration_days,
            'price':      p.price,
            'desc':       p.description,
            'is_popular': p.is_popular,
        }
        for p in plans
    }


# ═══════════════════════════════════════════════════
#  HELPER — UPI QR Code banao
# ═══════════════════════════════════════════════════
def make_qr_base64(upi_id, name, amount, note):
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
#  REGISTER  ← BUG FIX: `name` → `username`
# ═══════════════════════════════════════════════════
def register(request):
    if get_logged_user(request):
        return redirect('index')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        # ── Validation ──
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

        # ── User DB mein save karo ──
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=True
        )

        # ── Profile create karo ──
        UserProfile.objects.create(user=user, is_paid=False)

        # ── Email verification token ──
        token = str(uuid.uuid4())
        EmailVerification.objects.create(user=user, token=token, is_verified=False)

        # ── Verify link banao ──
        verify_link = f"{settings.SITE_URL}/verify-email/{token}/"

        # Console mein bhi print karo (debug ke liye)
        print("\n" + "=" * 60)
        print(f"EMAIL VERIFICATION LINK for {email}:")
        print(verify_link)
        print("=" * 60 + "\n")

        # ── Email bhejo ──  ← BUG FIX: `name` → `username`
        try:
            send_mail(
                subject="Welcome to Smart Typing Test!",
                message=(
                    f"Hi {username},\n\n"
                    "Congratulations! Your account has been successfully created.\n\n"
                    "Please verify your email by clicking the link below:\n"
                    f"{verify_link}\n\n"
                    "After verification, you can log in here:\n"
                    f"{settings.SITE_URL}/login/\n\n"
                    "Best of luck!\n"
                    "Team Smart Typing Test"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(
                request,
                "Account created! Please check your email to verify your account."
            )
        except Exception as e:
            print(f"Email send error: {e}")
            messages.warning(
                request,
                f"Account created, but verification email could not be sent. "
                f"Error: {e}"
            )

        return redirect('login')

    return render(request, 'register.html')


# ═══════════════════════════════════════════════════
#  EMAIL VERIFY
# ═══════════════════════════════════════════════════
def verify_email(request, token):
    try:
        ev = EmailVerification.objects.get(token=token)
    except EmailVerification.DoesNotExist:
        messages.error(request, "Invalid verification link!")
        return redirect('login')

    if ev.is_verified:
        messages.success(request, "Email already verified!")
        return redirect('login')

    ev.is_verified = True
    ev.save()

    messages.success(request, "Email verified! Please login now.")
    return redirect('login')


# ═══════════════════════════════════════════════════
#  LOGIN
# ═══════════════════════════════════════════════════
def login(request):
    if get_logged_user(request):
        return redirect('index')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        user = User.objects.filter(email=email).first()

        if not user:
            messages.error(request, "This email is not registered!")
            return redirect('login')

        if not user.check_password(password):
            messages.error(request, "Incorrect password!")
            return redirect('login')

        request.session['user_id'] = user.id
        request.session.set_expiry(86400)

        messages.success(request, f"Welcome back, {user.username}!")
        return redirect('index')

    return render(request, 'login.html')


# ═══════════════════════════════════════════════════
#  LOGOUT
# ═══════════════════════════════════════════════════
def logout_view(request):
    request.session.flush()
    messages.success(request, "Logged out successfully!")
    return redirect('login')


# ═══════════════════════════════════════════════════
#  INDEX
# ═══════════════════════════════════════════════════
def index(request):
    if request.user.is_authenticated:
        user = request.user
        request.session['user_id'] = user.id
    else:
        user = get_logged_user(request)

    if not user:
        return redirect('login')

    profile, _ = UserProfile.objects.get_or_create(user=user)

    return render(request, 'index.html', {
        'user':    user,
        'profile': profile,
        'is_paid': profile.is_active(),
    })


# ═══════════════════════════════════════════════════
#  DASHBOARD
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

    active_plans = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order')

    return render(request, 'dashboard.html', {
        'user':             user,
        'profile':          profile,
        'is_paid':          is_active,
        'days_left':        profile.days_left(),
        'visible_passages': visible_passages,
        'locked_passages':  locked_passages,
        'selected_lang':    selected_lang,
        'active_plans':     active_plans,
    })


# ═══════════════════════════════════════════════════
#  PAYMENT
# ═══════════════════════════════════════════════════
def payment(request):
    user = get_logged_user(request)
    if not user:
        return redirect('login')

    profile, _ = UserProfile.objects.get_or_create(user=user)

    if profile.is_active():
        messages.success(
            request,
            f"Your {profile.plan} plan is already active! "
            f"{profile.days_left()} days remaining."
        )
        return redirect('dashboard')

    PLANS         = get_plans_dict()
    site_settings = SiteSettings.get_settings()

    if request.method == 'GET':
        return render(request, 'payment.html', {
            'user':  user,
            'plans': PLANS,
            'step':  'select',
        })

    plan_key = request.POST.get('plan', '').strip()

    if plan_key not in PLANS:
        messages.error(request, "Invalid plan! Please try again.")
        return redirect('payment')

    plan_info     = PLANS[plan_key]
    base_price    = plan_info['price']
    unique_paise  = random.randint(10, 99)
    unique_amount = float(f"{base_price}.{unique_paise}")

    PaymentRequest.objects.filter(
        user=user,
        status='pending',
        expires_at__lt=timezone.now()
    ).update(status='expired')

    pay_req = PaymentRequest.objects.create(
        user          = user,
        plan          = plan_key,
        base_amount   = base_price,
        unique_paise  = unique_paise,
        unique_amount = unique_amount,
        expires_at    = timezone.now() + timezone.timedelta(minutes=1),
    )

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
        'upi_id':        site_settings.upi_id,
    })


# ═══════════════════════════════════════════════════
#  PAYMENT CONFIRM
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
        messages.error(request, "Payment request not found or expired!")
        return redirect('payment')

    if pay_req.is_expired():
        pay_req.status = 'expired'
        pay_req.save()
        messages.error(request, "QR code expired! Please try again.")
        return redirect('payment')

    pay_req.transaction_ref = txn_ref
    pay_req.save()

    messages.success(
        request,
        f"Payment submitted! Admin will verify and activate within 24 hours. "
        f"Request ID: #{pay_req.id}"
    )
    return redirect('dashboard')


# ═══════════════════════════════════════════════════
#  PAYMENT APPROVE — Admin only
# ═══════════════════════════════════════════════════
def payment_approve(request, pay_req_id):
    user = get_logged_user(request)

    if not user or not user.is_staff:
        messages.error(request, "Access denied!")
        return redirect('login')

    try:
        pay_req = PaymentRequest.objects.get(id=pay_req_id)
    except PaymentRequest.DoesNotExist:
        messages.error(request, "Payment request not found!")
        return redirect('/admin/')

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

    messages.success(
        request,
        f"{pay_req.user.username}'s {pay_req.plan} plan activated! "
        f"Expiry: {profile.expiry_date.strftime('%d %b %Y')}"
    )
    return redirect('/admin/app/paymentrequest/')


# ═══════════════════════════════════════════════════
#  FORGOT PASSWORD
# ═══════════════════════════════════════════════════
def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        user  = User.objects.filter(email=email).first()

        if not user:
            messages.error(request, "This email is not registered!")
            return redirect('forgot_password')

        PasswordReset.objects.filter(user=user).delete()

        token = str(uuid.uuid4())
        PasswordReset.objects.create(user=user, token=token)

        reset_link = f"{settings.SITE_URL}/reset-password/{token}/"

        print(f"\n{'='*60}\nPASSWORD RESET LINK for {email}:\n{reset_link}\n{'='*60}\n")

        try:
            send_mail(
                subject="Smart Typing Test — Password Reset",
                message=(
                    f"Hi {user.username},\n\n"
                    f"Click the link below to reset your password:\n\n"
                    f"{reset_link}\n\n"
                    "This link is valid for 24 hours.\n\n"
                    "If you did not request this, ignore this email.\n\n"
                    "Team Smart Typing Test"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(request, "Reset link sent to your email!")
        except Exception as e:
            print(f"Email error: {e}")
            messages.error(request, f"Email could not be sent. Error: {e}")

        return redirect('login')

    return render(request, 'forgot_password.html')


# ═══════════════════════════════════════════════════
#  RESET PASSWORD
# ═══════════════════════════════════════════════════
def reset_password(request, token):
    reset_obj = PasswordReset.objects.filter(token=token).first()

    if not reset_obj:
        messages.error(request, "Invalid or expired link!")
        return redirect('login')

    if reset_obj.is_expired():
        reset_obj.delete()
        messages.error(request, "Link expired! Please try forgot password again.")
        return redirect('forgot_password')

    if request.method == 'POST':
        new_pw  = request.POST.get('password', '')
        conf_pw = request.POST.get('confirm_password', '')

        if len(new_pw) < 6:
            messages.error(request, "Password must be at least 6 characters!")
            return render(request, 'reset_password.html', {'token': token})

        if new_pw != conf_pw:
            messages.error(request, "Passwords do not match!")
            return render(request, 'reset_password.html', {'token': token})

        user = reset_obj.user
        user.set_password(new_pw)
        user.save()
        reset_obj.delete()

        messages.success(request, "Password updated successfully! Please login.")
        return redirect('login')

    return render(request, 'reset_password.html', {'token': token})