from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    CustomUser, PasswordResetToken, Client, Document, UserAPICall, APIKey,
    AccountDeletionRequest, UserActivityLog, AdminActionLog,
    RefreshToken, AccountDeactivationRequest
)

# Admin config for CustomUser
@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    model = CustomUser
    list_display = ('email', 'client', 'is_staff', 'is_active', 'last_login', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'client', 'subscription_plan')
    search_fields = ('email', 'client__name', 'contact_name', 'contact_phone')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password', 'client_id', 'client_secret_hashed', 'temp_password')}),
        ('Personal Info', {
            'fields': (
                'client', 'contact_name', 'contact_phone', 'contact_email', 'address',
                'industry', 'use_case', 'user_preferences', 'last_document_edited'
            )
        }),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Account Status', {
            'fields': (
                'account_status', 'subscription_plan', 'plan_expiry_date', 'two_factor_enabled', 'notifications_enabled'
            )
        }),
        ('Important Dates', {'fields': ('last_login', 'date_joined', 'last_activity', 'profile_created_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'client', 'is_active', 'is_staff'),
        }),
    )

# Admin config for Client (Organisation)
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', 'created_at')
    search_fields = ('name', 'industry')
    list_filter = ('industry',)
    ordering = ('name',)

# Admin config for Document
@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title',)
    search_fields = ('title',)

# Admin config for UserAPICall
@admin.register(UserAPICall)
class UserAPICallAdmin(admin.ModelAdmin):
    list_display = ('user', 'endpoint', 'timestamp')
    search_fields = ('user__email', 'endpoint')
    list_filter = ('timestamp',)

# Admin config for PasswordResetToken
@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at', 'is_used')
    search_fields = ('user__email', 'token')
    list_filter = ('is_used', 'created_at')

# Admin config for APIKey
@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('user', 'client_id', 'created_at', 'updated_at')
    search_fields = ('user__email', 'client_id')
    list_filter = ('created_at',)

# Admin config for AccountDeletionRequest
@admin.register(AccountDeletionRequest)
class AccountDeletionRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'requested_at', 'is_processed')
    list_filter = ('is_processed',)
    search_fields = ('user__email',)

# Admin config for UserActivityLog
@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'timestamp')
    list_filter = ('event', 'timestamp')
    search_fields = ('user__email',)

# Admin config for AdminActionLog
@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):
    list_display = ('admin_user', 'target_user', 'action', 'timestamp')
    search_fields = ('admin_user__email', 'target_user__email')
    list_filter = ('action', 'timestamp')

# Admin config for RefreshToken
@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'expires_at', 'created_at')
    search_fields = ('user__email', 'token')
    list_filter = ('expires_at', 'created_at')

# Admin config for AccountDeactivationRequest
@admin.register(AccountDeactivationRequest)
class AccountDeactivationRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'requested_at', 'is_processed')
    list_filter = ('is_processed',)
    search_fields = ('user__email',)

