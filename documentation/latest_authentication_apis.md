
#### SIGNUP

#####Request

```
curl -X 'POST' \
  'http://localhost:8020/api/v1/auth/signup/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "john_doe",
    "email": "john_doe@aidocumines.com",
    "password": "SecurePass#456",
    "organisation": "AI DocuMines User",
    "contact_name": "John Doe",
    "contact_phone": "+27 444 555 666",
    "contact_email": "john_doe@aidocumines.com",
    "address": "456 Doe Street, Cape Town",
    "industry": "AI Research",
    "use_case": "Testing user management and admin privileges."
  }'
```
#####Response
```
{"message":"User registered successfully","user_id":2,"organisation":"AI DocuMines User","contact_name":"John Doe","contact_phone":"+27 444 555 666","industry":"AI Research","use_case":"Testing user management and admin privileges.","client_id":"0sTxkNaAwCRiG4kl1QrhGTuYL9PspG7ziGy5vzBo","client_secret":"cV990IV3S32i8gPGHIaJH727MeNlNlA69fzHVVxzp0ZBI2lsV3UziMZjKtQW6N5WqSgPYXblLh4NMPOJe7XS7LrIDq1iw6IPWZ0mMjW6EY74IQCvxcN6mSHr8YF5J6TS","profile_created_at":"2025-03-07T03:34:18.305185Z","last_login":null,"last_activity":null,"total_time_logged_in":"N/A","total_api_calls_made":0,"account_status":"active","total_files_uploaded":0,"subscription_plan":"premium","plan_expiry_date":"2025-06-06T00:00:00Z","2fa_enabled":false,"roles":[],"last_document_edited":"document_12345.pdf","user_preferences":{"theme":"light","language":"en"},"notifications_enabled":true}
```

#### LOGIN

##### Request
```
curl -X 'POST' \
  'http://localhost:8020/api/v1/auth/login/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-Client-ID: 0sTxkNaAwCRiG4kl1QrhGTuYL9PspG7ziGy5vzBo' \
  -H 'X-Client-Secret: cV990IV3S32i8gPGHIaJH727MeNlNlA69fzHVVxzp0ZBI2lsV3UziMZjKtQW6N5WqSgPYXblLh4NMPOJe7XS7LrIDq1iw6IPWZ0mMjW6EY74IQCvxcN6mSHr8YF5J6TS' \
  -d '{
    "email": "john_doe@aidocumines.com",
    "password": "SecurePass#456"
  }'
```
#####Response
```
{"access_token":"O3hznbqTVVQ7WtFISN3u54NdHIPpt6","expires":"2025-03-08 03:41:37"}
```

#### FETCH USER PROFILE

##### Request
```
curl -X 'GET' \
  'http://localhost:8020/api/v1/auth/profile/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer O3hznbqTVVQ7WtFISN3u54NdHIPpt6' \
  -H 'X-Client-ID: 0sTxkNaAwCRiG4kl1QrhGTuYL9PspG7ziGy5vzBo' \
  -H 'X-Client-Secret: cV990IV3S32i8gPGHIaJH727MeNlNlA69fzHVVxzp0ZBI2lsV3UziMZjKtQW6N5WqSgPYXblLh4NMPOJe7XS7LrIDq1iw6IPWZ0mMjW6EY74IQCvxcN6mSHr8YF5J6TS'
```
#####Response
```
{"email":"john_doe@aidocumines.com","organisation":"AI DocuMines User","contact_name":"John Doe","contact_phone":"+27 444 555 666","address":"456 Doe Street, Cape Town","industry":"AI Research","use_case":"Testing user management and admin privileges."}
```
#### UPDATE USER PROFILE

#####Request
```
curl -X 'PUT' \
  'http://localhost:8020/api/v1/auth/profile/update/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer O3hznbqTVVQ7WtFISN3u54NdHIPpt6' \
  -H 'Content-Type: application/json' \
  -H 'X-Client-ID: 0sTxkNaAwCRiG4kl1QrhGTuYL9PspG7ziGy5vzBo' \
  -H 'X-Client-Secret: cV990IV3S32i8gPGHIaJH727MeNlNlA69fzHVVxzp0ZBI2lsV3UziMZjKtQW6N5WqSgPYXblLh4NMPOJe7XS7LrIDq1iw6IPWZ0mMjW6EY74IQCvxcN6mSHr8YF5J6TS' \
  -d '{
    "contact_name": "John Updated",
    "contact_phone": "+27 444 555 777",
    "address": "789 Updated Street, Cape Town"
  }'
```
#####Response
```
{"message":"Profile updated successfully"}
```

#### PASSWORD RESET
#####Request
```
curl -X 'POST' \
  'http://localhost:8020/api/v1/auth/password/reset/request/' \
  -H 'accept: application/json' \
  -H 'X-Client-ID: DdFJAfpXgZnZ85MtFVL8KxUX1DrhgP5tr0OpisZj' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "john_doe@aidocumines.com"
  }'
```
#####Response
```
{"message":"Password reset token sent to your email","reset_token":"57dce062-4a15-42ef-a61e-c0fdaefac56a"}
```
#### MATCH USER TOKEN WITH SYSTEM TOKEN TO COMPLETE PASSWORD RESET
#####Request
```
curl -X 'POST' \
  'http://localhost:8020/api/v1/auth/password/reset/' \
  -H 'accept: application/json' \
  -H 'X-Client-ID: DdFJAfpXgZnZ85MtFVL8KxUX1DrhgP5tr0OpisZj' \
  -H 'Content-Type: application/json' \
  -d '{
    "token": "57dce062-4a15-42ef-a61e-c0fdaefac56a",
    "new_password": "NewSecurePass#789"
  }'
```
#####Response
```
{"message":"Password reset successful"}
```
#### LOGGING IN WITH NEW PASSWORD GENERATES A NEW TOKEN

#####Request
```
curl -X 'POST' \
  'http://localhost:8020/api/v1/auth/login/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-Client-ID: 0sTxkNaAwCRiG4kl1QrhGTuYL9PspG7ziGy5vzBo' \
  -H 'X-Client-Secret: cV990IV3S32i8gPGHIaJH727MeNlNlA69fzHVVxzp0ZBI2lsV3UziMZjKtQW6N5WqSgPYXblLh4NMPOJe7XS7LrIDq1iw6IPWZ0mMjW6EY74IQCvxcN6mSHr8YF5J6TS' \
  -d '{
    "email": "john_doe@aidocumines.com",
    "password": "NewSecurePass#789"
  }'
```
#####Response
```
{"access_token":"SQz7Qmcm914O4kOrNdJNEXGz1C4vZt","expires":"2025-03-08 04:30:16"}
```

#### TOKEN REFRESH

#####Request
```
curl -X 'POST' \
  'http://localhost:8020/api/v1/auth/refresh-token/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-Client-ID: 0sTxkNaAwCRiG4kl1QrhGTuYL9PspG7ziGy5vzBo' \
  -H 'X-Client-Secret: cV990IV3S32i8gPGHIaJH727MeNlNlA69fzHVVxzp0ZBI2lsV3UziMZjKtQW6N5WqSgPYXblLh4NMPOJe7XS7LrIDq1iw6IPWZ0mMjW6EY74IQCvxcN6mSHr8YF5J6TS' \
  -d '{
    "refresh_token": "S4bXPJpLHtZDkFfTBmCFpgDaMEkDVX"
  }'
```
#####Response
```
{"access_token":"UTCnoZQLYHPHzMcKcEnJdFp41jqWXU","expires":"2025-03-08 06:08:22"}
```