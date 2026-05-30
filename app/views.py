import uuid
import random
import qrcode
import io
import base64
import razorpay
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
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


def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def google_redirect(request):
    if request.user.is_authenticated:
        request.session['user_id'] = request.user.id
    return redirect('/index/')


def get_logged_user(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


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


def make_qr_base64(upi_id, name, amount, note):
    upi_url = (
        f"upi://pay?pa={upi_id}&pn={name}&am={amount}&cu=INR&tn={note}"
    )
    qr = qrcode.QRCode(version=1, box_size=8, border=3)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img    = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')


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

        db_username = username
        counter = 1
        while User.objects.filter(username=db_username).exists():
            db_username = f"{username}_{counter}"
            counter += 1

        user = User.objects.create_user(
            username   = db_username,
            first_name = username,
            email      = email,
            password   = password,
            is_active  = True
        )

        UserProfile.objects.create(user=user, is_paid=False)

        token = str(uuid.uuid4())
        EmailVerification.objects.create(user=user, token=token, is_verified=False)
        verify_link = f"{settings.SITE_URL}/verify-email/{token}/"

        print("\n" + "=" * 60)
        print(f"EMAIL VERIFICATION LINK for {email}:")
        print(verify_link)
        print("=" * 60 + "\n")

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
            messages.success(request, "Account created! Please check your email to verify your account.")
        except Exception as e:
            print(f"Email send error: {e}")
            messages.warning(request, f"Account created, but verification email could not be sent. Error: {e}")

        return redirect('login')

    return render(request, 'register.html')


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

        display_name = user.first_name or user.username
        messages.success(request, f"Welcome back, {display_name}!")
        return redirect('index')

    return render(request, 'login.html')


def logout_view(request):
    request.session.flush()
    messages.success(request, "Logged out successfully!")
    return redirect('login')


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
        'user':         user,
        'profile':      profile,
        'is_paid':      profile.is_active(),
        'display_name': user.first_name or user.username,
    })


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
        'display_name':     user.first_name or user.username,
    })


def payment(request):
    user = get_logged_user(request)
    if not user:
        return redirect('login')

    profile, _ = UserProfile.objects.get_or_create(user=user)

    if profile.is_active():
        messages.success(
            request,
            f"Your {profile.plan} plan is already active! {profile.days_left()} days remaining."
        )
        return redirect('dashboard')

    PLANS = get_plans_dict()

    if request.method == 'GET':
        return render(request, 'payment.html', {
            'user':            user,
            'plans':           PLANS,
            'step':            'select',
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        })

    plan_key = request.POST.get('plan', '').strip()

    if plan_key not in PLANS:
        messages.error(request, "Invalid plan! Please try again.")
        return redirect('payment')

    plan_info    = PLANS[plan_key]
    amount_inr   = plan_info['price']
    amount_paise = amount_inr * 100

    client = get_razorpay_client()
    razorpay_order = client.order.create({
        'amount':          amount_paise,
        'currency':        'INR',
        'payment_capture': 1,
        'notes': {
            'plan_key':   plan_key,
            'user_id':    str(user.id),
            'user_email': user.email,
        }
    })

    pay_req = PaymentRequest.objects.create(
        user            = user,
        plan            = plan_key,
        base_amount     = amount_inr,
        unique_paise    = 0,
        unique_amount   = amount_inr,
        transaction_ref = razorpay_order['id'],
        expires_at      = timezone.now() + timezone.timedelta(hours=1),
    )

    return render(request, 'payment.html', {
        'user':              user,
        'plans':             PLANS,
        'step':              'razorpay',
        'plan_key':          plan_key,
        'plan_info':         plan_info,
        'pay_req':           pay_req,
        'amount_paise':      amount_paise,
        'amount_inr':        amount_inr,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_key_id':   settings.RAZORPAY_KEY_ID,
        'user_email':        user.email,
        'user_name':         user.first_name or user.username,
    })


def razorpay_verify(request):
    if request.method != 'POST':
        return redirect('payment')

    user = get_logged_user(request)
    if not user:
        return redirect('login')

    razorpay_payment_id = request.POST.get('razorpay_payment_id', '')
    razorpay_order_id   = request.POST.get('razorpay_order_id', '')
    razorpay_signature  = request.POST.get('razorpay_signature', '')
    pay_req_id          = request.POST.get('pay_req_id', '')

    client = get_razorpay_client()
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id':   razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature':  razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        messages.error(request, "Payment verification failed! Please contact support.")
        return redirect('payment')

    try:
        pay_req = PaymentRequest.objects.get(id=pay_req_id, user=user)
    except PaymentRequest.DoesNotExist:
        messages.error(request, "Payment request not found!")
        return redirect('payment')

    try:
        plan_obj = SubscriptionPlan.objects.get(plan_key=pay_req.plan)
        days     = plan_obj.duration_days
    except SubscriptionPlan.DoesNotExist:
        days = 30

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.is_paid     = True
    profile.plan        = pay_req.plan
    profile.paid_date   = timezone.now()
    profile.expiry_date = timezone.now() + timezone.timedelta(days=days)
    profile.save()

    pay_req.status          = 'approved'
    pay_req.transaction_ref = razorpay_payment_id
    pay_req.save()

    display_name = user.first_name or user.username
    try:
        send_mail(
            subject="Smart Typing Test — Payment Successful! 🎉",
            message=(
                f"Hi {display_name},\n\n"
                f"Your payment was successful!\n\n"
                f"Plan: {plan_obj.plan_name}\n"
                f"Amount: ₹{pay_req.unique_amount}\n"
                f"Expiry: {profile.expiry_date.strftime('%d %b %Y')}\n\n"
                f"All passages are now unlocked. Happy typing!\n\n"
                f"Team Smart Typing Test"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception:
        pass

    messages.success(
        request,
        f"🎉 Payment successful! {plan_obj.plan_name} activated. Expiry: {profile.expiry_date.strftime('%d %b %Y')}"
    )
    return redirect('dashboard')


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

    display_name = pay_req.user.first_name or pay_req.user.username
    messages.success(
        request,
        f"{display_name}'s {pay_req.plan} plan activated! Expiry: {profile.expiry_date.strftime('%d %b %Y')}"
    )
    return redirect('/admin/app/paymentrequest/')


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

        display_name = user.first_name or user.username

        try:
            send_mail(
                subject="Smart Typing Test — Password Reset",
                message=(
                    f"Hi {display_name},\n\n"
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
            messages.error(request, f"Email could not be sent. Error: {e}")

        return redirect('login')

    return render(request, 'forgot_password.html')


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