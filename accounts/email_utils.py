import os
import base64
import html
import requests


# ============================================================
# BREVO CONFIGURATION
# ============================================================

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


# ============================================================
# COMMON BREVO EMAIL FUNCTION
# ============================================================

def send_brevo_email(
    recipient_email,
    subject,
    html_content,
    text_content=None,
    attachment_path=None,
    attachment_name=None
):
    """
    Central email-sending function.

    Every SecureCrypt email function uses this function.
    """

    # --------------------------------------------------------
    # VALIDATE RECIPIENT
    # --------------------------------------------------------

    if not recipient_email:
        raise ValueError(
            "Recipient email address is required."
        )

    # --------------------------------------------------------
    # GET BREVO ENVIRONMENT VARIABLES
    # --------------------------------------------------------

    api_key = os.environ.get(
        "BREVO_API_KEY"
    )

    sender_email = os.environ.get(
        "BREVO_SENDER_EMAIL"
    )

    sender_name = os.environ.get(
        "BREVO_SENDER_NAME",
        "SecureCrypt"
    )

    # --------------------------------------------------------
    # VALIDATE BREVO CONFIGURATION
    # --------------------------------------------------------

    if not api_key:
        raise ValueError(
            "BREVO_API_KEY is not configured."
        )

    if not sender_email:
        raise ValueError(
            "BREVO_SENDER_EMAIL is not configured."
        )

    # --------------------------------------------------------
    # HEADERS
    # --------------------------------------------------------

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }

    # --------------------------------------------------------
    # EMAIL DATA
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # TEXT CONTENT
    # --------------------------------------------------------

    if text_content:
        data["textContent"] = text_content

    # --------------------------------------------------------
    # ATTACHMENT
    # --------------------------------------------------------

    if attachment_path:

        if not os.path.exists(attachment_path):
            raise FileNotFoundError(
                f"Attachment not found: {attachment_path}"
            )

        with open(
            attachment_path,
            "rb"
        ) as file:

            encoded_file = base64.b64encode(
                file.read()
            ).decode("utf-8")

        data["attachment"] = [
            {
                "content": encoded_file,

                "name": (
                    attachment_name
                    or os.path.basename(
                        attachment_path
                    )
                ),
            }
        ]

    # --------------------------------------------------------
    # SEND TO BREVO
    # --------------------------------------------------------

    response = requests.post(
        BREVO_API_URL,
        headers=headers,
        json=data,
        timeout=20
    )

    # --------------------------------------------------------
    # LOG BREVO RESPONSE
    # --------------------------------------------------------

    print(
        "BREVO STATUS:",
        response.status_code
    )

    print(
        "BREVO RESPONSE:",
        response.text
    )

    # --------------------------------------------------------
    # RAISE ERROR IF BREVO REJECTS REQUEST
    # --------------------------------------------------------

    response.raise_for_status()

    # --------------------------------------------------------
    # RETURN BREVO RESPONSE
    # --------------------------------------------------------

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

    subject = (
        "Your SecureCrypt Encrypted File"
    )

    html_content = """
    <html>
    <body>

        <h2>SecureCrypt</h2>

        <p>
            Your encrypted file is attached
            to this email.
        </p>

        <p>
            Keep your decryption password safe.
            You will need it to decrypt the file.
        </p>

        <p>
            Regards,<br>
            <strong>SecureCrypt Security Team</strong>
        </p>

    </body>
    </html>
    """

    text_content = (
        "Your SecureCrypt encrypted file "
        "is attached to this email.\n\n"
        "Keep your decryption password safe."
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
# NORMAL NOTIFICATION EMAIL
# ============================================================

def send_notification_email(
    recipient_email,
    subject,
    message
):

    if not recipient_email:
        raise ValueError(
            "Recipient email address is required."
        )

    safe_message = html.escape(
        message
    )

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt</h2>

        <p>
            {safe_message}
        </p>

        <p>
            Regards,<br>
            <strong>SecureCrypt Security Team</strong>
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=recipient_email,

        subject=subject,

        html_content=html_content,

        text_content=message,
    )

    return True


# ============================================================
# PASSWORD RESET EMAIL
# ============================================================

