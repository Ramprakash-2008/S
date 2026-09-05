from accounts import views
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from accounts.views import (
    admin_user_detail_view,
    deactivate_user_view,
    activate_user_view,
    register_view,
    login_view,
    logout_view,
    dashboard_view,
    encrypt_file_view,
    decrypt_file_view,
    my_files_view,
    download_encrypted_file_view,
    clear_file_history_view,
    profile_view,
    edit_profile_view,
    change_password_view,
    admin_dashboard_view,
    admin_users_view,
    approve_user_view,
    reject_user_view,
    pending_approvals_view,
    admin_file_management_view,
    admin_download_file_view,
    admin_delete_file_view,
    admin_insights_view,
    admin_insights_pdf_view,
    admin_activity_logs_view,
    download_activity_logs,
    admin_security_logs_view,
    admin_lock_user_view,
    unlock_user_view,
    clear_security_logs,
    download_security_logs,
    admin_delete_user_view,
    forgot_password_view,
    reset_password_view,
    settings_view,
    user_security_logs_view,
    notifications,
)



urlpatterns = [

    # =========================================================
    # HOME
    # =========================================================
    path(
    "notifications/",
    views.notifications,
    name="notifications"
),
path(
    "security-logs/",
    views.user_security_logs_view,
    name="security_logs"
),
    path(
    "forgot-password/",
    views.forgot_password_view,
    name="forgot_password"
),
path("settings/", views.settings_view, name="settings"),
path(
    "reset-password/<uidb64>/<token>/",
    views.reset_password_view,
    name="reset_password"
),
    path(
        "",
        RedirectView.as_view(pattern_name="login"),
        name="home"
    ),
    path(
    "admin-users/<int:user_id>/delete/",
    views.admin_delete_user_view,
    name="admin_delete_user"
),
    path(
    "admin-files/<int:file_id>/download/",
    views.admin_download_file_view,
    name="admin_download_file",
),
    path(
    "admin-security-logs/lock/<int:user_id>/",
    admin_lock_user_view,
    name="admin_lock_user"
    ),
path(
    "admin-files/<int:file_id>/delete/",
    views.admin_delete_file_view,
    name="admin_delete_file",
),

    # =========================================================
    # AUTHENTICATION
    # =========================================================

    path(
        "register/",
        register_view,
        name="register"
    ),

    path(
        "login/",
        login_view,
        name="login"
    ),

    path(
        "logout/",
        logout_view,
        name="logout"
    ),

    # =========================================================
    # USER DASHBOARD
    # =========================================================

    path(
        "dashboard/",
        dashboard_view,
        name="dashboard"
    ),
    path(
    "admin-files/",
    admin_file_management_view,
    name="admin_files"
    ),
    # =========================================================
    # PROFILE
    # =========================================================

    path(
        "profile/",
        profile_view,
        name="profile"
    ),

    path(
        "edit-profile/",
        edit_profile_view,
        name="edit_profile"
    ),

    path(
    "admin-insights/",
    admin_insights_view,
    name="admin_insights"
    ),
    path(
        "change-password/",
        change_password_view,
        name="change_password"
    ),

    # =========================================================
    # ENCRYPTION
    # =========================================================

    path(
        "encrypt/",
        encrypt_file_view,
        name="encrypt"
    ),
    path(
    "admin-insights/pdf/",
    admin_insights_pdf_view,
    name="admin_insights_pdf"
    ),
    path(
        "decrypt/",
        decrypt_file_view,
        name="decrypt"
    ),

    # =========================================================
    # FILES
    # =========================================================

    path(
        "my-files/",
        my_files_view,
        name="my_files"
    ),

    path(
        "my-files/clear-history/",
        clear_file_history_view,
        name="clear_file_history"
    ),

    path(
        "download/<int:file_id>/",
        download_encrypted_file_view,
        name="download_encrypted_file"
    ),

    # =========================================================
    # ADMIN DASHBOARD
    # =========================================================

    path(
        "admin-dashboard/",
        admin_dashboard_view,
        name="admin_dashboard"
    ),
    
    path(
    "admin-security-logs/download/",
    views.download_security_logs,
    name="download_security_logs"
    ),
    path(
    "admin-security-logs/clear/",
    clear_security_logs,
    name="clear_security_logs"
),


    path(
    "admin-users/<int:user_id>/unlock/",
    unlock_user_view,
    name="unlock_user"
    ),
    # =========================================================
    # ADMIN USER MANAGEMENT
    # =========================================================
    path(
    "admin-activity-logs/",
    admin_activity_logs_view,
    name="admin_activity_logs"
    ),
    path(
    "download-activity-logs/",
    download_activity_logs,
    name="download_activity_logs"
    ),
    path(
        "admin-users/",
        admin_users_view,
        name="admin_users"
    ),
    path(
    "admin-security-logs/",
    admin_security_logs_view,
    name="admin_security_logs"
    ),
    path(
    "pending-approvals/",
    pending_approvals_view,
    name="pending_approvals"
    ),
    # USER DETAILS
    path(
        "admin-users/<int:user_id>/",
        admin_user_detail_view,
        name="admin_user_detail"
    ),

    # APPROVE
    path(
        "admin-users/<int:user_id>/approve/",
        approve_user_view,
        name="approve_user"
    ),

    # REJECT
    path(
        "admin-users/<int:user_id>/reject/",
        reject_user_view,
        name="reject_user"
    ),

    # ACTIVATE
    path(
        "admin-users/<int:user_id>/activate/",
        activate_user_view,
        name="activate_user"
    ),

    # DEACTIVATE
    path(
        "admin-users/<int:user_id>/deactivate/",
        deactivate_user_view,
        name="deactivate_user"
    ),

    # =========================================================
    # DJANGO ADMIN
    # =========================================================

    path(
        "admin/",
        admin.site.urls
    ),
]


# =============================================================
# MEDIA FILES - DEVELOPMENT ONLY
# =============================================================

if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )