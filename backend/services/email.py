"""
Email service using SMTP.
Works with Gmail, SendGrid, Mailgun, AWS SES, etc.

For Gmail:
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=your_email@gmail.com
    SMTP_PASS=your_app_password  (NOT your real password!)
    
To generate Gmail App Password:
    Google Account → Security → 2-Step Verification → App Passwords
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import os
import logging

logger = logging.getLogger(__name__)

# Load SMTP config from environment
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_NAME = os.getenv("FROM_NAME", "TradeMaster")
APP_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


# ==========================================
# 1. CORE EMAIL SENDER
# ==========================================

def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """
    Send an HTML email using SMTP.
    Returns True if successful, False otherwise.
    """
    if not SMTP_USER or not SMTP_PASS:
        logger.warning("⚠️ Email not configured - skipping send (set SMTP_USER, SMTP_PASS in .env)")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((FROM_NAME, SMTP_USER))
        msg["To"] = to_email

        # Attach HTML body
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

        logger.info(f"✅ Email sent to {to_email} - Subject: {subject}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("❌ SMTP authentication failed. Check SMTP_USER / SMTP_PASS.")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to send email to {to_email}: {e}")
        return False


# ==========================================
# 2. EMAIL TEMPLATES
# ==========================================

def _base_template(title: str, body: str) -> str:
    """Common HTML wrapper for all emails."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; background: #0f172a; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 32px; color: #f8fafc; }}
            .header {{ color: #3b82f6; font-size: 28px; font-weight: bold; margin-bottom: 24px; text-align: center; }}
            .content {{ font-size: 15px; line-height: 1.6; color: #cbd5e1; }}
            .btn {{ display: inline-block; padding: 12px 28px; background: #3b82f6; color: #ffffff !important; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 16px; }}
            .amount {{ font-size: 32px; color: #10b981; font-weight: bold; text-align: center; margin: 20px 0; }}
            .footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid #334155; font-size: 12px; color: #64748b; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">{FROM_NAME}</div>
            <div class="content">
                <h2 style="color:#f8fafc;">{title}</h2>
                {body}
            </div>
            <div class="footer">
                © {__import__('datetime').datetime.now().year} {FROM_NAME}. All rights reserved.<br>
                If you did not request this email, please ignore it.
            </div>
        </div>
    </body>
    </html>
    """


# ==========================================
# 3. PUBLIC EMAIL FUNCTIONS
# ==========================================

def send_welcome_email(email: str, name: str) -> bool:
    """Send welcome email when user signs up."""
    body = f"""
        <p>Hi <b>{name}</b>,</p>
        <p>Welcome to {FROM_NAME}! 🎉</p>
        <p>Your account has been created successfully. You can now access:</p>
        <ul>
            <li>✅ AI-powered trading signals</li>
            <li>✅ Auto-copy trading with Binance</li>
            <li>✅ 24/7 live support</li>
        </ul>
        <p style="text-align: center;">
            <a href="{APP_URL}/dashboard" class="btn">Go to Dashboard</a>
        </p>
    """
    html = _base_template("Welcome Aboard!", body)
    return send_email(email, f"Welcome to {FROM_NAME}!", html)


def send_payment_receipt(email: str, name: str, amount: float, plan_name: str) -> bool:
    """Send payment confirmation with receipt details."""
    body = f"""
        <p>Hi <b>{name}</b>,</p>
        <p>Thank you for your payment! Your subscription is now active.</p>
        <div class="amount">${amount:.2f}</div>
        <table style="width:100%; margin: 20px 0;">
            <tr><td style="color:#94a3b8;">Plan:</td><td><b>{plan_name}</b></td></tr>
            <tr><td style="color:#94a3b8;">Amount:</td><td>${amount:.2f}</td></tr>
            <tr><td style="color:#94a3b8;">Status:</td><td style="color:#10b981;"><b>PAID</b></td></tr>
        </table>
        <p style="text-align: center;">
            <a href="{APP_URL}/subscription" class="btn">View Subscription</a>
        </p>
    """
    html = _base_template("Payment Confirmed ✅", body)
    return send_email(email, f"Payment Receipt - ${amount:.2f}", html)


def send_wallet_deposit_receipt(email: str, name: str, amount: float, new_balance: float) -> bool:
    """Send wallet top-up confirmation."""
    body = f"""
        <p>Hi <b>{name}</b>,</p>
        <p>Your wallet has been topped up successfully.</p>
        <div class="amount">+${amount:.2f}</div>
        <p style="text-align: center; color: #94a3b8;">
            New Balance: <b style="color:#3b82f6;">${new_balance:.2f}</b>
        </p>
        <p style="text-align: center;">
            <a href="{APP_URL}/wallet" class="btn">View Wallet</a>
        </p>
    """
    html = _base_template("Deposit Successful 💰", body)
    return send_email(email, f"Wallet Deposit - ${amount:.2f}", html)


def send_renewal_reminder(email: str, name: str, plan_name: str, days_left: int) -> bool:
    """Send reminder 7 days before subscription expires."""
    body = f"""
        <p>Hi <b>{name}</b>,</p>
        <p>Your <b>{plan_name}</b> subscription will expire in <b style="color:#f59e0b;">{days_left} days</b>.</p>
        <p>Renew now to keep enjoying uninterrupted access to:</p>
        <ul>
            <li>Trading signals</li>
            <li>Auto-copy trading</li>
            <li>Live support</li>
        </ul>
        <p style="text-align: center;">
            <a href="{APP_URL}/subscription" class="btn">Renew Now</a>
        </p>
    """
    html = _base_template("Subscription Expiring Soon ⏰", body)
    return send_email(email, f"Your subscription expires in {days_left} days", html)


def send_password_reset(email: str, name: str, reset_token: str) -> bool:
    """Send password reset link (future feature)."""
    reset_url = f"{APP_URL}/reset-password?token={reset_token}"
    body = f"""
        <p>Hi <b>{name}</b>,</p>
        <p>We received a request to reset your password.</p>
        <p>Click the button below to reset it. This link expires in 1 hour.</p>
        <p style="text-align: center;">
            <a href="{reset_url}" class="btn">Reset Password</a>
        </p>
        <p style="color:#ef4444; font-size: 13px;">
            ⚠️ If you did not request this, please ignore this email. Your password will remain unchanged.
        </p>
    """
    html = _base_template("Reset Your Password", body)
    return send_email(email, "Password Reset Request", html)


def send_support_reply(email: str, name: str, original_message: str, admin_reply: str) -> bool:
    """Notify user of support ticket reply (optional)."""
    body = f"""
        <p>Hi <b>{name}</b>,</p>
        <p>You have a new reply from our support team:</p>
        <div style="background:#0f172a; padding:16px; border-radius:8px; border-left:3px solid #3b82f6; margin:16px 0;">
            <p style="color:#94a3b8; font-size:12px; margin:0 0 8px 0;">Your message:</p>
            <p style="margin:0; font-style:italic;">{original_message}</p>
        </div>
        <div style="background:#0f172a; padding:16px; border-radius:8px; border-left:3px solid #10b981; margin:16px 0;">
            <p style="color:#94a3b8; font-size:12px; margin:0 0 8px 0;">Support reply:</p>
            <p style="margin:0;"><b>{admin_reply}</b></p>
        </div>
        <p style="text-align: center;">
            <a href="{APP_URL}/support" class="btn">View in App</a>
        </p>
    """
    html = _base_template("New Support Reply", body)
    return send_email(email, "New Message from Support", html)


# ==========================================
# 4. TEST FUNCTION (for development)
# ==========================================

if __name__ == "__main__":
    """
    Test the email service directly.
    Run: python -m services.email your_email@example.com
    """
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python -m services.email your_email@example.com")
        sys.exit(1)

    test_email = sys.argv[1]
    print(f"Sending test email to {test_email}...")

    result = send_welcome_email(test_email, "Test User")
    if result:
        print("✅ Test email sent successfully!")
    else:
        print("❌ Failed to send. Check your SMTP config in .env")