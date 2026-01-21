# API Documentation

## Base URL
```
Development: http://localhost:8000
Production: https://api.yourcompany.com
```

## Authentication

All protected endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <access_token>
```

## User Types & Permissions

| User Type | Permissions |
|-----------|------------|
| Super Admin | Full system access, can manage all users and view all data |
| Enterprise | Can create sub-users, view own dashboard, manage own data |
| Individual | Can only manage own wallet and view own activities |
| Sub-user | Limited access under parent enterprise |

## API Endpoints Reference

### 1. Authentication

#### Register User
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe",
  "user_type": "individual"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "user_id": "IND-00001",
  "email": "john@example.com",
  "full_name": "John Doe",
  "user_type": "individual",
  "is_active": true,
  "is_blocked": false,
  "created_at": "2025-01-06T10:00:00Z"
}
```

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "SecurePass123!"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Refresh Token
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Get Current User
```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

### 2. User Management

#### List All Users (Super Admin)
```http
GET /api/v1/users/?page=1&page_size=20&user_type=enterprise&is_active=true
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `page` (integer, default: 1)
- `page_size` (integer, default: 20, max: 100)
- `user_type` (optional): super_admin, enterprise, individual, sub_user
- `is_active` (optional boolean)

#### Get User Details
```http
GET /api/v1/users/1
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": 1,
  "user_id": "JA1001",
  "email": "enterprise@example.com",
  "full_name": "Enterprise User",
  "user_type": "enterprise",
  "enterprise_id": "JA1001",
  "is_active": true,
  "is_blocked": false,
  "wallet_balance": 1500.00,
  "created_at": "2025-01-06T10:00:00Z"
}
```

#### Update User (Super Admin)
```http
PATCH /api/v1/users/1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "full_name": "Updated Name",
  "is_active": false
}
```

#### Block/Unblock User (Super Admin)
```http
POST /api/v1/users/1/block
Authorization: Bearer <access_token>

POST /api/v1/users/1/unblock
Authorization: Bearer <access_token>
```

#### Create Sub-user (Enterprise)
```http
POST /api/v1/users/enterprise/sub-user
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "email": "subuser@example.com",
  "password": "SecurePass123!",
  "full_name": "Sub User",
  "enterprise_id": "JA1001"
}
```

**Response:**
```json
{
  "id": 5,
  "user_id": "JA1001-01",
  "email": "subuser@example.com",
  "full_name": "Sub User",
  "user_type": "sub_user",
  "enterprise_id": "JA1001",
  "parent_user_id": 1
}
```

#### List Sub-users
```http
GET /api/v1/users/enterprise/JA1001/sub-users?page=1&page_size=20
Authorization: Bearer <access_token>
```

### 3. Wallet Management

#### Get My Wallet
```http
GET /api/v1/wallet/
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "balance": 1500.00,
  "created_at": "2025-01-06T10:00:00Z",
  "updated_at": "2025-01-06T15:30:00Z"
}
```

#### Top-up Wallet
```http
POST /api/v1/wallet/topup
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "amount": 500.00
}
```

**Response:**
```json
{
  "id": 123,
  "transaction_id": "TXN-ABC123DEF456",
  "user_id": 1,
  "transaction_type": "credit",
  "purpose": "wallet_topup",
  "amount": 500.00,
  "balance_before": 1500.00,
  "balance_after": 2000.00,
  "description": "Wallet top-up by IND-00001",
  "created_at": "2025-01-06T16:00:00Z"
}
```

#### Get Transaction History
```http
GET /api/v1/wallet/transactions/my?page=1&page_size=20
Authorization: Bearer <access_token>
```

#### Top-up User Wallet (Super Admin)
```http
POST /api/v1/wallet/1/topup
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "amount": 1000.00
}
```

### 4. Activity Tracking

#### Record Activity
```http
POST /api/v1/activities/record
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "user_id": 1,
  "activity_type": "report_generated",
  "cost": 10.00
}
```

