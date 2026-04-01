from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.utils.timezone import now
from datetime import timedelta
from paddy_app.models import AdminTable, CustomerTable, Subscription, PasswordResetOTP
from .utils import generate_otp, send_otp_email


def login_view(request):
    if request.session.get("user_id") and request.session.get("role"):
        role = request.session["role"]
        if role == "superadmin":
            return redirect("superadmin_app:superadmin_dashboard")
        elif role == "admin":
            return redirect("admin_app:admin_dashboard")
        elif role == "customer":
            return redirect("customer_app:customer_dashboard")

    if request.method == "POST":
        phone_number = request.POST.get("username")
        password = request.POST.get("password")

        if not phone_number or not password:
            messages.error(request, "All fields are required.")
            return redirect("login_app:login")

        try:
            admin_user = AdminTable.objects.get(phone_number=phone_number)
            if check_password(password, admin_user.password):
                if admin_user.admin_id <= 1000000:
                    request.session["user_id"] = admin_user.admin_id
                    request.session["role"] = "superadmin"
                    return redirect("superadmin_app:superadmin_dashboard")
                else:
                    request.session["user_id"] = admin_user.admin_id
                    request.session["role"] = "admin"
                    active_product_sub = Subscription.objects.filter(
                        admin_id=admin_user,
                        subscription_type__in=['admin_rice', 'admin_paddy', 'admin_pesticide'],
                        end_date__gte=now().date(),
                        subscription_status=1
                    ).first()
                    if active_product_sub:
                        return redirect("admin_app:admin_dashboard")
                    else:
                        return redirect("payment_app:admin_product_subscription")
        except AdminTable.DoesNotExist:
            pass

        try:
            customer_user = CustomerTable.objects.get(phone_number=phone_number)
            if check_password(password, customer_user.password):
                request.session["user_id"] = customer_user.customer_id
                request.session["role"] = "customer"
                sub = Subscription.objects.filter(
                    customer_id=customer_user, subscription_type="customer"
                ).order_by("-end_date").first()
                if sub:
                    if sub.end_date and sub.end_date >= now().date():
                        return redirect("customer_app:customer_dashboard")
                    else:
                        return redirect("payment_app:customer_subscription_payment")
                else:
                    Subscription.objects.create(
                        customer_id=customer_user,
                        subscription_type="customer",
                        subscription_status=1,
                        payment_amount=0,
                        start_date=now().date(),
                        end_date=now().date() + timedelta(days=30)
                    )
                    return redirect("customer_app:customer_dashboard")
        except CustomerTable.DoesNotExist:
            pass

        messages.error(request, "Invalid phone number or password.")

    return render(request, "login_app/login.html")


def logout_view(request):
    request.session.flush()
    messages.success(request, "Logged out successfully.")
    return redirect("login_app:login")


