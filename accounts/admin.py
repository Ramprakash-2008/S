from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from .models import AdminActivityLog
from .models import SecurityLog
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):

    list_display = (
        'username',
        'email',
        'phone',
        'status',
        'is_active',
        'is_staff',
    )

    list_filter = (
        'status',
        'is_active',
        'is_staff',
    )

    search_fields = (
        'username',
        'email',
        'phone',
    )

    actions = [
        'approve_users',
        'reject_users',
    ]

    @admin.action(description='Approve selected users')
    def approve_users(self, request, queryset):
        updated = queryset.update(
            status='APPROVED',
            is_active=True
        )

        self.message_user(
            request,
            f'{updated} user(s) approved successfully.'
        )

    @admin.action(description='Reject selected users')
    def reject_users(self, request, queryset):
        updated = queryset.update(
            status='REJECTED',
            is_active=False
        )

        self.message_user(
            request,
            f'{updated} user(s) rejected successfully.'
        )

@admin.register(AdminActivityLog)
class AdminActivityLogAdmin(admin.ModelAdmin):

    list_display = (
        "admin",
        "action",
        "target",
        "created_at",
    )

    list_filter = (
        "action",
        "created_at",
    )

    search_fields = (
        "admin__username",
        "target",
    )

    ordering = (
        "-created_at",
    )
@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):

    list_display = (
        "username",
        "event",
        "description",
        "created_at",
    )

    list_filter = (
        "event",
        "created_at",
    )

    search_fields = (
        "username",
        "description",
    )

    ordering = (
        "-created_at",
    )