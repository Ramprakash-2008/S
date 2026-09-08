import os
import base64
import requests

from django.conf import settings


BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def send_brevo_email(
    recipient_email,
    subject,
    html_content,
    text_content=None,
    attachment_path=None,
    attachment_name=None,
    disable_tracking=False,
):
    """
    Central Brevo email sender.

    All SecureCrypt emails should use this function.
    """

    if not recipient_email:
        raise ValueError("Recipient email address is required.")

    api_key = os.environ.get("BREVO_API_KEY")
    sender_email = os.environ.get("BREVO_SENDER_EMAIL")
    sender_name = os.environ.get(
        "BREVO_SENDER_NAME",
        "SecureCrypt"
    )

    if not api_key:
        raise ValueError("BREVO_API_KEY is not configured.")

    if not sender_email:
        raise ValueError("BREVO_SENDER_EMAIL is not configured.")

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }

    data = {
        "sender": {
            "name": sender_name,
            "email": sender_email,
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
    if disable_tracking:
        data["headers"] = {
        "X-Mailin-trackclicks": "0"
    }
    # ---------------------------------------------------------
    # OPTIONAL ATTACHMENT
    # ---------------------------------------------------------

    if attachment_path:

        if not os.path.exists(attachment_path):
            raise FileNotFoundError(
                f"Attachment not found: {attachment_path}"
            )

        with open(attachment_path, "rb") as file:

            encoded_file = base64.b64encode(
                file.read()
            ).decode("utf-8")

        data["attachment"] = [
            {
                "content": encoded_file,

                "name": (
                    attachment_name
                    or os.path.basename(attachment_path)
                ),
            }
        ]

    # ---------------------------------------------------------
    # SEND THROUGH BREVO
    # ---------------------------------------------------------

    response = requests.post(
        BREVO_URL,
        headers=headers,
        json=data,
        timeout=20
    )

    print("BREVO STATUS:", response.status_code)
    print("BREVO RESPONSE:", response.text)

    response.raise_for_status()

    return response.json()


# ============================================================
# ENCRYPTED FILE EMAIL
# ============================================================

def send_encrypted_file(
    recipient_email,
    file_path,
    filename
):

    if not recipient_email:
        raise ValueError(
            "Recipient email address is required."
        )

    if not file_path:
        raise ValueError(
            "Encrypted file path is required."
        )

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Encrypted file not found: {file_path}"
        )

    subject = "SecureCrypt - Encrypted File"

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt</h2>

        <p>Your encrypted file has been created successfully.</p>

        <p>
            <strong>File:</strong> {filename}
        </p>

        <p>
            The encrypted file is attached to this email.
        </p>

        <p>
            Keep your decryption password safe.
        </p>

        <br>

        <p>
            Regards,<br>
            SecureCrypt Security Team
        </p>

    </body>
    </html>
    """

    text_content = (
        f"Your SecureCrypt encrypted file '{filename}' "
        "is attached to this email."
    )

    send_brevo_email(
        recipient_email=recipient_email,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        attachment_path=file_path,
        attachment_name=filename,
    )

    return True


# ============================================================
# GENERIC NOTIFICATION EMAIL
# ============================================================

def send_notification_email(
    recipient_email,
    subject,
    message
):

    if not recipient_email:
        return False

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt</h2>

        <p>{message}</p>

        <br>

        <p>
            Regards,<br>
            SecureCrypt Security Team
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=recipient_email,
        subject=subject,
        html_content=html_content,
        text_content=message
    )

    return True


# ============================================================
# ACCOUNT LOCKED
# ============================================================

def send_account_locked_email(
    user,
    hours,
    reason="Administrator action"
):

    if not user.email:
        return False

    subject = "SecureCrypt - Account Locked"

    message = f"""
Hello {user.username},

Your SecureCrypt account has been temporarily locked.

Reason:
{reason}

Lock duration:
{hours} hour(s)

Your account will be available again after the lock period expires.

If you did not expect this action, please contact the administrator.

Regards,
SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt - Account Locked</h2>

        <p>Hello {user.username},</p>

        <p>
            Your SecureCrypt account has been temporarily locked.
        </p>

        <p>
            <strong>Reason:</strong><br>
            {reason}
        </p>

        <p>
            <strong>Lock duration:</strong><br>
            {hours} hour(s)
        </p>

        <p>
            Your account will be available again after
            the lock period expires.
        </p>

        <p>
            If you did not expect this action,
            please contact the administrator.
        </p>

        <br>

        <p>
            Regards,<br>
            SecureCrypt Security Team
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,
        subject=subject,
        html_content=html_content,
        text_content=message
    )

    return True


# ============================================================
# ACCOUNT UNLOCKED
# ============================================================