def admin_login_submit(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            admin = AdminTable.objects.get(email=email)
            if admin.check_password(password):
                request.session['user_id'] = admin.admin_id
                return redirect('superadmin_app:customers_under_admin')
        except AdminTable.DoesNotExist:
            pass
    return render(request, 'login_app/login.html', {'error': 'Invalid credentials'})


# ─────────────────────────────────────────────
#  FORGOT PASSWORD — STEP 1: Enter Email
# ─────────────────────────────────────────────
def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if not email:
            messages.error(request, "Please enter your email address.")
            return render(request, "login_app/forgot_password.html")

        # Look up user in both tables
        user_name = ""
        user_found = False

        try:
            admin = AdminTable.objects.get(email=email)
            user_name = admin.first_name
            user_found = True
        except AdminTable.DoesNotExist:
            pass

        if not user_found:
            try:
                customer = CustomerTable.objects.get(email=email)
                user_name = customer.first_name
                user_found = True
            except CustomerTable.DoesNotExist:
                pass

        if not user_found:
            # Don't reveal whether email exists — show same message
            messages.success(
                request,
                "If this email is registered, you'll receive an OTP shortly."
            )
            return render(request, "login_app/forgot_password.html")

        # Invalidate any previous unused OTPs for this email
        PasswordResetOTP.objects.filter(email=email, is_used=False).update(is_used=True)

        # Generate and save new OTP
        otp = generate_otp()
        PasswordResetOTP.objects.create(email=email, otp=otp)

        # Send OTP email
        try:
            send_otp_email(email, otp, user_name)
        except Exception as e:
            messages.error(request, "Failed to send OTP. Please try again later.")
            return render(request, "login_app/forgot_password.html")

        # Store email in session to pass between steps
        request.session["reset_email"] = email
        request.session["otp_verified"] = False

        messages.success(request, f"OTP sent to {email}. Please check your inbox.")
        return redirect("login_app:verify_otp")

    return render(request, "login_app/forgot_password.html")


# ─────────────────────────────────────────────
#  FORGOT PASSWORD — STEP 2: Verify OTP
# ─────────────────────────────────────────────
def verify_otp_view(request):
    email = request.session.get("reset_email")

    if not email:
        messages.error(request, "Session expired. Please start again.")
        return redirect("login_app:forgot_password")

    if request.method == "POST":
        action = request.POST.get("action")

        # ── Resend OTP ──
        if action == "resend":
            PasswordResetOTP.objects.filter(email=email, is_used=False).update(is_used=True)
            otp = generate_otp()
            PasswordResetOTP.objects.create(email=email, otp=otp)
            try:
                send_otp_email(email, otp)
                messages.success(request, "A new OTP has been sent to your email.")
            except Exception:
                messages.error(request, "Failed to resend OTP. Please try again.")
            return redirect("login_app:verify_otp")

        # ── Verify OTP ──
        entered_otp = request.POST.get("otp", "").strip()

        if not entered_otp:
            messages.error(request, "Please enter the OTP.")
            return render(request, "login_app/verify_otp.html", {"email": email})

        try:
            otp_record = PasswordResetOTP.objects.filter(
                email=email,
                otp=entered_otp,
                is_used=False
            ).latest("created_at")
        except PasswordResetOTP.DoesNotExist:
            messages.error(request, "Invalid OTP. Please check and try again.")
            return render(request, "login_app/verify_otp.html", {"email": email})

        if not otp_record.is_valid():
            messages.error(request, "This OTP has expired. Please request a new one.")
            return render(request, "login_app/verify_otp.html", {"email": email})

        # Mark OTP as used and flag session as verified
        otp_record.is_used = True
        otp_record.save()
        request.session["otp_verified"] = True

        messages.success(request, "OTP verified! Please set your new password.")
        return redirect("login_app:reset_password")

    return render(request, "login_app/verify_otp.html", {"email": email})


# ─────────────────────────────────────────────
#  FORGOT PASSWORD — STEP 3: Reset Password
# ─────────────────────────────────────────────
def reset_password_view(request):
    email = request.session.get("reset_email")
    otp_verified = request.session.get("otp_verified", False)

    # Guard: must have verified OTP to reach this page
    if not email or not otp_verified:
        messages.error(request, "Unauthorized access. Please complete OTP verification.")
        return redirect("login_app:forgot_password")

    if request.method == "POST":
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not password or not confirm_password:
            messages.error(request, "Both fields are required.")
            return render(request, "login_app/reset_password.html")

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return render(request, "login_app/reset_password.html")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "login_app/reset_password.html")

        hashed = make_password(password)
        updated = False

        # Update password in AdminTable
        try:
            admin = AdminTable.objects.get(email=email)
            admin.password = hashed
            admin.save(update_fields=["password"])
            updated = True
        except AdminTable.DoesNotExist:
            pass

        # Update password in CustomerTable
        if not updated:
            try:
                customer = CustomerTable.objects.get(email=email)
                customer.password = hashed
                customer.save(update_fields=["password"])
                updated = True
            except CustomerTable.DoesNotExist:
                pass

        if not updated:
            messages.error(request, "Account not found. Please try again.")
            return redirect("login_app:forgot_password")

        # Clean up session keys used for reset flow
        del request.session["reset_email"]
        del request.session["otp_verified"]

        messages.success(request, "Password reset successfully! Please log in with your new password.")
        return redirect("login_app:login")

    return render(request, "login_app/reset_password.html")