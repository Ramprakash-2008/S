from datetime import timedelta
import csv
import json
from functools import wraps
import os
import re
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.db.models.functions import (
    TruncDate,
    TruncDay,
    TruncMonth,
    TruncYear,
)
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import (
    urlsafe_base64_decode,
    urlsafe_base64_encode,
)

from openpyxl import Workbook

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

from encryption import decrypt_file, encrypt_file

from .email_utils import (
    send_account_locked_email,
    send_account_unlocked_email,
    send_encrypted_file,
    send_new_registration_admin_email,
    send_notification_email,
    send_registration_success_email,
    send_suspicious_activity_email,
    send_user_approved_email,
    send_user_deactivated_email,
    send_user_deleted_email,
    send_user_rejected_email,
)
from .models import (
    AdminActivityLog,
    CustomUser,
    EncryptedFile,
    SecurityLog,
     Notification,
)
from .email_utils import (
    send_password_reset_email,
    send_password_changed_email
)
User = get_user_model()

def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):

        if not request.user.is_staff:
            messages.error(
                request,
                "You do not have permission to access this page."
            )
            return redirect("dashboard")

        return view_func(request, *args, **kwargs)

    return wrapper
@login_required
def admin_security_logs_view(request):

    if not request.user.is_staff:
        messages.error(
            request,
            "You do not have permission to access security logs."
        )
        return redirect("dashboard")

    current_time = timezone.now()

    logs = SecurityLog.objects.select_related(
        "user"
    ).order_by(
        "-created_at"
    )

    # Add current lock status to every log
    for log in logs:

        if log.user is not None:
            log.is_currently_locked = (
            log.user.locked_until is not None
            and log.user.locked_until > current_time
        )
        else:
            log.is_currently_locked = False
    # ------------------------------------------
    # SECURITY STATISTICS
    # ------------------------------------------

    total_events = SecurityLog.objects.count()

    failed_logins = SecurityLog.objects.filter(
        event="FAILED_LOGIN"
    ).count()

    successful_logins = SecurityLog.objects.filter(
        event="SUCCESSFUL_LOGIN"
    ).count()

    # IMPORTANT:
    # Count users currently locked,
    # NOT the number of ACCOUNT_LOCKED logs.
    locked_accounts = User.objects.filter(
        locked_until__isnull=False,
        locked_until__gt=current_time
    ).count()

    context = {
        "logs": logs,
        "total_events": total_events,
        "failed_logins": failed_logins,
        "locked_accounts": locked_accounts,
        "successful_logins": successful_logins,
    }

    return render(
        request,
        "accounts/admin_security_logs.html",
        context
    )

@admin_required
def admin_delete_user_view(request, user_id):

    if request.method != "POST":
        return redirect("admin_users")

    user = get_object_or_404(
        CustomUser,
        id=user_id
    )

    # Never allow administrator to delete themselves
    if user.is_superuser:
        messages.warning(
            request,
            "Administrator accounts cannot be deleted."
        )
        return redirect("admin_users")

    username = user.username
    send_user_deleted_email(user)
    user.delete()

    messages.success(
        request,
        f"{username} has been permanently deleted."
    )

    return redirect("admin_users")
@admin_required
def admin_lock_user_view(request, user_id):

    if request.method != "POST":
        return redirect("admin_security_logs")

    user = get_object_or_404(
        CustomUser,
        id=user_id
    )

    # Never manually lock the administrator
    if user.is_superuser:
        messages.warning(
            request,
            "Administrator accounts cannot be locked here."
        )
        return redirect("admin_security_logs")

    # Get duration from the form
    duration = request.POST.get("duration")

    allowed_durations = {
        "1": 1,
        "6": 6,
        "12": 12,
        "24": 24,
    }

    if duration not in allowed_durations:
        messages.error(
            request,
            "Invalid lock duration."
        )
        return redirect("admin_security_logs")

    hours = allowed_durations[duration]

    user.locked_until = (
        timezone.now() + timedelta(hours=hours)
    )

    user.save(
        update_fields=["locked_until"]
    )
    send_account_locked_email(
    user,
    hours,
    reason="Account manually locked by administrator."
)
    # Security log
    SecurityLog.objects.create(
        user=user,
        event="ACCOUNT_LOCKED",
        description=(
            f"Account manually locked by administrator "
            f"for {hours} hour(s)."
        )
    )

    messages.success(
        request,
        f"{user.username} has been locked for {hours} hour(s)."
    )

    return redirect("admin_security_logs")
@login_required
def download_security_logs(request):

    if not request.user.is_staff:
        messages.error(
            request,
            "You do not have permission to download security logs."
        )
        return redirect("dashboard")

    logs = SecurityLog.objects.select_related(
        "user"
    ).order_by("-created_at")

    response = HttpResponse(
        content_type="text/csv"
    )

    response["Content-Disposition"] = (
        'attachment; filename="security_logs.csv"'
    )

    writer = csv.writer(response)

    writer.writerow([
        "User",
        "Event",
        "Description",
        "Date & Time",
    ])

    for log in logs:

        writer.writerow([
            log.user.username if log.user else "Unknown",
            log.event,
            log.description,
            log.created_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        ])

    return response
# ============================================================
# REGISTER
# ============================================================
@login_required
def user_security_logs_view(request):

    logs = SecurityLog.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(
        request,
        "accounts/security_logs.html",
        {
            "logs": logs
        }
    )
def register_view(request):

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()

        password = request.POST.get("password", "")
        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )

        # ==========================================
        # REQUIRED FIELDS
        # ==========================================

        if not username or not email or not phone or not password:

            messages.error(
                request,
                "All fields are required."
            )

            return render(
                request,
                "accounts/register.html"
            )

        # ==========================================
        # PASSWORD MATCH
        # ==========================================

        if password != confirm_password:

            messages.error(
                request,
                "Passwords do not match."
            )

            return render(
                request,
                "accounts/register.html"
            )

        # ==========================================
        # PASSWORD STRENGTH
        # ==========================================

        try:

            validate_password(
                password
            )

        except ValidationError as e:

            for error in e.messages:

                messages.error(
                    request,
                    error
                )

            return render(
                request,
                "accounts/register.html"
            )

        # ==========================================
        # USERNAME CHECK
        # ==========================================

        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                "Username already exists."
            )

            return render(
                request,
                "accounts/register.html"
            )

        # ==========================================
        # EMAIL CHECK
        # ==========================================

        if User.objects.filter(
            email=email
        ).exists():

            messages.error(
                request,
                "Email already exists."
            )

            return render(
                request,
                "accounts/register.html"
            )

        # ==========================================
        # PHONE CHECK
        # ==========================================

        if User.objects.filter(
            phone=phone
        ).exists():

            messages.error(
                request,
                "Phone number already exists."
            )

            return render(
                request,
                "accounts/register.html"
            )

        # ==========================================
        # CREATE USER
        # ONLY AFTER ALL VALIDATION
        # ==========================================

        user = User.objects.create_user(
            username=username,
            email=email,
            phone=phone,
            password=password
        )

        # ==========================================
        # ACCOUNT STATUS
        # ==========================================

        user.status = "PENDING"
        user.is_active = False

        user.save()

        # ==========================================
        # EMAIL USER
        # ==========================================

        send_registration_success_email(
            user
        )

        # ==========================================
        # EMAIL ADMIN
        # ==========================================

        send_new_registration_admin_email(
            user
        )

        # ==========================================
        # SUCCESS MESSAGE
        # ==========================================

        messages.success(
            request,
            "Registration successful. "
            "Please wait for admin approval."
        )

        return redirect(
            "login"
        )

    return render(
        request,
        "accounts/register.html"
    )