def send_password_reset_email(
    user,
    reset_url
):

    if not user.email:
        return False

    username = html.escape(
        user.username
    )

    safe_reset_url = html.escape(
        reset_url,
        quote=True
    )

    subject = (
        "SecureCrypt Password Reset Request"
    )

    text_content = f"""
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

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt</h2>

        <p>
            Hello {username},
        </p>

        <p>
            We received a request to reset your
            SecureCrypt account password.
        </p>

        <p>
            Click the button below to create
            a new password:
        </p>

        <p>
            <a
                href="{safe_reset_url}"
                style="
                    display:inline-block;
                    padding:12px 20px;
                    background:#2563eb;
                    color:white;
                    text-decoration:none;
                    border-radius:6px;
                "
            >
                Reset Password
            </a>
        </p>

        <p>
            If you did not request this password reset,
            you can safely ignore this email.
        </p>

        <p>
            For your security, do not share this link
            with anyone.
        </p>

        <p>
            Regards,<br>
            <strong>SecureCrypt Security Team</strong>
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,

        subject=subject,

        html_content=html_content,

        text_content=text_content,
    )

    return True


# ============================================================
# PASSWORD CHANGED EMAIL
# ============================================================

def send_password_changed_email(
    user
):

    if not user.email:
        return False

    username = html.escape(
        user.username
    )

    subject = (
        "Security Alert: "
        "Your SecureCrypt Password Was Changed"
    )

    text_content = f"""
Hello {user.username},

Your SecureCrypt account password was
successfully changed.

If you changed your password,
no further action is required.

If you DID NOT change your password,
your account may be compromised.

Please contact the SecureCrypt administrator
immediately so your account can be secured.

SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt Security Alert</h2>

        <p>
            Hello {username},
        </p>

        <p>
            Your SecureCrypt account password was
            <strong>successfully changed.</strong>
        </p>

        <p>
            If you changed your password,
            no further action is required.
        </p>

        <p>
            If you <strong>DID NOT</strong> change
            your password, your account may be compromised.
        </p>

        <p>
            Please contact the SecureCrypt administrator
            immediately so your account can be secured.
        </p>

        <p>
            Regards,<br>
            <strong>SecureCrypt Security Team</strong>
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,

        subject=subject,

        html_content=html_content,

        text_content=text_content,
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

    username = html.escape(
        user.username
    )

    safe_reason = html.escape(
        reason
    )

    subject = (
        "SecureCrypt - Account Locked"
    )

    text_content = f"""
Hello {user.username},

Your SecureCrypt account has been
temporarily locked.

Reason:
{reason}

Lock duration:
{hours} hour(s)

Your account will be available again
after the lock period expires.

If you did not expect this action,
please contact the administrator.

Regards,
SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt</h2>

        <p>
            Hello {username},
        </p>

        <p>
            Your SecureCrypt account has been
            <strong>temporarily locked.</strong>
        </p>

        <p>
            <strong>Reason:</strong><br>
            {safe_reason}
        </p>

        <p>
            <strong>Lock duration:</strong><br>
            {hours} hour(s)
        </p>

        <p>
            Your account will be available again
            after the lock period expires.
        </p>

        <p>
            Regards,<br>
            <strong>SecureCrypt Security Team</strong>
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,

        subject=subject,

        html_content=html_content,

        text_content=text_content,
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

    username = html.escape(
        user.username
    )

    safe_reason = html.escape(
        reason
    )

    subject = (
        "SecureCrypt - Account Unlocked"
    )

    text_content = f"""
Hello {user.username},

Your SecureCrypt account has been unlocked.

Reason:
{reason}

You can now log in and use your
SecureCrypt account normally.

If you did not expect this action,
please contact the administrator immediately.

Regards,
SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt</h2>

        <p>
            Hello {username},
        </p>

        <p>
            Your SecureCrypt account has been
            <strong>unlocked.</strong>
        </p>

        <p>
            <strong>Reason:</strong><br>
            {safe_reason}
        </p>

        <p>
            You can now log in and use your
            SecureCrypt account normally.
        </p>

        <p>
            Regards,<br>
            <strong>SecureCrypt Security Team</strong>
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,

        subject=subject,

        html_content=html_content,

        text_content=text_content,
    )

    return True


