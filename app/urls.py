from django.urls import path, include
from . import views

urlpatterns = [

    # ── ROOT → Login ──
    path('', views.login, name='home'),

    # ── AUTH ──
    path('login/',                     views.login,           name='login'),
    path('register/',                  views.register,         name='register'),
    path('logout/',                    views.logout_view,      name='logout'),
    path('verify-email/<str:token>/',  views.verify_email,     name='verify_email'),
    path('forgot-password/',           views.forgot_password,  name='forgot_password'),
    path('reset-password/<str:token>/', views.reset_password,  name='reset_password'),

    # ── MAIN PAGES ──
    path('index/',     views.index,     name='index'),      # Landing + Typing Test
    path('dashboard/', views.dashboard, name='dashboard'),  # Passage select

    # ── PAYMENT ──
    path('payment/',                          views.payment,         name='payment'),
    path('payment-confirm/',                  views.payment_confirm, name='payment_confirm'),
    path('payment-approve/<int:pay_req_id>/', views.payment_approve, name='payment_approve'),

    # ── GOOGLE LOGIN ──
    path('accounts/', include('allauth.urls')),
]