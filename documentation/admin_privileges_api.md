#Admin Privileges API Documentation

This documentation outlines the endpoints and usage examples for managing users and their privileges in the Admin API.
Base URL

#### Fetch Super Admin Credentials or Create if does not exist
#####Request
```
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/admin/users/create/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "admin@aidocumines.com",
    "password": "AdminSecure#789",
    "organisation": "AI DocuMines",
    "contact_name": "John Doe",
    "contact_phone": "+27 555 666 777",
    "address": "456 Doe Street, Cape Town",
    "industry": "AI Research",
    "use_case": "Admin user creation for initial setup."
  }'
```
#####Response
```
{"error":"Admin account already exists. Authentication required.","email":"admin@aidocumines.com","password":"superpassword","client_id":"VEBvGSRH6ZBhSyDNXWzRqMtEX2S12R61DK29JJ3Y","client_secret":"UfU5sZzS7uD53mtq71gThbH4TVMkpSW3SeCHQDlbDNS9lOrqY5FNwSfsQ5SwzqSLtwujARciaxUbxdUeYAEDB8JxcjRehpUH41isNKiXIfBSKxHVz5B2RTkJhyQDeos8"}
```
#### Login Super Admin User
#####Request
```
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/login/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-Client-ID: VEBvGSRH6ZBhSyDNXWzRqMtEX2S12R61DK29JJ3Y' \
  -H 'X-Client-Secret: UfU5sZzS7uD53mtq71gThbH4TVMkpSW3SeCHQDlbDNS9lOrqY5FNwSfsQ5SwzqSLtwujARciaxUbxdUeYAEDB8JxcjRehpUH41isNKiXIfBSKxHVz5B2RTkJhyQDeos8' \
  -d '{
    "email": "admin@aidocumines.com",
    "password": "superpassword"
  }'
```
#####Response
```
{"access_token":"o66tDDsNq4EpVYvYT6bGOjRUkaox9M","expires":"2025-03-09 05:08:56"}
``` 

#### Fetches a list of all users.

#####Request
```
curl -X 'GET' \
  'http://localhost:8000/api/v1/auth/admin/users/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer o66tDDsNq4EpVYvYT6bGOjRUkaox9M'
```
#####Response
```
[{"id":1,"email":"admin@aidocumines.com","organisation":"AI DocuMines","is_active":true},{"id":4,"email":"testuser@neworg.com","organisation":"New AI Startups","is_active":true},{"id":5,"email":"freshuser@aiworld.com","organisation":"AI Global Solutions","is_active":true},{"id":6,"email":"uniquetestuser@nextgenai.com","organisation":"NextGen AI Innovations","is_active":true},{"id":7,"email":"brandnewuser@futureai.com","organisation":"Future AI Technologies","is_active":true}]
```


#### Promote User to Admin

##### Request

``` 
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/admin/users/promote/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer o66tDDsNq4EpVYvYT6bGOjRUkaox9M' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": 4
  }'
```
#####Response
```
{"message":"User testuser@neworg.com has been promoted to admin"}
``` 
#### Retrieve a User
#####Request
```
curl -X 'GET' \
  'http://localhost:8000/api/v1/auth/admin/users/7/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer o66tDDsNq4EpVYvYT6bGOjRUkaox9M'
```
#####Response
```
{"id":7,"email":"brandnewuser@futureai.com","organisation":"Future AI Technologies","is_active":true,"is_superuser":true,"created_at":"2025-03-08T06:07:33.520796Z"}
```

Response:

```
{
  "message": "User james_brown@aidocumines.com has been promoted to admin"
}

```

#### Disable User Account

#####Request

```
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/admin/users/disable/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer o66tDDsNq4EpVYvYT6bGOjRUkaox9M' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": 7
  }'
```
#####Response
```
{"message":"User account disabled successfully"}
```

#### Deactivate an Account
#####Request
```
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/account/deactivate/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer o66tDDsNq4EpVYvYT6bGOjRUkaox9M' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": 7
  }'
```
#####Response
```
{"message":"Account deactivated successfully"}
```

#### Reactivate/Activate a User
#####Request
```
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/admin/users/enable-user/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer o66tDDsNq4EpVYvYT6bGOjRUkaox9M' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": 7
  }'
```
#####Response
```
{"message":"User account enabled successfully"}
```
#### Retrieve Logged In User Credentials
#####Request
```
curl -X 'GET' \
  'http://localhost:8000/api/v1/auth/api-keys/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer o66tDDsNq4EpVYvYT6bGOjRUkaox9M'
```
#####Response
```
{"applications":[{"client_id":"i3lZzYQxetoBW42MobpnEzNIoOm3ooOZN4AMqVdi","created":"2025-03-08T05:07:35.978404Z","updated":"2025-03-08T05:07:35.978434Z"},{"client_id":"VEBvGSRH6ZBhSyDNXWzRqMtEX2S12R61DK29JJ3Y","created":"2025-03-08T05:07:36.191536Z","updated":"2025-03-08T05:07:36.191543Z"}]}
```
#### Enable a Deactivated User
#####Request
```
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/admin/users/enable-user/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer o66tDDsNq4EpVYvYT6bGOjRUkaox9M' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": 8
  }'
```
#####Response
```
{"message":"User account enabled successfully"}
```

