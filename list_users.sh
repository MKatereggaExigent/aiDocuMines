#!/bin/bash

docker exec -i aidocumines_web python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()

for u in User.objects.all():
    print(f"ID: {u.id} | Email: {u.email} | Is Staff: {u.is_staff} | Is Superuser: {u.is_superuser}")
EOF

