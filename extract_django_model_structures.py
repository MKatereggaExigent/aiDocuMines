import os
import json
import importlib.util
import inspect
from django.conf import settings
from django.apps import apps
from django.db import models
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiDocuMines.settings')  # Replace with your project settings
django.setup()

output = {}

for app_config in apps.get_app_configs():
    app_label = app_config.label
    models_dict = {}

    for model in app_config.get_models():
        model_info = {
            "fields": [],
            "relationships": {
                "ForeignKey": [],
                "OneToOneField": [],
                "ManyToManyField": []
            }
        }

        for field in model._meta.get_fields():
            if isinstance(field, models.Field):
                model_info["fields"].append({
                    "name": field.name,
                    "type": field.__class__.__name__
                })

            if isinstance(field, models.ForeignKey):
                model_info["relationships"]["ForeignKey"].append({
                    "field": field.name,
                    "to": field.related_model.__name__
                })

            elif isinstance(field, models.OneToOneField):
                model_info["relationships"]["OneToOneField"].append({
                    "field": field.name,
                    "to": field.related_model.__name__
                })

            elif isinstance(field, models.ManyToManyField):
                model_info["relationships"]["ManyToManyField"].append({
                    "field": field.name,
                    "to": field.related_model.__name__
                })

        models_dict[model.__name__] = model_info

    if models_dict:
        output[app_label] = models_dict

# Save to JSON
with open("django_models_structure.json", "w") as f:
    json.dump(output, f, indent=4)

print("Model structure exported to django_models_structure.json")

