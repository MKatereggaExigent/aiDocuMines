# Testing Guide for 5 Vertical Applications

This guide provides comprehensive instructions for testing all 5 vertical application endpoints on the server.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Getting Your OAuth Token](#getting-your-oauth-token)
3. [Testing Methods](#testing-methods)
4. [API Endpoints Overview](#api-endpoints-overview)
5. [Testing with Python Script](#testing-with-python-script)
6. [Testing with Postman](#testing-with-postman)
7. [Testing with cURL](#testing-with-curl)

---

## 🔧 Prerequisites

- **Server URL**: Your aiDocuMines server URL (e.g., `https://api.yourdomain.com`)
- **OAuth Token**: Valid OAuth2 access token with appropriate scopes
- **Client Association**: Your user must be associated with a client organization

---

## 🔑 Getting Your OAuth Token

### Method 1: Using Django Admin

1. Log in to Django admin: `https://your-server-url.com/admin/`
2. Navigate to **OAuth2 Provider** → **Access Tokens**
3. Create a new token or copy an existing one
4. Make sure the token has `read` and `write` scopes

### Method 2: Using OAuth2 Flow

```bash
# Get authorization code
curl -X POST https://your-server-url.com/o/token/ \
  -d "grant_type=password" \
  -d "username=your_username" \
  -d "password=your_password" \
  -d "client_id=your_client_id" \
  -d "client_secret=your_client_secret"
```

---

## 🧪 Testing Methods

We provide 3 ways to test the endpoints:

1. **Python Script** - Automated testing of all endpoints
2. **Postman Collection** - Interactive API testing
3. **cURL Commands** - Command-line testing

---

## 📊 API Endpoints Overview

### 1. Private Equity - Due Diligence

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/private-equity/due-diligence-runs/` | List all DD runs |
| POST | `/api/v1/private-equity/due-diligence-runs/` | Create new DD run |
| GET | `/api/v1/private-equity/due-diligence-runs/{id}/` | Get DD run details |
| GET | `/api/v1/private-equity/risk-clause-summary/` | Risk clause analytics |
| GET | `/api/v1/private-equity/document-type-summary/` | Document type analytics |
| GET | `/api/v1/private-equity/service-executions/` | Service execution logs |

### 2. Class Actions - Mass Claims

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/class-actions/mass-claims-runs/` | List all mass claims runs |
| POST | `/api/v1/class-actions/mass-claims-runs/` | Create new mass claims run |
| GET | `/api/v1/class-actions/intake-forms/` | List intake forms |
| GET | `/api/v1/class-actions/evidence-documents/` | List evidence documents |
| POST | `/api/v1/class-actions/pii-redaction/` | Trigger PII redaction |
| GET | `/api/v1/class-actions/service-executions/` | Service execution logs |

### 3. Labor & Employment - Workplace Communications

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/labor-employment/communications-runs/` | List communications runs |
| POST | `/api/v1/labor-employment/communications-runs/` | Create new run |
| GET | `/api/v1/labor-employment/message-analysis-summary/` | Message analytics |
| GET | `/api/v1/labor-employment/wage-hour-summary/` | Wage hour analytics |
| GET | `/api/v1/labor-employment/compliance-alert-summary/` | Compliance alerts |
| GET | `/api/v1/labor-employment/service-executions/` | Service execution logs |

### 4. IP Litigation - Patent Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/ip-litigation/analysis-runs/` | List patent analysis runs |
| POST | `/api/v1/ip-litigation/analysis-runs/` | Create new analysis run |
| GET | `/api/v1/ip-litigation/patent-documents/` | List patent documents |
| GET | `/api/v1/ip-litigation/claim-charts/` | List claim charts |
| GET | `/api/v1/ip-litigation/patent-analysis-summary/` | Patent analytics |
| GET | `/api/v1/ip-litigation/service-executions/` | Service execution logs |

### 5. Regulatory Compliance - GDPR/CCPA

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/regulatory-compliance/compliance-runs/` | List compliance runs |
| POST | `/api/v1/regulatory-compliance/compliance-runs/` | Create new run |
| GET | `/api/v1/regulatory-compliance/dsar-requests/` | List DSAR requests |
| GET | `/api/v1/regulatory-compliance/compliance-summary/` | Compliance analytics |
| GET | `/api/v1/regulatory-compliance/alert-summary/` | Alert analytics |
| GET | `/api/v1/regulatory-compliance/service-executions/` | Service execution logs |

---

## 🐍 Testing with Python Script

### 1. Run the automated test script:

```bash
cd ~/Apps/aiDocuMines
python test_vertical_endpoints.py https://your-server-url.com your_oauth_token_here
```

### 2. Expected Output:

```
ℹ Testing vertical endpoints on: https://your-server-url.com
ℹ Using token: abc123...

================================================================================
1. PRIVATE EQUITY - Due Diligence
================================================================================

ℹ Testing: List Due Diligence Runs
  URL: https://your-server-url.com/api/v1/private-equity/due-diligence-runs/
  Method: GET
✓ Status: 200
  Response: [...]

...

================================================================================
TEST RESULTS SUMMARY
================================================================================

Total Tests: 25
✓ Passed: 25
✗ Failed: 0

Success Rate: 100.0%

✓ 🎉 All tests passed!
```

---

## 📮 Testing with Postman

### 1. Import the Collection

1. Open Postman
2. Click **Import**
3. Select `postman_collection_verticals.json`
4. Collection will be imported with all endpoints

### 2. Configure Variables

1. Click on the collection name
2. Go to **Variables** tab
3. Set the following variables:
   - `base_url`: Your server URL (e.g., `https://api.yourdomain.com`)
   - `access_token`: Your OAuth token

### 3. Run Tests

1. Expand any folder (e.g., "1. Private Equity")
2. Click on any request
3. Click **Send**
4. View the response

### 4. Run All Tests

1. Click on the collection name
2. Click **Run**
3. Select all requests
4. Click **Run Collection**

---

## 🔧 Testing with cURL

### Example: List Due Diligence Runs

```bash
curl -X GET \
  https://your-server-url.com/api/v1/private-equity/due-diligence-runs/ \
  -H "Authorization: Bearer your_oauth_token_here" \
  -H "Content-Type: application/json"
```

### Example: Create Due Diligence Run

```bash
curl -X POST \
  https://your-server-url.com/api/v1/private-equity/due-diligence-runs/ \
  -H "Authorization: Bearer your_oauth_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "run_name": "Test DD Run",
    "target_company": "Acme Corp",
    "deal_type": "acquisition",
    "deal_value": 10000000.00
  }'
```

---

## ✅ Expected Responses

### Successful GET Request (200 OK)

```json
[
  {
    "id": 1,
    "run_name": "Test DD Run",
    "target_company": "Acme Corp",
    "created_at": "2024-01-15T10:30:00Z",
    ...
  }
]
```

### Successful POST Request (201 Created)

```json
{
  "id": 2,
  "run_name": "New DD Run",
  "status": "created",
  "message": "Due diligence run created successfully"
}
```

### Empty List (200 OK)

```json
[]
```

This is normal if no data exists yet.

---

## 🚨 Troubleshooting

### 401 Unauthorized

- **Cause**: Invalid or expired OAuth token
- **Solution**: Generate a new token

### 403 Forbidden

- **Cause**: User not associated with a client or insufficient permissions
- **Solution**: Ensure user has a client association and proper roles

### 404 Not Found

- **Cause**: Endpoint URL is incorrect
- **Solution**: Verify the endpoint path matches the documentation

### 500 Internal Server Error

- **Cause**: Server-side error
- **Solution**: Check server logs for details

---

## 📝 Notes

- All endpoints require OAuth2 authentication
- All endpoints are multi-tenant (filtered by client)
- Empty responses (`[]`) are normal if no data exists
- POST requests require valid JSON payloads
- Some endpoints may require specific query parameters

---

## 🎯 Next Steps

After successful testing:

1. ✅ Verify all endpoints return 200/201 status codes
2. ✅ Create test data using POST endpoints
3. ✅ Verify data appears in GET endpoints
4. ✅ Test filtering and query parameters
5. ✅ Test error handling with invalid data

---

**Happy Testing! 🚀**

