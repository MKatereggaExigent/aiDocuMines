#!/bin/bash

docker exec -i aidocumines_web python manage.py shell <<EOF
import json
from django.contrib.auth import get_user_model
from custom_authentication.models import Client
from oauth2_provider.models import Application
from oauth2_provider.generators import generate_client_secret

User = get_user_model()

# Settings
ADMIN_EMAIL = "admin@aidocumines.com"
ADMIN_PASSWORD = "superpassword"

# 1️⃣ Delete all superusers
User.objects.filter(is_superuser=True).delete()

# 2️⃣ Create or get the client (tenant)
client, _ = Client.objects.get_or_create(
    name="AI DocuMines",
    defaults={
        "address": "Admin Address",
        "industry": "AI Research",
        "use_case": "System setup"
    }
)

# 3️⃣ Create new superuser
user = User.objects.create_superuser(
    email=ADMIN_EMAIL,
    password=ADMIN_PASSWORD,
    client=client,
    contact_name="Admin User",
    contact_phone="+27 000 000 000",
    address="Admin Address",
    industry="AI Research",
    use_case="System setup"
)

# 4️⃣ Create OAuth2 password grant app
raw_client_secret = generate_client_secret()
app = Application.objects.create(
    user=user,
    client_type=Application.CLIENT_CONFIDENTIAL,
    authorization_grant_type=Application.GRANT_PASSWORD,
    name="System Admin API Access",
    client_secret=raw_client_secret
)

# 5️⃣ Output credentials as JSON
print(json.dumps({
    "admin_email": ADMIN_EMAIL,
    "admin_password": ADMIN_PASSWORD,
    "client_id": app.client_id,
    "client_secret": raw_client_secret
}, indent=4))
EOF

