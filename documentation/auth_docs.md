# API Authentication Guide

This document explains how to use the authentication endpoints of the API using `curl`. These endpoints allow users to sign up, log in, log out, and reset their passwords.

## 1. Signup

To create a new user account, use the following `curl` command:

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/signup/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "michaelk",
    "email": "michaelk@aims.ac.za",
    "password": "Micho#25",
    "organisation": "AI DocuMines",
    "contact_name": "Michael Kateregga",
    "contact_phone": "+27 123 456 789",
    "contact_email": "support@aidocumines.com",
    "address": "123 AI Street, Cape Town",
    "industry": "Document Processing",
    "use_case": "We need this API to process and analyze scanned documents."
  }'
```

### Response Example
```json
{
  "message":"User registered successfully",
  "organisation":"AI DocuMines",
  "contact_name":"Michael Kateregga",
  "contact_phone":"+27 123 456 789",
  "industry":"Document Processing",
  "use_case":"We need this API to process and analyze scanned documents.",
  "client_id":"DdFJAfpXgZnZ85MtFVL8KxUX1DrhgP5tr0OpisZj",
  "client_secret":"GBLxD1xG7OrBsjDOzzJojmkzXdALFRowF0kR6iSBgi2UP5VGiDtuvDaOuIZVuvg1xDYJlP0Q6F1ZA9bPhDmHq11FydNptavMSbACYMrobh1P0fLwY672fEawqYultWZm"
}
```

## 2. Login

To log in and receive an access token, use the following command:

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/login/' \
  -H 'accept: application/json' \
  -H 'X-Client-ID: DdFJAfpXgZnZ85MtFVL8KxUX1DrhgP5tr0OpisZj' \
  -H 'X-Client-Secret: GBLxD1xG7OrBsjDOzzJojmkzXdALFRowF0kR6iSBgi2UP5VGiDtuvDaOuIZVuvg1xDYJlP0Q6F1ZA9bPhDmHq11FydNptavMSbACYMrobh1P0fLwY672fEawqYultWZm' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "michaelk@aims.ac.za",
    "password": "Micho#25"
  }'
```

### Response Example
```json
{
  "access_token":"tvyGxXW477cxnwqUu3AGwKAbJA2eWv",
  "expires":"2025-03-07 08:35:21"
}
```

## 3. Logout

To log out and invalidate the access token, use the following command:

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/logout/' \
  -H 'accept: application/json' \
  -H 'X-Client-ID: DdFJAfpXgZnZ85MtFVL8KxUX1DrhgP5tr0OpisZj' \
  -H 'Authorization: Bearer tvyGxXW477cxnwqUu3AGwKAbJA2eWv' \
  -H 'Content-Type: application/json'
```

### Response Example
```json
{
  "message":"Logged out successfully"
}
```

## 4. Request Password Reset

To request a password reset token, use the following command:

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/password/reset/request/' \
  -H 'accept: application/json' \
  -H 'X-Client-ID: DdFJAfpXgZnZ85MtFVL8KxUX1DrhgP5tr0OpisZj' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "michaelk@aims.ac.za"
  }'
```

### Response Example
```json
{
  "message":"Password reset token sent to your email",
  "reset_token":"751a96f3-a7c8-4c5f-bc14-8940aef67296"
}
```

## 5. Reset Password

To reset the password using the received reset token, use the following command:

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/password/reset/' \
  -H 'accept: application/json' \
  -H 'X-Client-ID: DdFJAfpXgZnZ85MtFVL8KxUX1DrhgP5tr0OpisZj' \
  -H 'Content-Type: application/json' \
  -d '{
    "token": "751a96f3-a7c8-4c5f-bc14-8940aef67296",
    "new_password": "NewSecure#Pass123"
  }'
```

### Response Example
```json
{
  "message":"Password reset successful"
}
```

## 6. Login with New Password

After resetting the password, use the new password to log in:

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/login/' \
  -H 'accept: application/json' \
  -H 'X-Client-ID: DdFJAfpXgZnZ85MtFVL8KxUX1DrhgP5tr0OpisZj' \
  -H 'X-Client-Secret: GBLxD1xG7OrBsjDOzzJojmkzXdALFRowF0kR6iSBgi2UP5VGiDtuvDaOuIZVuvg1xDYJlP0Q6F1ZA9bPhDmHq11FydNptavMSbACYMrobh1P0fLwY672fEawqYultWZm' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "michaelk@aims.ac.za",
    "password": "NewSecure#Pass123"
  }'
```

### Response Example
```json
{
  "access_token":"DAQrje70CMZHRFlsjV5mwMilFM1nVO",
  "expires":"2025-03-07 08:42:34"
}
```

---

This guide provides all the necessary commands to integrate authentication into your frontend application. Use the provided `client_id` and `client_secret` when making requests to authenticate users and manage sessions securely.