def send_account_unlocked_email(
    user,
    reason="Administrator action"
):

    if not user.email:
        return False

    subject = "SecureCrypt - Account Unlocked"

    message = f"""
Hello {user.username},

Your SecureCrypt account has been unlocked.

Reason:
{reason}

You can now log in and use your SecureCrypt account normally.

If you did not expect this action, please contact the administrator immediately.

Regards,
SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt - Account Unlocked</h2>

        <p>Hello {user.username},</p>

        <p>
            Your SecureCrypt account has been unlocked.
        </p>

        <p>
            <strong>Reason:</strong><br>
            {reason}
        </p>

        <p>
            You can now log in and use your
            SecureCrypt account normally.
        </p>

        <p>
            If you did not expect this action,
            please contact the administrator immediately.
        </p>

        <br>

        <p>
            Regards,<br>
            SecureCrypt Security Team
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,
        subject=subject,
        html_content=html_content,
        text_content=message
    )

    return True


# ============================================================
# REGISTRATION SUCCESS
# ============================================================

def send_registration_success_email(user):

    if not user.email:
        return False

    subject = "SecureCrypt - Registration Successful"

    message = f"""
Hello {user.username},

Your SecureCrypt account has been successfully registered.

Your account is currently waiting for administrator approval.

You will be able to log in and use SecureCrypt once your account has been approved.

Please do not share your password with anyone.

Regards,
SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt - Registration Successful</h2>

        <p>Hello {user.username},</p>

        <p>
            Your SecureCrypt account has been successfully registered.
        </p>

        <p>
            Your account is currently waiting for
            administrator approval.
        </p>

        <p>
            You will be able to log in and use SecureCrypt
            once your account has been approved.
        </p>

        <p>
            Please do not share your password with anyone.
        </p>

        <br>

        <p>
            Regards,<br>
            SecureCrypt Security Team
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,
        subject=subject,
        html_content=html_content,
        text_content=message
    )

    return True


# ============================================================
# NEW REGISTRATION → ADMIN
# ============================================================

def send_new_registration_admin_email(user):

    admin_email = settings.DEFAULT_FROM_EMAIL

    if not admin_email:
        return False

    subject = "SecureCrypt - New User Registration"

    message = f"""
Hello Administrator,

A new user has registered on SecureCrypt
and is waiting for approval.

Username: {user.username}
Email: {user.email}
Phone: {user.phone}

Please log in to the SecureCrypt Admin Dashboard
to review and approve or reject this registration.

Regards,
SecureCrypt Security System
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt - New User Registration</h2>

        <p>Hello Administrator,</p>

        <p>
            A new user has registered on SecureCrypt
            and is waiting for approval.
        </p>

        <p>
            <strong>Username:</strong> {user.username}<br>
            <strong>Email:</strong> {user.email}<br>
            <strong>Phone:</strong> {user.phone}
        </p>

        <p>
            Please log in to the SecureCrypt Admin Dashboard
            to review this registration.
        </p>

        <br>

        <p>
            Regards,<br>
            SecureCrypt Security System
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=admin_email,
        subject=subject,
        html_content=html_content,
        text_content=message
    )

    return True


# ============================================================
# USER APPROVED
# ============================================================

def send_user_approved_email(user):

    if not user.email:
        return False

    subject = "SecureCrypt - Account Approved"

    message = f"""
Hello {user.username},

Good news!

Your SecureCrypt account has been approved by the administrator.

You can now log in to SecureCrypt and use the available features.

Please keep your account credentials secure.

Regards,
SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt - Account Approved</h2>

        <p>Hello {user.username},</p>

        <p>
            Good news! Your SecureCrypt account has been
            approved by the administrator.
        </p>

        <p>
            You can now log in to SecureCrypt and use
            the available features.
        </p>

        <p>
            Please keep your account credentials secure.
        </p>

        <br>

        <p>
            Regards,<br>
            SecureCrypt Security Team
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,
        subject=subject,
        html_content=html_content,
        text_content=message
    )

    return True


# ============================================================
# USER REJECTED
# ============================================================

def send_user_rejected_email(user):

    if not user.email:
        return False

    subject = "SecureCrypt - Account Registration Update"

    message = f"""
Hello {user.username},

We are writing to inform you that your SecureCrypt account registration has been rejected by the administrator.

You currently cannot log in to SecureCrypt using this account.

If you believe this was a mistake, please contact the SecureCrypt administrator.

Regards,
SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt - Registration Update</h2>

        <p>Hello {user.username},</p>

        <p>
            Your SecureCrypt account registration has been
            rejected by the administrator.
        </p>

        <p>
            You currently cannot log in to SecureCrypt
            using this account.
        </p>

        <p>
            If you believe this was a mistake,
            please contact the SecureCrypt administrator.
        </p>

        <br>

        <p>
            Regards,<br>
            SecureCrypt Security Team
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,
        subject=subject,
        html_content=html_content,
        text_content=message
    )

    return True


# ============================================================
# USER DEACTIVATED
# ============================================================

def send_user_deactivated_email(user):

    if not user.email:
        return False

    subject = "SecureCrypt - Account Deactivated"

    message = f"""
Hello {user.username},

Your SecureCrypt account has been deactivated by the administrator.

You will not be able to access your account while it is deactivated.

If you believe this action was taken by mistake, please contact the SecureCrypt administrator.

