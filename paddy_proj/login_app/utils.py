import random
from django.core.mail import send_mail
from django.conf import settings


def generate_otp():
    """Generate a secure 6-digit OTP"""
    return str(random.randint(100000, 999999))


def send_otp_email(email, otp, user_name=""):
    """Send OTP email for password reset"""
    subject = "Password Reset OTP - MandyAg"

    greeting = f"Hello {user_name}," if user_name else "Hello,"

    message = f"""
{greeting}

You requested a password reset for your MandyAg account.

Your OTP is: {otp}

This OTP is valid for 10 minutes. Do not share it with anyone.

If you did not request this, please ignore this email.

- The MandyAg Team
"""

    html_message = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f7f6; margin: 0; padding: 0; }}
    .wrapper {{ max-width: 520px; margin: 40px auto; background: #fff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(17,153,142,0.10); }}
    .header {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); padding: 36px 40px 28px; text-align: center; }}
    .header h1 {{ color: #fff; margin: 0; font-size: 26px; letter-spacing: 1px; }}
    .header p {{ color: rgba(255,255,255,0.85); margin: 6px 0 0; font-size: 14px; }}
    .body {{ padding: 36px 40px; }}
    .body p {{ color: #444; font-size: 15px; line-height: 1.7; }}
    .otp-box {{ background: linear-gradient(135deg, #f0fffe 0%, #e8fdf5 100%); border: 2px dashed #11998e; border-radius: 12px; text-align: center; padding: 24px 20px; margin: 28px 0; }}
    .otp-box .label {{ font-size: 13px; color: #888; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 10px; }}
    .otp-box .otp {{ font-size: 42px; font-weight: 800; color: #11998e; letter-spacing: 10px; }}
    .otp-box .expiry {{ font-size: 13px; color: #e74c3c; margin-top: 10px; }}
    .warning {{ background: #fff8e1; border-left: 4px solid #f6c90e; border-radius: 6px; padding: 12px 16px; margin-top: 20px; font-size: 13px; color: #7a6200; }}
    .footer {{ background: #f9f9f9; border-top: 1px solid #eee; padding: 20px 40px; text-align: center; font-size: 12px; color: #aaa; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>🌾 MandyAg</h1>
      <p>Password Reset Request</p>
    </div>
    <div class="body">
      <p>{greeting}</p>
      <p>We received a request to reset the password for your account. Use the OTP below to proceed.</p>
      <div class="otp-box">
        <div class="label">Your One-Time Password</div>
        <div class="otp">{otp}</div>
        <div class="expiry">⏱ Expires in 10 minutes</div>
      </div>
      <div class="warning">
        🔒 Never share this OTP with anyone. MandyAg will never ask for your OTP.
      </div>
      <p style="margin-top:24px;">If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>
    </div>
    <div class="footer">
      &copy; 2025 MandyAg. All rights reserved.<br/>This is an automated message, please do not reply.
    </div>
  </div>
</body>
</html>
"""

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        html_message=html_message,
        fail_silently=False,
    )