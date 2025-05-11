# management/commands/export_permissions.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
import csv

class Command(BaseCommand):
    help = 'Exports all permissions to CSV'

    def handle(self, *args, **kwargs):
        with open('all_permissions.csv', 'w', newline='') as csvfile:
            fieldnames = ['app_label', 'model', 'codename', 'name']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for perm in Permission.objects.all():
                writer.writerow({
                    'app_label': perm.content_type.app_label,
                    'model': perm.content_type.model,
                    'codename': perm.codename,
                    'name': perm.name
                })
        self.stdout.write(self.style.SUCCESS('Exported permissions to all_permissions.csv'))