#### Reset User Password
#####Request

```
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/admin/users/reset-password/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer o66tDDsNq4EpVYvYT6bGOjRUkaox9M' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": 8,
    "new_password": "SecureNewPass#456"
  }'
```
#####Response
```
{"message":"User password reset successfully"}
```

#### Revoke API Key
#####Request
```
curl -X 'DELETE' \
  'http://localhost:8000/api/v1/auth/api-keys/revoke/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer o66tDDsNq4EpVYvYT6bGOjRUkaox9M' \
  -H 'Content-Type: application/json' \
  -d '{
    "client_id": "AJMT0TfolY1ovCLrpkS25PMNUVCVEp7kLwuebjJs"
  }'
```
#####Response
```
{"message":"API key revoked successfully"}
```

#### Fetch Users OAUTH2 Credentials
#####Request
```
curl -X 'GET' \
  'http://localhost:8000/api/v1/auth/admin/users/8/oauth-credentials/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer o66tDDsNq4EpVYvYT6bGOjRUkaox9M'
```
#####Response
```
{"error":"No OAuth credentials found for this user"}
```

#### Delete User Account
##### Request
```
 curl -X 'DELETE' \
  'http://localhost:8000/api/v1/auth/account/delete-account/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer o66tDDsNq4EpVYvYT6bGOjRUkaox9M' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": 4
  }'
```
##### Response
```
{"message":"Account deleted successfully"}
```


#### Create a User 
##### Request
```
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/admin/create-user/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer 5PsyKCmyP3ds5ohg23OdxFR7HdhlIg' \
  -d '{
    "email": "alice.brown@guestai.com",
    "organisation": "AI Guest Research",
    "contact_name": "Alice Brown",
    "contact_phone": "+27 777 111 222",
    "contact_email": "alice.brown@guestai.com",
    "address": "101 AI Lane, Cape Town",
    "industry": "AI Research",
    "use_case": "Exploring AI trends",
    "role": "Guest"
  }'
```
##### Respond
```
{"message":"User created successfully","user_id":2,"email":"alice.brown@guestai.com","temporary_password":"97a6af4c9acc","organisation":"AI Guest Research","role":"Guest","client_id":"0RtLU8RKSYMHo5zIws39MCkzv7Ez3F5Tge4gzE1u","client_secret":"Kw6DikxhICA51ln7Sb8uZFBC9ZP51AeOBjSkvDjUO95VwndDEzzCs48nsTpwhzGDw8vseQOVmiFVZrNmv4KMdGr1k5Fm7hQOUelpvAIlTEq2UkVXIUG4LMXUGHFGreMU"}
```

#### View User Activity Logs

##### Request

```
curl -X 'GET' \
  'http://localhost:8000/api/v1/auth/admin/users/2/activity/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer 5PsyKCmyP3ds5ohg23OdxFR7HdhlIg'
```
#####Response
```
[{"user":2,"event":"LOGIN","timestamp":"2025-03-08T06:22:20.660534-06:00","metadata":{"ip":"127.0.0.1"}},{"user":2,"event":"LOGIN","timestamp":"2025-03-08T06:21:29.532549-06:00","metadata":{"ip":"127.0.0.1"}}]%
```

Response:

```
[
  {
    "event": "LOGIN",
    "timestamp": "2025-03-06T12:34:56Z",
    "metadata": {}
  },
  {
    "event": "PASSWORD_RESET",
    "timestamp": "2025-03-06T13:00:00Z",
    "metadata": {}
  }
]
```

8. View Admin Action Logs

#### Endpoint:

##### GET /admin-action-logs/

Description:

Fetches a list of admin actions.

Request:

```
curl -X 'GET' \
  'http://localhost:8000/api/v1/auth/admin/admin-action-logs/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <your_token>'
```

Response:

```
[
  {
    "admin_user": "john_doe@aidocumines.com",
    "target_user": "james_brown@aidocumines.com",
    "action": "DISABLE_ACCOUNT",
    "timestamp": "2025-03-06T14:00:00Z",
    "details": "User account disabled for inactivity"
  }
]
```

Notes:

    Authorization: All admin actions require an access token in the Authorization header in the format Bearer <your_token>.
    User ID: Ensure to replace user_id in the request bodies with the actual user ID.