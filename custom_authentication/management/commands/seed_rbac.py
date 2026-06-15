"""
Management command to seed the comprehensive RBAC system.

Creates all granular Permission objects and Group objects (roles)
with their resolved permission sets.

Usage:
    python manage.py seed_rbac
"""

from django.core.management.base import BaseCommand
from custom_authentication.rbac import seed_permissions_and_roles


class Command(BaseCommand):
    help = "Seed RBAC permissions and roles into the database"

    def handle(self, *args, **options):
        self.stdout.write("Seeding RBAC permissions and roles...")
        seed_permissions_and_roles()
        self.stdout.write(self.style.SUCCESS("RBAC seeding complete."))