# ============================================================
# LOGIN
# ============================================================

def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password")

        try:
            user = User.objects.get(username=username)

        except User.DoesNotExist:

            # Log attempt even if username doesn't exist
            SecurityLog.objects.create(
                user=None,
                username=username,
                event="FAILED_LOGIN",
                description="Login attempt with an invalid username."
            )

            messages.error(
                request,
                "Invalid username or password."
            )

            return render(
                request,
                "accounts/login.html"
            )

        # ==========================================
        # CHECK ACCOUNT LOCK
        # ==========================================

        if user.locked_until:

            if timezone.now() < user.locked_until:

                remaining = user.locked_until - timezone.now()

                hours = int(
                    remaining.total_seconds() // 3600
                )

                messages.error(
                    request,
                    f"Your account is temporarily locked. "
                    f"Please try again after approximately "
                    f"{hours} hour(s)."
                )

                return render(
                    request,
                    "accounts/login.html"
                )

            else:

                # Lock period has expired
                user.locked_until = None
                user.failed_login_attempts = 0

                user.save(
                    update_fields=[
                        "locked_until",
                        "failed_login_attempts"
                    ]
                )

        # ==========================================
        # CHECK PASSWORD
        # ==========================================

        if not user.check_password(password):

            user.failed_login_attempts += 1

            # ======================================
            # LOG FAILED LOGIN
            # ======================================

            SecurityLog.objects.create(
                user=user,
                username=user.username,
                event="FAILED_LOGIN",
                description=(
                    f"Incorrect password attempt "
                    f"({user.failed_login_attempts}/3)."
                )
            )

            # ======================================
            # 3 FAILED ATTEMPTS
            # ======================================

            if user.failed_login_attempts >= 3:

                user.locked_until = (
                    timezone.now()
                    + timedelta(hours=12)
                )

                user.save(
                    update_fields=[
                        "failed_login_attempts",
                        "locked_until"
                    ]
                )
                send_notification_email(
    user.email,
    "SecureCrypt - Account Locked",
    f"""Hello {user.username},

Your SecureCrypt account has been temporarily locked.

Reason:
3 consecutive incorrect password attempts.

Lock duration:
12 hours

Your account will be available again after the lock period expires.

If you did not attempt to log in, please contact the administrator.

Regards,
SecureCrypt Security Team
"""
)
                # ==================================
                # LOG ACCOUNT LOCK
                # ==================================

                SecurityLog.objects.create(
                    user=user,
                    username=user.username,
                    event="ACCOUNT_LOCKED",
                    description=(
                        "Account locked for 12 hours "
                        "after 3 failed login attempts."
                    )
                )
                Notification.objects.create(
    user=user,
    title="Account Locked",
    message=(
        "Your SecureCrypt account has been temporarily locked "
        "for 12 hours after 3 failed login attempts."
    ),
    notification_type="WARNING"
)
                messages.error(
                    request,
                    "Too many incorrect password attempts. "
                    "Your account has been locked for 12 hours."
                )

                return render(
                    request,
                    "accounts/login.html"
                )

            user.save(
                update_fields=[
                    "failed_login_attempts"
                ]
            )

            attempts_left = (
                3 - user.failed_login_attempts
            )

            messages.error(
                request,
                f"Invalid username or password. "
                f"{attempts_left} attempt(s) remaining."
            )

            return render(
                request,
                "accounts/login.html"
            )

        # ==========================================
        # SUCCESSFUL PASSWORD
        # ==========================================

        user.failed_login_attempts = 0

        user.save(
            update_fields=[
                "failed_login_attempts"
            ]
        )

        # ==========================================
        # ADMIN
        # ==========================================

        if user.is_superuser or user.is_staff:

            login(request, user)

            SecurityLog.objects.create(
                user=user,
                username=user.username,
                event="SUCCESSFUL_LOGIN",
                description="Administrator logged in successfully."
            )

            Notification.objects.create(
    user=user,
    title="Administrator Login",
    message="Your SecureCrypt administrator account was logged in successfully.",
    notification_type="SECURITY"
)
            return redirect(
                "admin_dashboard"
            )

        # ==========================================
        # PENDING
        # ==========================================

        if user.status == "PENDING":

            messages.warning(
                request,
                "Your account is waiting for admin approval."
            )

            return render(
                request,
                "accounts/login.html"
            )

        # ==========================================
        # REJECTED
        # ==========================================

        if user.status == "REJECTED":

            messages.error(
                request,
                "Your account registration has been rejected."
            )

            return render(
                request,
                "accounts/login.html"
            )

        # ==========================================
        # APPROVED + ACTIVE
        # ==========================================

        if user.status == "APPROVED" and user.is_active:

            login(request, user)

            SecurityLog.objects.create(
                user=user,
                username=user.username,
                event="SUCCESSFUL_LOGIN",
                description="User logged in successfully."
            )
            Notification.objects.create(
            user=user,
            title="Successful Login",
            message="Your SecureCrypt account was logged in successfully.",
            notification_type="SECURITY"
            )

            return redirect(
                "dashboard"
            )

        messages.error(
            request,
            "Your account is not active. "
            "Please contact the administrator."
        )

    return render(
        request,
        "accounts/login.html"
    )

# ============================================================
# USER DASHBOARD
# ============================================================
    
@login_required
def dashboard_view(request):

    return render(
        request,
        "accounts/dashboard.html"
    )


# ============================================================
# ADMIN - FILE MANAGEMENT
# ============================================================