**Activity Types:**
- `report_generated` - Cost: $10.00 (configurable)
- `form_downloaded` - Cost: $5.00 (configurable)

**Response:**
```json
{
  "id": 456,
  "user_id": 1,
  "activity_type": "report_generated",
  "activity_count": 1,
  "cost": 10.00,
  "created_at": "2025-01-06T16:30:00Z"
}
```

#### Get My Activities
```http
GET /api/v1/activities/my?page=1&page_size=20&activity_type=report_generated
Authorization: Bearer <access_token>
```

#### Get Activity Statistics
```http
GET /api/v1/activities/stats/1?start_date=2025-01-01&end_date=2025-01-31
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "report_generated": {
    "count": 150,
    "total_cost": 1500.00
  },
  "form_downloaded": {
    "count": 75,
    "total_cost": 375.00
  }
}
```

#### Get Enterprise Activity Summary
```http
GET /api/v1/activities/enterprise/JA1001/summary?start_date=2025-01-01
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "total_reports": 250,
  "total_forms": 120,
  "total_cost": 3100.00,
  "sub_users_count": 5
}
```

### 5. Dashboard (Super Admin)

#### Get Dashboard Statistics
```http
GET /api/v1/dashboard/stats?start_date=2025-01-01&end_date=2025-01-31
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "total_users": 150,
  "total_enterprise_users": 25,
  "total_individual_users": 100,
  "total_sub_users": 25,
  "total_reports_generated": 5000,
  "total_forms_downloaded": 2500,
  "total_revenue": 75000.00
}
```

#### Get Enterprise Users Summary
```http
GET /api/v1/dashboard/enterprise-users?page=1&page_size=20
Authorization: Bearer <access_token>
```

**Response:**
```json
[
  {
    "user_id": "JA1001",
    "enterprise_id": "JA1001",
    "full_name": "Tech Corp",
    "email": "contact@techcorp.com",
    "sub_user_count": 5,
    "reports_generated": 250,
    "forms_downloaded": 120,
    "wallet_balance": 5000.00,
    "is_active": true,
    "is_blocked": false,
    "created_at": "2025-01-01T10:00:00Z"
  }
]
```

#### Get Revenue Statistics
```http
GET /api/v1/dashboard/revenue?period=monthly&start_date=2025-01-01
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `period`: daily, monthly, yearly

**Response:**
```json
[
  {
    "period": "2025-01",
    "revenue": 25000.00,
    "transaction_count": 150
  },
  {
    "period": "2024-12",
    "revenue": 20000.00,
    "transaction_count": 120
  }
]
```

#### Get User Growth Statistics
```http
GET /api/v1/dashboard/user-growth?period_days=30
Authorization: Bearer <access_token>
```

#### Get Top Active Users
```http
GET /api/v1/dashboard/top-active-users?limit=10&activity_type=report_generated
Authorization: Bearer <access_token>
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid input data",
  "message": "Validation error"
}
```

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Access denied. Super Admin privileges required."
}
```

### 404 Not Found
```json
{
  "detail": "User not found"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "message": "Internal server error",
  "detail": "An unexpected error occurred"
}
```

## Rate Limiting

- Default: 60 requests per minute per IP
- Burst: 1000 requests per hour
- Response header: `X-RateLimit-Remaining`

When rate limit exceeded:
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

## Pagination

All list endpoints support pagination:

**Request:**
```
GET /api/v1/users/?page=2&page_size=50
```

**Response Headers:**
```
X-Total-Count: 150
X-Page: 2
X-Page-Size: 50
```

## Date Formats

All dates use ISO 8601 format:
```
2025-01-06T16:30:00Z
```

## Webhooks (Future)

Webhook events will be sent for:
- User registration
- Wallet top-up
- Activity recorded
- Threshold alerts

## SDK & Libraries

Coming soon:
- Python SDK
- JavaScript SDK
- Postman Collection
