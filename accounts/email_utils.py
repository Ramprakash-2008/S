from django.core.mail import EmailMessage
from django.conf import settings
import os
from django.core.mail import send_mail
from django.conf import settings
import base64
import requests
def send_brevo_email(
    recipient_email,
    subject,
    html_content,
    text_content=None,
    attachment_path=None,
    attachment_name=None
):
    url = "https://api.brevo.com/v3/smtp/email"

    headers = {
        "accept": "application/json",
        "api-key": os.environ.get("BREVO_API_KEY"),
        "content-type": "application/json",
    }

    data = {
        "sender": {
            "name": os.environ.get("BREVO_SENDER_NAME", "SecureCrypt"),
            "email": os.environ.get("BREVO_SENDER_EMAIL"),
        },
        "to": [
            {
                "email": recipient_email
            }
        ],
        "subject": subject,
        "htmlContent": html_content,
    }

    if text_content:
        data["textContent"] = text_content

    if attachment_path:
        with open(attachment_path, "rb") as f:
            encoded_file = base64.b64encode(f.read()).decode("utf-8")

        data["attachment"] = [
            {
                "content": encoded_file,
                "name": attachment_name or os.path.basename(attachment_path),
            }
        ]

    response = requests.post(
        url,
        headers=headers,
        json=data,
        timeout=20
    )
    if not response.ok:
        print("BREVO STATUS:", response.status_code)
        print("BREVO RESPONSE:", response.text)


    response.raise_for_status()

    return response.json()
def send_encrypted_file(
    recipient_email,
    file_path,
    filename
):
    """
    Send an encrypted file as an email attachment.

    Parameters:
        recipient_email: Email address of the recipient
        file_path: Full path to the encrypted file
        filename: Filename shown in the email attachment
    """

    # Validate recipient
    if not recipient_email:
        raise ValueError(
            "Recipient email address is required."
        )

    # Validate file
    if not file_path:
        raise ValueError(
            "Encrypted file path is required."
        )

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Encrypted file not found: {file_path}"
        )
    subject = "Your SecureCrypt Encrypted File"

    html_content = """
    <h2>SecureCrypt</h2>
    <p>Your encrypted file is attached to this email.</p>
    """

    text_content = (
        "Your SecureCrypt encrypted file is attached."
    )
    # Create email
    send_brevo_email(
    recipient_email=recipient_email,
    subject=subject,
    html_content=html_content,
    text_content=text_content,
    attachment_path=file_path,
    attachment_name=filename,
    )
    return True
def send_notification_email(
    recipient_email,
    subject,
    message
):
    """
    Send a normal SecureCrypt notification email.
    """

    if not recipient_email:
        raise ValueError(
            "Recipient email address is required."
        )

    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient_email]
    )

    email.send(
        fail_silently=False
    )

    return True
def send_account_locked_email(user, hours, reason="Administrator action"):
    if not user.email:
        return False

    email = EmailMessage(
        subject="SecureCrypt - Account Locked",

        body=(
            f"Hello {user.username},\n\n"
            "Your SecureCrypt account has been temporarily locked.\n\n"
            f"Reason:\n{reason}\n\n"
            f"Lock duration:\n{hours} hour(s)\n\n"
            "Your account will be available again after "
            "the lock period expires.\n\n"
            "If you did not expect this action, please contact "
            "the administrator.\n\n"
            "Regards,\n"
            "SecureCrypt Security Team"
        ),

        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )

    email.send(fail_silently=False)

    return True
def send_account_unlocked_email(user, reason="Administrator action"):
    if not user.email:
        return False

    email = EmailMessage(
        subject="SecureCrypt - Account Unlocked",

        body=(
            f"Hello {user.username},\n\n"
            "Your SecureCrypt account has been unlocked.\n\n"
            f"Reason:\n{reason}\n\n"
            "You can now log in and use your SecureCrypt account normally.\n\n"
            "If you did not expect this action, please contact "
            "the administrator immediately.\n\n"
            "Regards,\n"
            "SecureCrypt Security Team"
        ),

        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )

    email.send(fail_silently=False)

    return True
def send_registration_success_email(user):
    if not user.email:
        return False

    email = EmailMessage(
        subject="SecureCrypt - Registration Successful",

        body=(
            f"Hello {user.username},\n\n"
            "Your SecureCrypt account has been successfully registered.\n\n"
            "Your account is currently waiting for administrator approval.\n\n"
            "You will be able to log in and use SecureCrypt "
            "once your account has been approved.\n\n"
            "Please do not share your password with anyone.\n\n"
            "Regards,\n"
            "SecureCrypt Security Team"
        ),

        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )

    email.send(fail_silently=False)

    return True