@admin_required
def admin_file_management_view(request):

    if not request.user.is_staff:
        messages.error(
            request,
            "You do not have permission."
        )
        return redirect("dashboard")

    search = request.GET.get("search", "").strip()

    files = EncryptedFile.objects.select_related(
        "owner"
    ).filter(
        is_deleted=False
    ).order_by("-created_at")

    if search:

        files = files.filter(
            original_filename__icontains=search
        ) | files.filter(
            owner__username__icontains=search
        )

    context = {
        "files": files,
        "search": search,

        # Statistics
        "total_files": EncryptedFile.objects.count(),
        "active_files": EncryptedFile.objects.filter(is_deleted=False).count(),
        "deleted_files": EncryptedFile.objects.filter(is_deleted=True).count(),
    }
    return render(
        request,
        "accounts/admin_file_management.html",
        context
    )
@admin_required
def admin_download_file_view(request, file_id):

    if not request.user.is_superuser:
        return redirect("dashboard")

    file = get_object_or_404(
        EncryptedFile,
        id=file_id
    )
    log_admin_action(
    request.user,
    "DOWNLOAD_FILE",
    file.original_filename
    )
    return FileResponse(
        file.encrypted_file.open("rb"),
        as_attachment=True,
        filename=file.original_filename
    )

# ============================================================
# MY FILES
# ============================================================

@login_required
def my_files_view(request):

    expired_files = EncryptedFile.objects.filter(
        owner=request.user,
        is_deleted=False,
        expires_at__isnull=False,
        expires_at__lte=timezone.now()
    )

    for file in expired_files:

        if file.encrypted_file:
            file.encrypted_file.delete(save=False)

        file.is_deleted = True
        file.save(update_fields=["is_deleted"])
        Notification.objects.create(
            user=request.user,
            title="File Expired",
            message=(
                f"Your encrypted file "
                f"'{file.original_filename}' "
                f"has expired and is no longer available."
            ),
            notification_type="FILE"
        )

    files = EncryptedFile.objects.filter(
        owner=request.user,
        is_deleted=False
    ).order_by("-created_at")

    return render(
        request,
        "accounts/my_files.html",
        {"files": files}
    )

@login_required
def notifications(request):

    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")

    unread_count = notifications.filter(
        is_read=False
    ).count()

    return render(
        request,
        "accounts/notifications.html",
        {
            "notifications": notifications,
            "unread_count": unread_count,
        }
    )
@login_required
def settings_view(request):

    if request.method == "POST":

        setting = request.POST.get("setting")

        if setting == "security_alerts":

            request.user.security_alerts = (
                request.POST.get("security_alerts") == "on"
            )

            request.user.save(
                update_fields=["security_alerts"]
            )


        elif setting == "file_expiry_alerts":

            request.user.file_expiry_alerts = (
                request.POST.get("file_expiry_alerts") == "on"
            )

            request.user.save(
                update_fields=["file_expiry_alerts"]
            )


        return redirect("settings")


    return render(
        request,
        "accounts/settings.html"
    )

@admin_required
def admin_insights_pdf_view(request):

    # ------------------------------------------
    # Get real database data
    # ------------------------------------------

    total_users = CustomUser.objects.count()

    approved_users = CustomUser.objects.filter(
        status="APPROVED"
    ).count()

    pending_users = CustomUser.objects.filter(
        status="PENDING"
    ).count()

    rejected_users = CustomUser.objects.filter(
        status="REJECTED"
    ).count()

    total_files = EncryptedFile.objects.count()

    active_files = EncryptedFile.objects.filter(
        is_deleted=False
    ).count()

    deleted_files = EncryptedFile.objects.filter(
        is_deleted=True
    ).count()

    top_users = CustomUser.objects.annotate(
        file_count=Count("encrypted_files")
    ).order_by(
        "-file_count",
        "username"
    )[:10]


    # ------------------------------------------
    # Create PDF response
    # ------------------------------------------

    response = HttpResponse(
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        'attachment; filename="securecrypt_insights.pdf"'
    )


    # ------------------------------------------
    # Create PDF
    # ------------------------------------------

    pdf = canvas.Canvas(
        response,
        pagesize=A4
    )

    width, height = A4


    # ------------------------------------------
    # Title
    # ------------------------------------------

    pdf.setFont("Helvetica-Bold", 22)

    pdf.setFillColor(colors.HexColor("#1e3a8a"))

    pdf.drawString(
        50,
        height - 60,
        "SecureCrypt Insights"
    )


    pdf.setFont("Helvetica", 10)

    pdf.setFillColor(colors.black)

    pdf.drawString(
        50,
        height - 80,
        "Admin Analytics Report"
    )


    # ------------------------------------------
    # Statistics
    # ------------------------------------------

    y = height - 125

    pdf.setFont("Helvetica-Bold", 14)

    pdf.drawString(
        50,
        y,
        "User Statistics"
    )

    y -= 25

    user_data = [
        ["Metric", "Count"],
        ["Total Users", str(total_users)],
        ["Approved Users", str(approved_users)],
        ["Pending Users", str(pending_users)],
        ["Rejected Users", str(rejected_users)],
    ]

    user_table = Table(
        user_data,
        colWidths=[250, 100]
    )

    user_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#2563eb")
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "FONTNAME",
                (0, 1),
                (-1, -1),
                "Helvetica"
            ),

            (
                "ALIGN",
                (1, 1),
                (1, -1),
                "CENTER"
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                7
            ),
        ])
    )

    user_table.wrapOn(
        pdf,
        width,
        height
    )

    user_table.drawOn(
        pdf,
        50,
        y - 100
    )


    # ------------------------------------------
    # File Statistics
    # ------------------------------------------

    y -= 145

    pdf.setFont(
        "Helvetica-Bold",
        14
    )

    pdf.drawString(
        50,
        y,
        "File Statistics"
    )

    y -= 25

    file_data = [
        ["Metric", "Count"],
        ["Total Files", str(total_files)],
        ["Active Files", str(active_files)],
        ["Deleted Files", str(deleted_files)],
    ]

    file_table = Table(
        file_data,
        colWidths=[250, 100]
    )

    file_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#10b981")
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "ALIGN",
                (1, 1),
                (1, -1),
                "CENTER"
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                7
            ),
        ])
    )

    file_table.wrapOn(
        pdf,
        width,
        height
    )

    file_table.drawOn(
        pdf,
        50,
        y - 80
    )


    # ------------------------------------------
    # Top Users
    # ------------------------------------------

    y -= 125

    pdf.setFont(
        "Helvetica-Bold",
        14
    )

    pdf.drawString(
        50,
        y,
        "Top Users"
    )

    y -= 25

    top_user_data = [
        ["Rank", "Username", "Email", "Files"]
    ]

    for index, user in enumerate(
        top_users,
        start=1
    ):

        top_user_data.append([
            str(index),
            user.username,
            user.email,
            str(user.file_count)
        ])


    top_table = Table(
        top_user_data,
        colWidths=[
            45,
            120,
            200,
            60
        ]
    )

    top_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#7c3aed")
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                6
            ),
        ])
    )

    top_table.wrapOn(
        pdf,
        width,
        height
    )

    top_table.drawOn(
        pdf,
        50,
        y - 200
    )


    # ------------------------------------------
    # Footer
    # ------------------------------------------

    pdf.setFont(
        "Helvetica",
        8
    )

    pdf.setFillColor(colors.grey)

    pdf.drawString(
        50,
        30,
        "Generated by SecureCrypt Admin"
    )


    # ------------------------------------------
    # Finish PDF
    # ------------------------------------------

    pdf.save()

    return response