# ============================================================
# REGISTRATION SUCCESS
# ============================================================

def send_registration_success_email(
    user
):

    if not user.email:
        return False

    username = html.escape(
        user.username
    )

    subject = (
        "SecureCrypt - Registration Successful"
    )

    text_content = f"""
Hello {user.username},

Your SecureCrypt account has been
successfully registered.

Your account is currently waiting
for administrator approval.

You will be able to log in and use
SecureCrypt once your account has
been approved.

Please do not share your password
with anyone.

Regards,
SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt</h2>

        <p>
            Hello {username},
        </p>

        <p>
            Your SecureCrypt account has been
            <strong>successfully registered.</strong>
        </p>

        <p>
            Your account is currently waiting
            for administrator approval.
        </p>

        <p>
            You will be able to log in and use
            SecureCrypt once your account has
            been approved.
        </p>

        <p>
            Please do not share your password
            with anyone.
        </p>

        <p>
            Regards,<br>
            <strong>SecureCrypt Security Team</strong>
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,

        subject=subject,

        html_content=html_content,

        text_content=text_content,
    )

    return True


# ============================================================
# NEW REGISTRATION → ADMIN
# ============================================================

def send_new_registration_admin_email(
    user
):

    admin_email = os.environ.get(
        "BREVO_ADMIN_EMAIL"
    )

    if not admin_email:

        admin_email = os.environ.get(
            "BREVO_SENDER_EMAIL"
        )

    if not admin_email:
        return False

    username = html.escape(
        user.username
    )

    user_email = html.escape(
        user.email
    )

    phone = html.escape(
        user.phone
    )

    subject = (
        "SecureCrypt - New User Registration"
    )

    text_content = (
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
    )

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt</h2>

        <p>
            Hello Administrator,
        </p>

        <p>
            A new user has registered on SecureCrypt
            and is waiting for approval.
        </p>

        <p>
            <strong>Username:</strong>
            {username}
            <br>

            <strong>Email:</strong>
            {user_email}
            <br>

            <strong>Phone:</strong>
            {phone}
        </p>

        <p>
            Please log in to the SecureCrypt
            Admin Dashboard to review this registration.
        </p>

        <p>
            Regards,<br>
            <strong>SecureCrypt Security System</strong>
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=admin_email,

        subject=subject,

        html_content=html_content,

        text_content=text_content,
    )

    return True


# ============================================================
# USER APPROVED
# ============================================================

def send_user_approved_email(
    user
):

    if not user.email:
        return False

    username = html.escape(
        user.username
    )

    subject = (
        "SecureCrypt - Account Approved"
    )

    text_content = f"""
Hello {user.username},

Good news!

Your SecureCrypt account has been
approved by the administrator.

You can now log in to SecureCrypt
and use the available features.

Please keep your account credentials secure.

Regards,
SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt</h2>

        <p>
            Hello {username},
        </p>

        <p>
            Good news!
        </p>

        <p>
            Your SecureCrypt account has been
            <strong>approved.</strong>
        </p>

        <p>
            You can now log in to SecureCrypt
            and use the available features.
        </p>

        <p>
            Please keep your account credentials secure.
        </p>

        <p>
            Regards,<br>
            <strong>SecureCrypt Security Team</strong>
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,

        subject=subject,

        html_content=html_content,

        text_content=text_content,
    )

    return True


# ============================================================
# USER REJECTED
# ============================================================

def send_user_rejected_email(
    user
):

    if not user.email:
        return False

    username = html.escape(
        user.username
    )

    subject = (
        "SecureCrypt - Account Registration Update"
    )

    text_content = f"""
Hello {user.username},

We are writing to inform you that your
SecureCrypt account registration has
been rejected by the administrator.

You currently cannot log in to SecureCrypt
using this account.

If you believe this was a mistake,
please contact the SecureCrypt administrator.

Regards,
SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt</h2>

        <p>
            Hello {username},
        </p>

        <p>
            We are writing to inform you that your
            SecureCrypt account registration has
            been <strong>rejected.</strong>
        </p>

        <p>
            You currently cannot log in to SecureCrypt
            using this account.
        </p>

        <p>
            If you believe this was a mistake,
            please contact the SecureCrypt administrator.
        </p>

        <p>
            Regards,<br>
            <strong>SecureCrypt Security Team</strong>
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,

        subject=subject,

        html_content=html_content,

        text_content=text_content,
    )

    return True


# ============================================================
# USER DEACTIVATED
# ============================================================

def send_user_deactivated_email(
    user
):

    if not user.email:
        return False

    username = html.escape(
        user.username
    )

    subject = (
        "SecureCrypt - Account Deactivated"
    )

    text_content = f"""