def send_new_registration_admin_email(user):
    admin_email = settings.DEFAULT_FROM_EMAIL

    if not admin_email:
        return False

    email = EmailMessage(
        subject="SecureCrypt - New User Registration",

        body=(
            "Hello Administrator,\n\n"
            "A new user has registered on SecureCrypt "
            "and is waiting for approval.\n\n"

            f"Username: {user.username}\n"
            f"Email: {user.email}\n"
            f"Phone: {user.phone}\n\n"

            "Please log in to the SecureCrypt Admin Dashboard "
            "to review and approve or reject this registration.\n\n"

            "Regards,\n"
            "SecureCrypt Security System"
        ),

        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[admin_email]
    )

    email.send(fail_silently=False)

    return True
def send_user_approved_email(user):

    email = EmailMessage(
        subject="SecureCrypt - Account Approved",

        body=(
            f"Hello {user.username},\n\n"
            "Good news! Your SecureCrypt account has been "
            "approved by the administrator.\n\n"

            "You can now log in to SecureCrypt and use "
            "the available features.\n\n"

            "Please keep your account credentials secure.\n\n"

            "Regards,\n"
            "SecureCrypt Security Team"
        ),

        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )

    email.send(
        fail_silently=False
    )

    return True
def send_user_rejected_email(user):

    email = EmailMessage(
        subject="SecureCrypt - Account Registration Update",

        body=(
            f"Hello {user.username},\n\n"
            "We are writing to inform you that your "
            "SecureCrypt account registration has been "
            "rejected by the administrator.\n\n"

            "You currently cannot log in to SecureCrypt "
            "using this account.\n\n"

            "If you believe this was a mistake, please "
            "contact the SecureCrypt administrator.\n\n"

            "Regards,\n"
            "SecureCrypt Security Team"
        ),

        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )

    email.send(
        fail_silently=False
    )

    return True
def send_user_deactivated_email(user):

    email = EmailMessage(
        subject="SecureCrypt - Account Deactivated",

        body=(
            f"Hello {user.username},\n\n"
            "Your SecureCrypt account has been deactivated "
            "by the administrator.\n\n"

            "You will not be able to access your account "
            "while it is deactivated.\n\n"

            "If you believe this action was taken by mistake, "
            "please contact the SecureCrypt administrator.\n\n"

            "Regards,\n"
            "SecureCrypt Security Team"
        ),

        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )

    email.send(
        fail_silently=False
    )

    return True
def send_user_deleted_email(user):

    email = EmailMessage(
        subject="SecureCrypt - Account Deleted",

        body=(
            f"Hello {user.username},\n\n"
            "Your SecureCrypt account has been deleted "
            "by the administrator.\n\n"

            "You will no longer be able to log in or access "
            "this SecureCrypt account.\n\n"

            "If you believe this action was taken by mistake, "
            "please contact the SecureCrypt administrator.\n\n"

            "Regards,\n"
            "SecureCrypt Security Team"
        ),

        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )

    email.send(
        fail_silently=False
    )

    return True
def send_suspicious_activity_email(owner, attempted_by, filename):

    email = EmailMessage(
        subject="⚠️ SecureCrypt - Suspicious Activity Detected",

        body=(
            f"Hello {owner.username},\n\n"

            "We detected a suspicious activity involving "
            "one of your encrypted files.\n\n"

            f"File: {filename}\n"
            f"Attempted by account: {attempted_by.username}\n\n"

            "Another account attempted to decrypt a file "
            "belonging to you. The decryption attempt was "
            "blocked by SecureCrypt.\n\n"

            "If you recognize this activity, no action is "
            "required. Otherwise, please review your account "
            "security.\n\n"

            "Regards,\n"
            "SecureCrypt Security Team"
        ),

        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[owner.email]
    )

    email.send(fail_silently=False)

    return True
def send_password_reset_email(
    user,
    reset_url
):

    subject = (
        "SecureCrypt Password Reset Request"
    )

    message = f"""
Hello {user.username},

We received a request to reset your
SecureCrypt account password.

Click the secure link below to create
a new password:

{reset_url}

If you did not request this password reset,
you can safely ignore this email.

For your security, do not share this link
with anyone.

SecureCrypt Security Team
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False
    )
def send_password_changed_email(
    user
):

    subject = (
        "Security Alert: Your SecureCrypt Password Was Changed"
    )

    message = f"""
Hello {user.username},

Your SecureCrypt account password was
successfully changed.

If you changed your password, no further
action is required.

If you DID NOT change your password,
your account may be compromised.

Please contact the SecureCrypt administrator
immediately so your account can be secured.

SecureCrypt Security Team
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False
    )
