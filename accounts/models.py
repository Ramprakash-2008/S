from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class CustomUser(AbstractUser):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    email = models.EmailField(unique=True)

    phone = models.CharField(
        max_length=15,
        unique=True
    )
    REQUIRED_FIELDS = ["email", "phone"]
    security_alerts = models.BooleanField(default=True)

    file_expiry_alerts = models.BooleanField(default=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="PENDING"
    )
    failed_login_attempts = models.PositiveIntegerField(default=0)
    
    locked_until = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return self.username


class EncryptedFile(models.Model):

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="encrypted_files"
    )

    original_filename = models.CharField(
        max_length=255
    )

    encrypted_file = models.FileField(
        upload_to="encrypted_files/"
    )
    encrypted_file_hash = models.CharField(
    max_length=64,
    unique=True,
    null=True,
    blank=True
)

    encryption_method = models.CharField(
        max_length=50,
        default="Fernet"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    is_deleted = models.BooleanField(
        default=False
    )
class AdminActivityLog(models.Model):

    ACTION_CHOICES = [
        ("APPROVE_USER", "Approved User"),
        ("REJECT_USER", "Rejected User"),
        ("ACTIVATE_USER", "Activated User"),
        ("DEACTIVATE_USER", "Deactivated User"),
        ("DOWNLOAD_FILE", "Downloaded File"),
        ("DELETE_FILE", "Deleted File"),
    ]

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="admin_activity_logs"
    )

    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES
    )

    target = models.CharField(
        max_length=255
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    
    def __str__(self):
        return self.original_filename
class SecurityLog(models.Model):

    EVENT_CHOICES = [
        ("FAILED_LOGIN", "Failed Login"),
        ("ACCOUNT_LOCKED", "Account Locked"),
        ("SUCCESSFUL_LOGIN", "Successful Login"),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="security_logs"
    )

    username = models.CharField(
        max_length=150
    )

    event = models.CharField(
        max_length=30,
        choices=EVENT_CHOICES
    )

    description = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.username} - {self.event}"
class Notification(models.Model):

    NOTIFICATION_TYPES = (
        ("SECURITY", "Security"),
        ("SUCCESS", "Success"),
        ("WARNING", "Warning"),
        ("PASSWORD", "Password"),
        ("FILE", "File"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(
        max_length=255
    )

    message = models.TextField()

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default="SECURITY"
    )

    is_read = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ["-created_at"]

    def __str__(self):

        return (
            f"{self.user.username} - "
            f"{self.title}"
        )