Hello {user.username},

Your SecureCrypt account has been
deactivated by the administrator.

You will not be able to access your account
while it is deactivated.

If you believe this action was taken by mistake,
please contact the SecureCrypt administrator.

Regards,
SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt</h2>

        <p>
            Hello {username},
        </p>

        <p>
            Your SecureCrypt account has been
            <strong>deactivated</strong> by
            the administrator.
        </p>

        <p>
            You will not be able to access your
            account while it is deactivated.
        </p>

        <p>
            If you believe this action was taken
            by mistake, please contact the
            SecureCrypt administrator.
        </p>

        <p>
            Regards,<br>
            <strong>SecureCrypt Security Team</strong>
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,

        subject=subject,

        html_content=html_content,

        text_content=text_content,
    )

    return True


# ============================================================
# USER DELETED
# ============================================================

def send_user_deleted_email(
    user
):

    if not user.email:
        return False

    username = html.escape(
        user.username
    )

    subject = (
        "SecureCrypt - Account Deleted"
    )

    text_content = f"""
Hello {user.username},

Your SecureCrypt account has been
deleted by the administrator.

You will no longer be able to log in
or access this SecureCrypt account.

If you believe this action was taken
by mistake, please contact the
SecureCrypt administrator.

Regards,
SecureCrypt Security Team
"""

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt</h2>

        <p>
            Hello {username},
        </p>

        <p>
            Your SecureCrypt account has been
            <strong>deleted</strong> by the administrator.
        </p>

        <p>
            You will no longer be able to log in
            or access this SecureCrypt account.
        </p>

        <p>
            If you believe this action was taken
            by mistake, please contact the
            SecureCrypt administrator.
        </p>

        <p>
            Regards,<br>
            <strong>SecureCrypt Security Team</strong>
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=user.email,

        subject=subject,

        html_content=html_content,

        text_content=text_content,
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

    owner_username = html.escape(
        owner.username
    )

    attempted_username = html.escape(
        attempted_by.username
    )

    safe_filename = html.escape(
        filename
    )

    subject = (
        "SecureCrypt - Suspicious Activity Detected"
    )

    text_content = (
        f"Hello {owner.username},\n\n"

        "We detected suspicious activity involving "
        "one of your encrypted files.\n\n"

        f"File: {filename}\n"
        f"Attempted by account: "
        f"{attempted_by.username}\n\n"

        "Another account attempted to decrypt a file "
        "belonging to you. The attempt was blocked "
        "by SecureCrypt.\n\n"

        "If you recognize this activity, no action is "
        "required. Otherwise, please review your "
        "account security.\n\n"

        "Regards,\n"
        "SecureCrypt Security Team"
    )

    html_content = f"""
    <html>
    <body>

        <h2>SecureCrypt Security Alert</h2>

        <h3>
            Suspicious Activity Detected
        </h3>

        <p>
            Hello {owner_username},
        </p>

        <p>
            We detected suspicious activity involving
            one of your encrypted files.
        </p>

        <p>
            <strong>File:</strong>
            {safe_filename}
            <br>

            <strong>Attempted by account:</strong>
            {attempted_username}
        </p>

        <p>
            Another account attempted to decrypt a file
            belonging to you. The attempt was blocked
            by SecureCrypt.
        </p>

        <p>
            If you recognize this activity, no action is
            required. Otherwise, please review your
            account security.
        </p>

        <p>
            Regards,<br>
            <strong>SecureCrypt Security Team</strong>
        </p>

    </body>
    </html>
    """

    send_brevo_email(
        recipient_email=owner.email,

        subject=subject,

        html_content=html_content,

        text_content=text_content,
    )

    return True
