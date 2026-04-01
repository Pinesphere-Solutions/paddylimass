from django.urls import path
from .views import *

app_name = 'login_app'

urlpatterns = [
    path("", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("admin-login-submit/", admin_login_submit, name="admin_login_submit"),

    # Forgot password flow
    path("forgot-password/", forgot_password_view, name="forgot_password"),
    path("verify-otp/", verify_otp_view, name="verify_otp"),
    path("reset-password/", reset_password_view, name="reset_password"),
]