@admin_required
def admin_activity_logs_view(request):

    logs = AdminActivityLog.objects.select_related(
        "admin"
    ).order_by("-created_at")

    # Activity statistics
    total_activities = logs.count()

    approved_users = logs.filter(
        action="APPROVE_USER"
    ).count()

    rejected_users = logs.filter(
        action="REJECT_USER"
    ).count()

    file_activities = logs.filter(
        action__in=[
            "DOWNLOAD_FILE",
            "DELETE_FILE"
        ]
    ).count()

    return render(
        request,
        "accounts/admin_activity_logs.html",
        {
            "logs": logs,

            "total_activities": total_activities,
            "approved_users": approved_users,
            "rejected_users": rejected_users,
            "file_activities": file_activities,
        }
    )
@admin_required
def admin_delete_file_view(request, file_id):

    if not request.user.is_superuser:
        return redirect("dashboard")

    file = get_object_or_404(
        EncryptedFile,
        id=file_id
    )
    log_admin_action(
        request.user,
        "DELETE_FILE",
        file.original_filename
    )
    file.encrypted_file.delete(save=False)
    file.delete()

    messages.success(
        request,
        "Encrypted file deleted successfully."
    )

    return redirect("admin_files")
# ============================================================
# DOWNLOAD ENCRYPTED FILE
# ============================================================
@admin_required
def download_activity_logs(request):

    logs = AdminActivityLog.objects.select_related(
        "admin"
    ).order_by("-created_at")

    workbook = Workbook()
    worksheet = workbook.active

    worksheet.title = "Activity Logs"

    worksheet.append([
        "ID",
        "Administrator",
        "Action",
        "Target",
        "Date & Time"
    ])

    for log in logs:

        worksheet.append([
            log.id,
            log.admin.username,
            log.get_action_display(),
            log.target,
            log.created_at.strftime("%d-%m-%Y %H:%M:%S")
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response["Content-Disposition"] = (
        'attachment; filename="SecureCrypt_Activity_Logs.xlsx"'
    )

    workbook.save(response)

    return response

def log_admin_action(admin, action, target):
    AdminActivityLog.objects.create(
        admin=admin,
        action=action,
        target=target
    )
@login_required
def admin_unlock_user(request, user_id):

    if not request.user.is_staff:
        messages.error(
            request,
            "You do not have permission to perform this action."
        )
        return redirect("dashboard")

    if request.method != "POST":
        return redirect("admin_security_logs")

    user = get_object_or_404(
        CustomUser,
        id=user_id
    )

    # Never modify administrator accounts
    if user.is_superuser:
        messages.warning(
            request,
            "Administrator accounts cannot be modified here."
        )
        return redirect("admin_security_logs")

    user.locked_until = None
    user.failed_login_attempts = 0

    user.save(
        update_fields=[
            "locked_until",
            "failed_login_attempts"
        ]
    )
    send_account_unlocked_email(
        user,
        reason="Account manually unlocked by administrator."
    )

    # Record security event
    SecurityLog.objects.create(
        user=user,
        event="ACCOUNT_UNLOCKED",
        description=(
            f"Account unlocked manually by "
            f"administrator {request.user.username}."
        )
    )

    messages.success(
        request,
        f"{user.username}'s account has been unlocked."
    )

    return redirect("admin_security_logs")
@login_required
def clear_security_logs(request):

    if not request.user.is_staff:
        messages.error(
            request,
            "You do not have permission to perform this action."
        )
        return redirect("dashboard")

    if request.method != "POST":
        return redirect("admin_security_logs")

    SecurityLog.objects.all().delete()

    messages.success(
        request,
        "All security logs have been cleared."
    )

    return redirect("admin_security_logs")
@login_required
def download_encrypted_file_view(request, file_id):

    try:

        encrypted_file = EncryptedFile.objects.get(
            id=file_id,
            owner=request.user,
            is_deleted=False
        )

    except EncryptedFile.DoesNotExist:

        messages.error(request, "File not found.")
        return redirect("my_files")

    if (
        encrypted_file.expires_at
        and encrypted_file.expires_at <= timezone.now()
    ):

        if encrypted_file.encrypted_file:
            encrypted_file.encrypted_file.delete(save=False)

        encrypted_file.is_deleted = True
        encrypted_file.save(update_fields=["is_deleted"])

        messages.error(
            request,
            "This encrypted file has expired."
        )

        return redirect("my_files")

    if not encrypted_file.encrypted_file:

        messages.error(
            request,
            "Encrypted file is not available."
        )

        return redirect("my_files")

    try:

        file_data = encrypted_file.encrypted_file.read()

        response = HttpResponse(
            file_data,
            content_type="application/octet-stream"
        )

        response["Content-Disposition"] = (
            f'attachment; '
            f'filename="{encrypted_file.original_filename}.enc"'
        )

        return response

    except Exception:
        messages.error(
        request,
        "Unable to download the encrypted file."
    )
    return redirect("my_files")

      

# ============================================================
# CHANGE PASSWORD
# ============================================================

@login_required
def change_password_view(request):

    if request.method == "POST":

        form = PasswordChangeForm(
            request.user,
            request.POST
        )

        if form.is_valid():

            user = form.save()

            update_session_auth_hash(
                request,
                user
            )

            email_sent = False

            try:

                send_mail(
                    subject="SecureCrypt - Password Changed",
                    message=(
                        f"Hello {user.username},\n\n"
                        "Your SecureCrypt account password "
                        "was successfully changed.\n\n"
                        "If you made this change, no further "
                        "action is required.\n\n"
                        "If you did not make this change, "
                        "please contact the SecureCrypt administrator "
                        "immediately.\n\n"
                        "Regards,\n"
                        "SecureCrypt Security Team"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False
                )

                email_sent = True

            except Exception as e:

                print(
                    "PASSWORD CHANGE EMAIL ERROR:",
                    e
                )

            if email_sent:

                messages.success(
                    request,
                    "Password changed successfully. "
                    "A security confirmation email has been sent."
                )

            else:

                messages.warning(
                    request,
                    "Password changed successfully, "
                    "but the confirmation email could not be sent."
                )

            return redirect("change_password")

        else:

            for field_errors in form.errors.values():

                for error in field_errors:
                    messages.error(request, error)

    else:

        form = PasswordChangeForm(request.user)

    return render(
        request,
        "accounts/change_password.html",
        {"form": form}
    )


# ============================================================
# CLEAR FILE HISTORY
# ============================================================

@login_required
def clear_file_history_view(request):

    if request.method == "POST":

        files = EncryptedFile.objects.filter(
            owner=request.user,
            is_deleted=False
        )

        deleted_count = 0

        for file in files:

            if file.encrypted_file:
                file.encrypted_file.delete(save=False)

            file.is_deleted = True
            file.save(update_fields=["is_deleted"])

            deleted_count += 1

        messages.success(
            request,
            f"{deleted_count} encrypted file(s) deleted from your history."
        )

    return redirect("my_files")


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@admin_required
def admin_dashboard_view(request):

    if not request.user.is_staff:

        messages.error(
            request,
            "You do not have permission to access the admin dashboard."
        )

        return redirect("dashboard")

    total_users = CustomUser.objects.count()

    approved_users = CustomUser.objects.filter(
        status="APPROVED"
    ).count()

    pending_users = CustomUser.objects.filter(
        status="PENDING"
    ).count()

    rejected_users = CustomUser.objects.filter(
        status="REJECTED"
    ).count()
    

    total_files = EncryptedFile.objects.count()

    recent_users = CustomUser.objects.order_by(
        "-date_joined"
    )[:5]

    recent_files = EncryptedFile.objects.select_related(
        "owner"
    ).order_by(
        "-created_at"
    )[:5]
    
    context = {
        "total_users": total_users,
        "approved_users": approved_users,
        "pending_users": pending_users,
        "rejected_users": rejected_users,
        "total_files": total_files,
        "recent_users": recent_users,
        "recent_files": recent_files,
        
    }

    return render(
        request,
        "accounts/admin_dashboard.html",
        context
    )


# ============================================================
# ADMIN - USER MANAGEMENT
# ============================================================

@admin_required
def admin_users_view(request):

    if not request.user.is_staff:

        messages.error(
            request,
            "You do not have permission to access user management."
        )

        return redirect("dashboard")

    users = CustomUser.objects.all().order_by("-date_joined")

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        users = users.filter(
            username__icontains=search
        ) | users.filter(
            email__icontains=search
        )

    total_users = CustomUser.objects.count()

    active_users = CustomUser.objects.filter(
        is_active=True
    ).count()

    pending_users = CustomUser.objects.filter(
        status="PENDING"
    ).count()

    rejected_users = CustomUser.objects.filter(
        status="REJECTED"
    ).count()
    locked_users = CustomUser.objects.filter(
        locked_until__isnull=False,
        locked_until__gt=timezone.now()
        ).count()
    context = {
        "users": users,
        "search": search,
        "total_users": total_users,
        "active_users": active_users,
        "pending_users": pending_users,
        "rejected_users": rejected_users,
        "locked_users": locked_users,
    }

    return render(
        request,
        "accounts/admin_users.html",
        context
    )

# ============================================================
# ADMIN - PENDING APPROVALS
# ============================================================

@admin_required
def pending_approvals_view(request):

    # Only staff/admin users
    if not request.user.is_staff:
        messages.error(
            request,
            "You do not have permission to access pending approvals."
        )
        return redirect("dashboard")

    # Get only users waiting for approval
    pending_users = CustomUser.objects.filter(
        status="PENDING"
    ).order_by("-date_joined")

    context = {
        "pending_users": pending_users,
        "pending_count": pending_users.count(),
    }

    return render(
        request,
        "accounts/pending_approvals.html",
        context
    )
# ============================================================
# ADMIN - USER DETAIL
# ============================================================

@admin_required
def admin_user_detail_view(request, user_id):

    if not request.user.is_staff:

        messages.error(
            request,
            "You do not have permission to access user details."
        )

        return redirect("dashboard")

    user = get_object_or_404(
        CustomUser,
        id=user_id
    )

    return render(
        request,
        "accounts/admin_user_detail.html",
        {
            "user_obj": user
        }
    )


# ============================================================
# ADMIN - APPROVE USER
# ============================================================

@admin_required
def approve_user_view(request, user_id):

    if not request.user.is_staff:

        messages.error(
            request,
            "You do not have permission to perform this action."
        )

        return redirect("dashboard")

    if request.method != "POST":
        return redirect("admin_users")

    user = get_object_or_404(
        CustomUser,
        id=user_id
    )

    if user.is_superuser:

        messages.warning(
            request,
            "Administrator accounts cannot be modified here."
        )

        return redirect("admin_users")

    user.status = "APPROVED"
    user.is_active = True
    user.save()
    send_user_approved_email(user)
    log_admin_action(
    request.user,
    "APPROVE_USER",
    user.username
    )
    messages.success(
        request,
        f"{user.username} has been approved successfully."
    )

    return redirect("admin_users")


# ============================================================
# ADMIN - REJECT USER
# ============================================================

@admin_required
def reject_user_view(request, user_id):

    if not request.user.is_staff:

        messages.error(
            request,
            "You do not have permission to perform this action."
        )

        return redirect("dashboard")

    if request.method != "POST":
        return redirect("admin_users")

    user = get_object_or_404(
        CustomUser,
        id=user_id
    )

    if user.is_superuser:

        messages.warning(
            request,
            "Administrator accounts cannot be modified here."
        )

        return redirect("admin_users")

    user.status = "REJECTED"
    user.is_active = False
    user.save()
    send_user_rejected_email(user)
    log_admin_action(
    request.user,
    "REJECT_USER",
    user.username
    )
    messages.success(
        request,
        f"{user.username} has been rejected."
    )

    return redirect("admin_users")


# ============================================================
# ADMIN - ACTIVATE USER
# ============================================================

@admin_required
def activate_user_view(request, user_id):

    if not request.user.is_staff:

        messages.error(
            request,
            "You do not have permission to perform this action."
        )

        return redirect("dashboard")

    if request.method != "POST":

        return redirect("admin_users")

    user = get_object_or_404(
        CustomUser,
        id=user_id
    )

    # Never modify superuser
    if user.is_superuser:

        messages.warning(
            request,
            "Administrator accounts cannot be modified here."
        )

        return redirect("admin_users")

    user.status = "APPROVED"
    user.is_active = True

    user.save(
        update_fields=[
            "status",
            "is_active"
        ]
    )
    log_admin_action(
    request.user,
    "ACTIVATE_USER",
    user.username
    )
    messages.success(
        request,
        f"{user.username} has been activated."
    )

    return redirect("admin_users")

@admin_required
def unlock_user_view(request, user_id):

    if request.method != "POST":
        return redirect("admin_users")

    user = get_object_or_404(
        CustomUser,
        id=user_id
    )

    # Never unlock/modify administrator here
    if user.is_superuser:
        messages.warning(
            request,
            "Administrator accounts cannot be modified here."
        )
        return redirect("admin_users")

    # Check whether actually locked
    if not user.locked_until:
        messages.info(
            request,
            f"{user.username} is not currently locked."
        )
        return redirect("admin_users")

    user.locked_until = None
    user.failed_login_attempts = 0

    user.save(
        update_fields=[
            "locked_until",
            "failed_login_attempts"
        ]
    )

    # Security log
    SecurityLog.objects.create(
        user=user,
        event="ACCOUNT_UNLOCKED",
        description=(
            f"Account manually unlocked by administrator "
            f"{request.user.username}."
        )
    )

    messages.success(
        request,
        f"{user.username} has been unlocked successfully."
    )

    return redirect("admin_users")
# ============================================================
# ADMIN - DEACTIVATE USER
# ============================================================

@admin_required
def admin_insights_view(request):

    # ==========================================
    # BASIC STATISTICS
    # ==========================================

    total_users = CustomUser.objects.count()

    approved_users = CustomUser.objects.filter(
        status="APPROVED"
    ).count()

    pending_users = CustomUser.objects.filter(
        status="PENDING"
    ).count()

    rejected_users = CustomUser.objects.filter(
        status="REJECTED"
    ).count()


    # ==========================================
    # FILE STATISTICS
    # ==========================================

    total_files = EncryptedFile.objects.count()

    active_files = EncryptedFile.objects.filter(
        is_deleted=False
    ).count()

    deleted_files = EncryptedFile.objects.filter(
        is_deleted=True
    ).count()


    # ==========================================
    # TOP USERS
    # ==========================================

    top_users = CustomUser.objects.annotate(
        file_count=Count("encrypted_files")
    ).order_by(
        "-file_count",
        "username"
    )


    # ==========================================
    # CURRENT DATE
    # ==========================================

    today = timezone.localdate()


    # ==========================================
    # LAST 7 DAYS
    # ==========================================

    seven_days_ago = today - timedelta(days=6)

    week_queryset = (
        CustomUser.objects
        .filter(
            date_joined__date__gte=seven_days_ago,
            date_joined__date__lte=today
        )
        .annotate(
            day=TruncDate("date_joined")
        )
        .values("day")
        .annotate(
            count=Count("id")
        )
        .order_by("day")
    )

    week_counts = {
        item["day"]: item["count"]
        for item in week_queryset
    }

    week_labels = []
    week_data = []

    for i in range(7):

        current_day = seven_days_ago + timedelta(days=i)

        week_labels.append(
            current_day.strftime("%d %b")
        )

        week_data.append(
            week_counts.get(current_day, 0)
        )


    # ==========================================
    # LAST 30 DAYS
    # ==========================================

    thirty_days_ago = today - timedelta(days=29)

    month_queryset = (
        CustomUser.objects
        .filter(
            date_joined__date__gte=thirty_days_ago,
            date_joined__date__lte=today
        )
        .annotate(
            day=TruncDate("date_joined")
        )
        .values("day")
        .annotate(
            count=Count("id")
        )
        .order_by("day")
    )

    month_counts = {
        item["day"]: item["count"]
        for item in month_queryset
    }

    month_labels = []
    month_data = []

    for i in range(30):

        current_day = thirty_days_ago + timedelta(days=i)

        month_labels.append(
            current_day.strftime("%d %b")
        )

        month_data.append(
            month_counts.get(current_day, 0)
        )


    # ==========================================
    # LAST YEAR - MONTH BY MONTH
    # ==========================================

    current_year = today.year
    current_month = today.month

    year_queryset = (
        CustomUser.objects
        .filter(
            date_joined__year__gte=current_year - 1
        )
        .annotate(
            month=TruncMonth("date_joined")
        )
        .values("month")
        .annotate(
            count=Count("id")
        )
        .order_by("month")
    )

    year_counts = {
        item["month"].strftime("%Y-%m"): item["count"]
        for item in year_queryset
    }

    year_labels = []
    year_data = []

    # Last 12 months
    for i in range(11, -1, -1):

        month = current_month - i
        year = current_year

        while month <= 0:
            month += 12
            year -= 1

        key = f"{year:04d}-{month:02d}"

        month_name = timezone.datetime(
            year,
            month,
            1
        ).strftime("%b %Y")

        year_labels.append(month_name)

        year_data.append(
            year_counts.get(key, 0)
        )


    # ==========================================
    # ALL TIME - YEAR BY YEAR
    # ==========================================

    all_queryset = (
        CustomUser.objects
        .annotate(
            year=TruncYear("date_joined")
        )
        .values("year")
        .annotate(
            count=Count("id")
        )
        .order_by("year")
    )

    all_labels = []
    all_data = []

    for item in all_queryset:

        all_labels.append(
            item["year"].strftime("%Y")
        )

        all_data.append(
            item["count"]
        )


    # ==========================================
    # CONTEXT
    # ==========================================

    context = {

        # Statistics
        "total_users": total_users,
        "approved_users": approved_users,
        "pending_users": pending_users,
        "rejected_users": rejected_users,

        "total_files": total_files,
        "active_files": active_files,
        "deleted_files": deleted_files,

        # Top users
        "top_users": top_users,

        # Chart data
        "week_labels": json.dumps(week_labels),
        "week_data": json.dumps(week_data),

        "month_labels": json.dumps(month_labels),
        "month_data": json.dumps(month_data),

        "year_labels": json.dumps(year_labels),
        "year_data": json.dumps(year_data),

        "all_labels": json.dumps(all_labels),
        "all_data": json.dumps(all_data),
    }

    return render(
        request,
        "accounts/admin_insights.html",
        context
    )
@admin_required
def deactivate_user_view(request, user_id):

    if not request.user.is_staff:

        messages.error(
            request,
            "You do not have permission to perform this action."
        )

        return redirect("dashboard")

    if request.method != "POST":

        return redirect("admin_users")

    user = get_object_or_404(
        CustomUser,
        id=user_id
    )

    # Don't deactivate admin
    if user.is_superuser:

        messages.warning(
            request,
            "Administrator accounts cannot be modified here."
        )

        return redirect("admin_users")

    # Don't deactivate yourself
    if user == request.user:

        messages.error(
            request,
            "You cannot deactivate yourself."
        )

        return redirect("admin_users")

    user.is_active = False

    user.save(
        update_fields=[
            "is_active"
        ]
    )
    send_user_deactivated_email(user)
    log_admin_action(
        request.user,
        "DEACTIVATE_USER",
        user.username
    )
    messages.success(
        request,
        f"{user.username} has been deactivated."
    )

    return redirect("admin_users")


# ============================================================
# ENCRYPT FILE
# ============================================================

@login_required
def encrypt_file_view(request):

    if request.method == "POST":

        uploaded_file = request.FILES.get("file")
        password = request.POST.get("password")
        recipient_email = request.POST.get(
            "recipient_email",
            ""
        ).strip()

        expiry = request.POST.get("expiry")

        if not uploaded_file:

            messages.error(
                request,
                "Please select a file."
            )

            return render(
                request,
                "accounts/encrypt.html"
            )

        if not password:

            messages.error(
                request,
                "Please enter an encryption password."
            )

            return render(
                request,
                "accounts/encrypt.html"
            )

        if not recipient_email:

            messages.error(
                request,
                "Please enter a recipient email address."
            )

            return render(
                request,
                "accounts/encrypt.html"
            )

        expires_at = None

        if expiry == "1hour":

            expires_at = (
                timezone.now()
                + timedelta(hours=1)
            )

        elif expiry == "1day":

            expires_at = (
                timezone.now()
                + timedelta(days=1)
            )

        elif expiry == "7days":

            expires_at = (
                timezone.now()
                + timedelta(days=7)
            )

        elif expiry == "never":

            expires_at = None

        try:

            file_data = uploaded_file.read()

            encrypted_data = encrypt_file(
                file_data,
                password
            )

            encrypted_name = (
                uploaded_file.name + ".enc"
            )

            encrypted_file = EncryptedFile(
                owner=request.user,
                original_filename=uploaded_file.name,
                encryption_method="Fernet",
                expires_at=expires_at
            )

            encrypted_file.encrypted_file.save(
                encrypted_name,
                ContentFile(encrypted_data),
                save=True
            )
            # ==========================================
# SECURITY LOG
# ==========================================

            SecurityLog.objects.create(
    user=request.user,
    username=request.user.username,
    event="FILE_ENCRYPTED",
    description=(
        f"File '{uploaded_file.name}' "
        "was encrypted successfully."
    )
)

# ==========================================
# NOTIFICATION
# ==========================================

            Notification.objects.create(
    user=request.user,
    title="File Encrypted",
    message=(
        f"Your file '{uploaded_file.name}' "
        "was encrypted successfully."
    ),
    notification_type="FILE"
)
            email_sent = False

            try:

                email_sent = send_encrypted_file(
                    recipient_email,
                    encrypted_file.encrypted_file.path,
                    encrypted_name
                )

            except Exception as email_error:

                messages.warning(
                    request,
                    "File encrypted successfully, "
                    "but the email could not be sent."
                )

                print(
                    "EMAIL ERROR:",
                    email_error
                )

            if email_sent:

                messages.success(
                    request,
                    "File encrypted successfully "
                    f"and sent to {recipient_email}."
                )

            else:

                messages.info(
                    request,
                    "The encrypted file was created successfully."
                )

            response = HttpResponse(
                encrypted_data,
                content_type="application/octet-stream"
            )

            response["Content-Disposition"] = (
                'attachment; '
                f'filename="{encrypted_name}"'
            )

            return response

        except Exception as e:

            messages.error(
                request,
                f"Encryption failed: {str(e)}"
            )

    return render(
        request,
        "accounts/encrypt.html"
    )


# ============================================================
# DECRYPT FILE
# ============================================================

@login_required
def decrypt_file_view(request):

    if request.method == "POST":

        uploaded_file = request.FILES.get("file")
        password = request.POST.get(
            "password",
            ""
        ).strip()

        if not uploaded_file:

            messages.error(
                request,
                "Please select an encrypted .enc file."
            )

            return render(
                request,
                "accounts/decrypt.html"
            )

        if not uploaded_file.name.lower().endswith(".enc"):

            messages.error(
                request,
                "Please upload a valid .enc encrypted file."
            )

            return render(
                request,
                "accounts/decrypt.html"
            )

        if not password:

            messages.error(
                request,
                "Please enter the decryption password."
            )

            return render(
                request,
                "accounts/decrypt.html"
            )

        try:

            # ------------------------------------------------
            # FIND THE ORIGINAL FILE RECORD
            # ------------------------------------------------
            
            normalized_name = uploaded_file.name

# Convert spaces and parentheses similarly to stored filename
            normalized_name = normalized_name.replace(" ", "_")
            normalized_name = normalized_name.replace("(", "")
            normalized_name = normalized_name.replace(")", "")

            encrypted_record = EncryptedFile.objects.filter(
    encrypted_file__endswith=normalized_name,
    is_deleted=False
).select_related(
    "owner"
).first()

            # ------------------------------------------------
            # FILE BELONGS TO ANOTHER USER
            # ------------------------------------------------

            if (
                encrypted_record
                and encrypted_record.owner != request.user
            ):

                SecurityLog.objects.create(
                    user=request.user,
                    event="SUSPICIOUS_ACTIVITY",
                    description=(
                        f"Attempted to decrypt encrypted file "
                        f"'{uploaded_file.name}' belonging to "
                        f"user '{encrypted_record.owner.username}'."
                    )
                )
                Notification.objects.create(
    user=encrypted_record.owner,
    title="Suspicious Activity Detected",
    message=(
        f"An unauthorized attempt was made to decrypt "
        f"your encrypted file '{uploaded_file.name}'."
    ),
    notification_type="SECURITY"
)

                try:

                    send_suspicious_activity_email(
                        encrypted_record.owner,
                        request.user,
                        uploaded_file.name
                    )

                except Exception as email_error:

                    print(
                        "SUSPICIOUS ACTIVITY EMAIL ERROR:",
                        email_error
                    )

                messages.error(
                    request,
                    "Unauthorized access detected. "
                    "This encrypted file belongs to another user. "
                    "The attempt has been logged."
                )

                return render(
                    request,
                    "accounts/decrypt.html"
                )

            # ------------------------------------------------
            # FILE NOT FOUND IN DATABASE
            # ------------------------------------------------

            if not encrypted_record:

                messages.error(
                    request,
                    "This encrypted file is not registered "
                    "in SecureCrypt or is no longer available."
                )

                return render(
                    request,
                    "accounts/decrypt.html"
                )

            # ------------------------------------------------
            # EXPIRED FILE CHECK
            # ------------------------------------------------

            if (
                encrypted_record.expires_at
                and encrypted_record.expires_at <= timezone.now()
            ):

                messages.error(
                    request,
                    "This encrypted file has expired and "
                    "can no longer be decrypted."
                )

                return render(
                    request,
                    "accounts/decrypt.html"
                )

            # ------------------------------------------------
            # OWNER VERIFIED → ALLOW DECRYPTION
            # ------------------------------------------------

            encrypted_data = uploaded_file.read()

            decrypted_data = decrypt_file(
                encrypted_data,
                password
            )
            SecurityLog.objects.create(
    user=request.user,
    username=request.user.username,
    event="FILE_DECRYPTED",
    description=(
        f"File '{encrypted_record.original_filename}' "
        "was decrypted successfully."
    )
)

# ==========================================
# NOTIFICATION
# ==========================================

            Notification.objects.create(
    user=request.user,
    title="File Decrypted",
    message=(
        f"Your file '{encrypted_record.original_filename}' "
        "was decrypted successfully."
    ),
    notification_type="FILE"
)
            original_name = (
                encrypted_record.original_filename
            )

            response = HttpResponse(
                decrypted_data,
                content_type="application/octet-stream"
            )

            response["Content-Disposition"] = (
                'attachment; '
                f'filename="{original_name}"'
            )

            return response

        except Exception as e:

            print(
                "DECRYPTION ERROR:",
                e
            )

            messages.error(
                request,
                "Decryption failed. "
                "The password may be incorrect "
                "or the encrypted file may be invalid."
            )

            return render(
                request,
                "accounts/decrypt.html"
            )

    return render(
        request,
        "accounts/decrypt.html"
    )

# ============================================================
# PROFILE
# ============================================================

@login_required
def profile_view(request):

    return render(
        request,
        "accounts/profile.html",
        {
            "user": request.user
        }
    )


# ============================================================
# EDIT PROFILE
# ============================================================

@login_required
def edit_profile_view(request):

    user = request.user

    if request.method == "POST":

        email = request.POST.get(
            "email",
            ""
        ).strip()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        if not email:

            messages.error(
                request,
                "Email cannot be empty."
            )

            return render(
                request,
                "accounts/edit_profile.html"
            )

        if not phone:

            messages.error(
                request,
                "Phone number cannot be empty."
            )

            return render(
                request,
                "accounts/edit_profile.html"
            )

        if CustomUser.objects.filter(
            email=email
        ).exclude(
            id=user.id
        ).exists():

            messages.error(
                request,
                "This email is already registered."
            )

            return render(
                request,
                "accounts/edit_profile.html"
            )

        if CustomUser.objects.filter(
            phone=phone
        ).exclude(
            id=user.id
        ).exists():

            messages.error(
                request,
                "This phone number is already registered."
            )

            return render(
                request,
                "accounts/edit_profile.html"
            )

        user.email = email
        user.phone = phone

        user.save()

        messages.success(
            request,
            "Profile updated successfully."
        )

        return redirect("profile")

    return render(
        request,
        "accounts/edit_profile.html"
    )


# ============================================================
# LOGOUT
# ============================================================

def logout_view(request):

    logout(request)

    messages.success(
        request,
        "You have been logged out successfully."
    )

    return redirect("login")

def reset_password_view(
    request,
    uidb64,
    token
):

    try:

        user_id = force_str(
            urlsafe_base64_decode(uidb64)
        )

        user = CustomUser.objects.get(
            pk=user_id
        )

    except (
        TypeError,
        ValueError,
        OverflowError,
        CustomUser.DoesNotExist
    ):

        user = None


    if (
        user is None
        or not default_token_generator.check_token(
            user,
            token
        )
    ):

        messages.error(
            request,
            "This password reset link is invalid "
            "or has expired."
        )

        return redirect("forgot_password")


    if request.method == "POST":

        new_password = request.POST.get(
            "new_password",
            ""
        )

        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )


        # Passwords must match
        if new_password != confirm_password:

            messages.error(
                request,
                "Passwords do not match."
            )

            return render(
                request,
                "accounts/reset_password.html"
            )


        # Validate Django password rules
        try:

            validate_password(
                new_password,
                user
            )

        except ValidationError as error:

            for message in error.messages:

                messages.error(
                    request,
                    message
                )

            return render(
                request,
                "accounts/reset_password.html"
            )


        # Change password
        user.set_password(
            new_password
        )

        user.save(
            update_fields=["password"]
        )


        # Create security log
        SecurityLog.objects.create(
            user=user,
            event="PASSWORD_CHANGED",
            description=(
                "Password was changed using the "
                "Forgot Password reset link."
            )
        )

        # Create in-app notification
        Notification.objects.create(
    user=user,
    title="Password Changed",
    message=(
        "Your SecureCrypt password was changed successfully."
    ),
    notification_type="PASSWORD"
)
        # Send security notification email
        try:

            send_password_changed_email(
                user
            )

        except Exception as e:

            pass

        messages.success(
            request,
            "Your password has been changed successfully. "
            "You can now log in."
        )

        return redirect("login")


    return render(
        request,
        "accounts/reset_password.html"
    )
def forgot_password_view(request):

    if request.method == "POST":

        email = request.POST.get(
            "email",
            ""
        ).strip()

        user = CustomUser.objects.filter(
            email=email
        ).first()

        # Do not reveal whether an email exists
        messages.success(
            request,
            "If this email is registered, "
            "a password reset link has been sent."
        )

        if user:

            uid = urlsafe_base64_encode(
                force_bytes(user.pk)
            )

            token = default_token_generator.make_token(
                user
            )

            reset_url = request.build_absolute_uri(
                reverse(
                    "reset_password",
                    kwargs={
                        "uidb64": uid,
                        "token": token
                    }
                )
            )

            try:

                send_password_reset_email(
                    user,
                    reset_url
                )

            except Exception as e:

                print(
                    "PASSWORD RESET EMAIL ERROR:",
                    e
                )

        return redirect("forgot_password")

    return render(
        request,
        "accounts/forgot_password.html"
    )