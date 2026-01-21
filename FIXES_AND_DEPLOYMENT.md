# RapidReportz Admin Panel - Fixed Version
## Critical Fixes Applied

### 🔧 Issues Fixed

#### 1. **Alembic Migration Error** (Critical)
**Problem:** The alembic `env.py` file was importing from `app.db.base` which doesn't exist, causing 500 errors on startup.

**Fixed:**
- Updated `/app/alembic/env.py` to import from correct paths:
  - Changed `from app.core.config import settings` → `from core.config import settings`
  - Changed `from app.db.base import Base` → `from core.database import Base`
- Added all model imports to ensure they're registered with SQLAlchemy Base
- Added Railway postgres URL fix (postgres:// → postgresql://)

#### 2. **Missing Payment Models** (Critical)
**Problem:** `payment.py` route was importing `Invoice`, `Subscription`, and `SubscriptionPlan` models that didn't exist.

**Fixed:**
- Added three new models to `models/models.py`:
  - `Invoice` - for payment invoices
  - `Subscription` - for subscription management
  - `SubscriptionPlan` - enum for subscription types (starter, professional, enterprise)
- Updated `main.py` to import these models so they're registered with SQLAlchemy

#### 3. **SQLAlchemy 2.0 Compatibility** (Important)
**Problem:** Raw SQL execution without `text()` wrapper causing warnings/errors.

**Fixed:**
- Updated health check endpoint to use `text()` wrapper: `db.execute(text("SELECT 1"))`
- Database connection already uses `text()` in `database.py`

---

## 📁 Project Structure

```
admin_panel_backend-main/
├── app/
│   ├── alembic/              # Database migrations (FIXED)
│   │   └── env.py            # ✅ Fixed import paths
│   ├── api/
│   │   ├── routes/
│   │   │   ├── auth.py       # Authentication
│   │   │   ├── users.py      # User management
│   │   │   ├── wallet.py     # Wallet operations
│   │   │   ├── payment.py    # Billplz payment gateway
│   │   │   ├── templates.py  # Template management
│   │   │   ├── tickets.py    # Support tickets
│   │   │   ├── activities.py # Activity tracking
│   │   │   └── dashboard.py  # Dashboard analytics
│   │   └── deps.py           # Dependencies
│   ├── core/
│   │   ├── config.py         # Configuration
│   │   ├── database.py       # Database connection
│   │   ├── security.py       # JWT & password hashing
│   │   └── cache.py          # Redis cache
│   ├── models/
│   │   ├── models.py         # ✅ Added Invoice, Subscription, SubscriptionPlan
│   │   ├── user.py           # User model
│   │   ├── wallet.py         # Wallet model
│   │   ├── activity.py       # Activity model
│   │   ├── ticket.py         # Ticket model
│   │   └── template.py       # Template model
│   ├── schemas/
│   │   └── schemas.py        # Pydantic schemas
│   ├── services/
│   │   ├── user_service.py
│   │   ├── wallet_service.py
│   │   └── email_service.py
│   ├── main.py               # ✅ Fixed health check & model imports
│   ├── startup.sh            # Startup script
│   └── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 🚀 Deployment to Railway

### Prerequisites
1. Railway account
2. PostgreSQL database provisioned on Railway
3. Redis instance (optional but recommended)

### Step 1: Environment Variables
Add these to your Railway service:

```bash
# Database (Railway provides this automatically)
DATABASE_URL=postgresql://user:password@host:port/database

# JWT Security
SECRET_KEY=your-super-secret-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# Application
PROJECT_NAME=RapidReportz Admin Panel
VERSION=2.0.0
ENVIRONMENT=production

# CORS
ALLOWED_ORIGINS=https://your-frontend-domain.com,https://app.rapidreportz.com

# Payment Gateway (Billplz Malaysia)
BILLPLZ_API_KEY=your-billplz-api-key
BILLPLZ_COLLECTION_ID=your-collection-id
BILLPLZ_X_SIGNATURE=your-x-signature-key
BILLPLZ_CALLBACK_URL=https://your-backend-url/api/payment/webhook/billplz

# Email (Optional - for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@rapidreportz.com
FROM_NAME=RapidReportz

# Redis (Optional - for caching)
REDIS_URL=redis://default:password@host:port
```

### Step 2: Deploy to Railway

**Option A: Using Railway CLI**
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Deploy
railway up
```

**Option B: Using GitHub (Recommended)**
1. Push your code to GitHub
2. Connect GitHub repository to Railway
3. Railway will auto-deploy on every push to main branch

### Step 3: Run Database Migrations
After first deployment, Railway will automatically run:
```bash
alembic upgrade head
```

This is handled by `startup.sh` script.

### Step 4: Create Super Admin User
Execute this in Railway's terminal:
```bash
python scripts/create_super_admin.py
```

---

## 🧪 Testing the Deployment

### 1. Health Check
```bash
curl https://your-app.railway.app/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "RapidReportz Admin Panel",
  "version": "2.0.0",
  "environment": "production",
  "timestamp": "2026-01-13T...",
  "database": "connected",
  "features": {
    "cors": "enabled",
    "rate_limiting": "enabled",
    "authentication": "enabled"
  }
}
```

### 2. API Documentation
Visit: `https://your-app.railway.app/docs`

### 3. Test Authentication
```bash
# Register new user
curl -X POST https://your-app.railway.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123!",
    "full_name": "Test User",
    "user_type": "individual"
  }'

# Login
curl -X POST https://your-app.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123!"
  }'
```

---

## 🗄️ Database Tables Created

The fixed version will create these tables:
1. **users** - User accounts
2. **wallets** - User wallet balances
3. **transactions** - Transaction history
4. **user_activities** - Activity tracking
5. **refresh_tokens** - JWT refresh tokens
6. **invoices** - ✅ NEW - Payment invoices
7. **subscriptions** - ✅ NEW - Subscription management
8. **tickets** - Support tickets
9. **templates** - Report templates

---

## 🔍 Troubleshooting

### Issue: "500 Internal Server Error"
**Check Railway logs:**
```bash
railway logs
```

**Common causes:**
1. Missing environment variables
2. Database connection failed
3. Alembic migration failed (should be fixed now)

### Issue: "Import Error" on startup
**Solution:** Ensure all model imports are in `main.py` and `alembic/env.py`

### Issue: Payment routes not working
**Check:**
1. Billplz credentials are set in environment variables
2. Invoice and Subscription models are created (fixed in this version)

### Issue: Database migration fails
**Run manually:**
```bash
# In Railway terminal
cd /app
alembic upgrade head
```

---

## 📊 Key Features

✅ **Authentication System**
- JWT with refresh tokens
- Email verification
- OTP verification (SMS/Email)
- 2FA (Google Authenticator)
- Password reset

✅ **User Management**
- Multi-tier: Super Admin, Enterprise, Individual, Sub-users
- Enterprise parent-child structure
- User blocking/activation

✅ **Wallet System**
- Malaysian Ringgit (RM) currency
- Transaction tracking
- Balance management
- Auto-deduction for reports

✅ **Payment Gateway**
- Billplz integration (Malaysia)
- Wallet top-up
- Subscription purchase
- Webhook handling

✅ **Template Builder**
- Dynamic pricing (RM37 base + RM1 per page)
- Auto page counting
- Template management

✅ **Support System**
- Ticket creation
- Status tracking
- Priority management

✅ **Analytics**
- Dashboard for all user types
- Activity tracking
- Transaction history

---

## 🔐 Security Features

- **JWT Authentication** with token rotation
- **Password Hashing** with bcrypt
- **Rate Limiting** on sensitive endpoints
- **CORS Protection** with configurable origins
- **SQL Injection Protection** via SQLAlchemy ORM
- **Environment-based** security (dev vs production)

---

## 📝 API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `POST /api/auth/verify-email` - Verify email
- `POST /api/auth/verify-otp` - Verify OTP
- `POST /api/auth/enable-2fa` - Enable 2FA
- `POST /api/auth/forgot-password` - Request password reset
- `POST /api/auth/reset-password` - Reset password

### Users
- `GET /api/users/me` - Get current user
- `PUT /api/users/me` - Update profile
- `GET /api/users/` - List users (admin only)

### Wallets
- `GET /api/wallets/balance` - Get wallet balance
- `GET /api/wallets/transactions` - Transaction history

### Payment
- `POST /api/payment/wallet/topup` - Create wallet top-up
- `POST /api/payment/subscription/purchase` - Purchase subscription
- `POST /api/payment/webhook/billplz` - Billplz webhook
- `GET /api/payment/transaction/{id}` - Get transaction status

### Templates
- `GET /api/templates/` - List templates
- `POST /api/templates/` - Create template
- `GET /api/templates/{id}` - Get template

### Tickets
- `POST /api/tickets/` - Create ticket
- `GET /api/tickets/` - List tickets
- `PUT /api/tickets/{id}` - Update ticket

### Dashboard
- `GET /api/dashboard/super-admin/overview` - Super admin dashboard
- `GET /api/dashboard/enterprise/overview` - Enterprise dashboard
- `GET /api/dashboard/individual/overview` - Individual dashboard

---

## 🎯 Next Steps

1. ✅ Deploy fixed version to Railway
2. ✅ Verify all endpoints work
3. Configure Billplz payment gateway
4. Set up email service (optional)
5. Configure Redis for caching (optional)
6. Set up monitoring/logging
7. Configure backup strategy

---

## 📞 Support

For issues or questions about this deployment:
1. Check Railway logs: `railway logs`
2. Review this documentation
3. Check `/docs` endpoint for API documentation
4. Test with `/health` endpoint first

---

## ✨ What's New in This Fixed Version

1. ✅ **Alembic migrations work** - Fixed import paths
2. ✅ **Payment models added** - Invoice, Subscription, SubscriptionPlan
3. ✅ **SQLAlchemy 2.0 compatible** - All raw SQL uses text()
4. ✅ **All models registered** - Proper SQLAlchemy Base metadata
5. ✅ **Railway-ready** - postgres:// → postgresql:// auto-fix
6. ✅ **Health check fixed** - Proper database connection test

---

**Version:** 2.0.0 - Fixed & Production Ready  
**Last Updated:** January 13, 2026  
**Status:** ✅ All critical issues resolved