Regards,
SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt - Account Deactivated</h2>

        <p>Hello {user.username},</p>

        <p>
            Your SecureCrypt account has been deactivated
            by the administrator.
        </p>

        <p>
            You will not be able to access your account
            while it is deactivated.
        </p>

        <p>
            If you believe this action was taken by mistake,
            please contact the SecureCrypt administrator.
        </p>

        <br>

        <p>
            Regards,<br>
            SecureCrypt Security Team
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,
        subject=subject,
        html_content=html_content,
        text_content=message
    )

    return True


# ============================================================
# USER DELETED
# ============================================================

def send_user_deleted_email(user):

    if not user.email:
        return False

    subject = "SecureCrypt - Account Deleted"

    message = f"""
Hello {user.username},

Your SecureCrypt account has been deleted by the administrator.

You will no longer be able to log in or access this SecureCrypt account.

If you believe this action was taken by mistake, please contact the SecureCrypt administrator.

Regards,
SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt - Account Deleted</h2>

        <p>Hello {user.username},</p>

        <p>
            Your SecureCrypt account has been deleted
            by the administrator.
        </p>

        <p>
            You will no longer be able to log in or access
            this SecureCrypt account.
        </p>

        <p>
            If you believe this action was taken by mistake,
            please contact the SecureCrypt administrator.
        </p>

        <br>

        <p>
            Regards,<br>
            SecureCrypt Security Team
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,
        subject=subject,
        html_content=html_content,
        text_content=message
    )

    return True


# ============================================================
# SUSPICIOUS ACTIVITY
# ============================================================

def send_suspicious_activity_email(
    owner,
    attempted_by,
    filename
):

    if not owner.email:
        return False

    subject = "SecureCrypt - Suspicious Activity Detected"

    message = f"""
Hello {owner.username},

We detected suspicious activity involving one of your encrypted files.

File:
{filename}

Attempted by account:
{attempted_by.username}

Another account attempted to decrypt a file belonging to you.

The decryption attempt was blocked by SecureCrypt.

If you recognize this activity, no action is required.
Otherwise, please review your account security.

Regards,
SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>⚠ SecureCrypt - Suspicious Activity</h2>

        <p>Hello {owner.username},</p>

        <p>
            We detected suspicious activity involving
            one of your encrypted files.
        </p>

        <p>
            <strong>File:</strong><br>
            {filename}
        </p>

        <p>
            <strong>Attempted by account:</strong><br>
            {attempted_by.username}
        </p>

        <p>
            Another account attempted to decrypt a file
            belonging to you.
        </p>

        <p>
            The decryption attempt was blocked by SecureCrypt.
        </p>

        <p>
            If you recognize this activity, no action is required.
            Otherwise, please review your account security.
        </p>

        <br>

        <p>
            Regards,<br>
            SecureCrypt Security Team
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=owner.email,
        subject=subject,
        html_content=html_content,
        text_content=message
    )

    return True


# ============================================================
# PASSWORD RESET
# ============================================================

def send_password_reset_email(user, reset_url):

    if not user.email:
        return False

    subject = "SecureCrypt - Password Reset Request"

    html_content = f"""
    <html>
    <body>
        <h2>SecureCrypt Password Reset</h2>

        <p>Hello {user.username},</p>

        <p>
            We received a request to reset your
            SecureCrypt account password.
        </p>

        <p>
            Click the button below to create a new password:
        </p>

        <p>
            <a href="{reset_url}">
                Reset My Password
            </a>
        </p>

        <p>
            If you did not request this password reset,
            you can safely ignore this email.
        </p>

        <p>
            For your security, do not share this link with anyone.
        </p>

        <p>
            SecureCrypt Security Team
        </p>
    </body>
    </html>
    """

    text_content = f"""
Hello {user.username},

We received a request to reset your SecureCrypt account password.

Reset your password using this link:

{reset_url}

If you did not request this password reset, you can safely ignore this email.

SecureCrypt Security Team
"""

    return send_brevo_email(
        recipient_email=user.email,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        disable_tracking=True,
    )
# ============================================================
# PASSWORD CHANGED
# ============================================================

def send_password_changed_email(user):

    if not user.email:
        return False

    subject = (
        "SecureCrypt - Password Changed"
    )

    message = f"""
Hello {user.username},

Your SecureCrypt account password was successfully changed.

If you changed your password, no further action is required.

If you DID NOT change your password,
your account may be compromised.

Please contact the SecureCrypt administrator immediately
so your account can be secured.

SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt Security Alert</h2>

        <p>Hello {user.username},</p>

        <p>
            Your SecureCrypt account password was
            successfully changed.
        </p>

        <p>
            If you changed your password,
            no further action is required.
        </p>

        <p>
            <strong>
                If you DID NOT change your password,
                your account may be compromised.
            </strong>
        </p>

        <p>
            Please contact the SecureCrypt administrator
            immediately so your account can be secured.
        </p>

        <br>

        <p>
            SecureCrypt Security Team
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,
        subject=subject,
        html_content=html_content,
        text_content=message
    )

    return True
