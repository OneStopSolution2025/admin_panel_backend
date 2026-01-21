# RapidReportz Admin Panel Backend

FastAPI-based REST API for RapidReportz Admin Panel with PostgreSQL database and Redis caching.

## 🚀 Features

- ✅ **FastAPI** - Modern, fast web framework
- ✅ **PostgreSQL** - Reliable database with SQLAlchemy ORM
- ✅ **Redis** - Caching layer
- ✅ **JWT Authentication** - Secure token-based auth
- ✅ **Alembic** - Database migrations
- ✅ **Docker** - Containerized deployment
- ✅ **Railway Ready** - Pre-configured for Railway deployment

## 📦 Project Structure

```
admin_panel_backend/
├── Dockerfile                      # Docker configuration
├── .dockerignore                   # Docker ignore rules
├── .gitignore                      # Git ignore rules
├── .env.example                    # Environment variables example
├── README.md                       # This file
└── app/
    ├── main.py                     # FastAPI application entry point
    ├── requirements.txt            # Python dependencies
    ├── alembic.ini                # Alembic configuration
    ├── core/
    │   ├── config.py              # Application settings
    │   ├── database.py            # Database connection
    │   ├── cache.py               # Redis cache manager
    │   └── security.py            # JWT & password hashing
    ├── models/
    │   ├── user.py                # User model
    │   ├── wallet.py              # Wallet model
    │   ├── activity.py            # Activity log model
    │   ├── ticket.py              # Support ticket model
    │   └── template.py            # Report template model
    ├── api/
    │   ├── deps.py                # API dependencies
    │   └── routes/
    │       ├── auth.py            # Authentication endpoints
    │       ├── users.py           # User management
    │       ├── wallet.py          # Wallet operations
    │       ├── activities.py      # Activity logs
    │       ├── dashboard.py       # Dashboard stats
    │       ├── tickets.py         # Support tickets
    │       └── templates.py       # Report templates
    └── alembic/
        ├── env.py                 # Alembic environment
        └── versions/              # Migration files
```

## 🛠️ Railway Deployment Guide

### Step 1: Push to GitHub

```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit - RapidReportz backend"

# Create GitHub repository and push
git remote add origin https://github.com/YOUR_USERNAME/admin_panel_backend.git
git branch -M main
git push -u origin main
```

### Step 2: Create Railway Project

1. Go to https://railway.app
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose **"admin_panel_backend"**

### Step 3: Add PostgreSQL Database

1. In your project, click **"+ New"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Wait for it to provision

### Step 4: Add Redis

1. Click **"+ New"** again
2. Select **"Database"** → **"Add Redis"**
3. Wait for it to provision

### Step 5: Configure Environment Variables

1. Click your **backend service**
2. Go to **"Variables"** tab
3. Add these variables:

**DATABASE_URL** (Variable Reference):
- Click "+ New Variable"
- Name: `DATABASE_URL`
- Click "Add Variable Reference"
- Select: `Postgres` → `DATABASE_URL`

**REDIS_URL** (Variable Reference):
- Click "+ New Variable"
- Name: `REDIS_URL`
- Click "Add Variable Reference"
- Select: `Redis` → `REDIS_URL`

**SECRET_KEY** (Raw Value):
- Name: `SECRET_KEY`
- Value: `rapidreportz-production-secret-key-change-to-random-32-chars`

**JWT_SECRET_KEY** (Raw Value):
- Name: `JWT_SECRET_KEY`
- Value: `jwt-secret-different-from-above-also-32-characters`

**Other Variables** (All Raw Values):
```
ALGORITHM = HS256
ACCESS_TOKEN_EXPIRE_MINUTES = 30
ENVIRONMENT = production
PYTHONUNBUFFERED = 1
```

### Step 6: Generate Domain

1. Go to **Settings** → **Networking**
2. Click **"Generate Domain"**
3. Port: `8000`
4. Click **"Generate"**

### Step 7: Deploy!

Railway automatically deploys. Wait 2-3 minutes.

Your API will be live at:
```
https://your-service-name.up.railway.app
```

## 📝 API Documentation

Once deployed, access the interactive API documentation:

- **Swagger UI**: `https://your-url.railway.app/docs`
- **ReDoc**: `https://your-url.railway.app/redoc`
- **Health Check**: `https://your-url.railway.app/health`

## 🔐 API Endpoints

### Authentication (`/api/auth`)
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user (returns JWT token)

### Users (`/api/users`)
- `GET /api/users/me` - Get current user info
- `GET /api/users` - List all users (admin only)
- `GET /api/users/{id}` - Get user by ID

### Wallet (`/api/wallet`)
- `GET /api/wallet/balance` - Get wallet balance
- `POST /api/wallet/deposit` - Deposit funds
- `POST /api/wallet/withdraw` - Withdraw funds

### Dashboard (`/api/dashboard`)
- `GET /api/dashboard/stats` - Get dashboard statistics

### Tickets (`/api/tickets`)
- `GET /api/tickets` - List user tickets
- `POST /api/tickets` - Create new ticket
- `GET /api/tickets/{id}` - Get ticket details
- `PUT /api/tickets/{id}` - Update ticket

### Templates (`/api/templates`)
- `GET /api/templates` - List all templates
- `POST /api/templates` - Create template (admin)
- `GET /api/templates/{id}` - Get template details
- `PUT /api/templates/{id}` - Update template (admin)
- `POST /api/templates/{id}/calculate-price` - Calculate price

### Activities (`/api/activities`)
- `GET /api/activities` - List user activities
- `POST /api/activities` - Log new activity

## 🧪 Testing the API

### 1. Register a User

```bash
curl -X POST "https://your-url.railway.app/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@rapidreportz.com",
    "username": "admin",
    "password": "SecurePassword123",
    "full_name": "Admin User"
  }'
```

### 2. Login

```bash
curl -X POST "https://your-url.railway.app/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=SecurePassword123"
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user_id": 1,
  "username": "admin"
}
```

### 3. Access Protected Endpoints

```bash
curl -X GET "https://your-url.railway.app/api/users/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 🔧 Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL
- Redis

### Setup

1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/admin_panel_backend.git
cd admin_panel_backend
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
cd app
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your local database credentials
```

5. Run migrations
```bash
alembic upgrade head
```

6. Start the server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Visit: http://localhost:8000/docs

## 🐳 Docker Development

```bash
# Build the image
docker build -t rapidreportz-backend .

# Run the container
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -e REDIS_URL="redis://host:6379" \
  -e SECRET_KEY="your-secret-key" \
  -e JWT_SECRET_KEY="your-jwt-secret" \
  rapidreportz-backend
```

## 📊 Database Migrations

### Create a new migration
```bash
alembic revision --autogenerate -m "description"
```

### Apply migrations
```bash
alembic upgrade head
```

### Rollback migration
```bash
alembic downgrade -1
```

## 🔒 Security Considerations

- **Change default secrets** in production
- **Use strong passwords** for database
- **Enable CORS** only for trusted domains
- **Use HTTPS** in production (Railway provides this)
- **Rate limiting** - Consider adding rate limiting middleware
- **Input validation** - All inputs are validated via Pydantic

## 📈 Monitoring

### Check Health
```bash
curl https://your-url.railway.app/health
```

### Railway Metrics
- Go to Railway → Your Service → **Metrics** tab
- Monitor CPU, Memory, Network usage

### View Logs
- Railway → Your Service → **Deployments** → Click deployment → View logs

## 🐛 Troubleshooting

### Issue: Application crashes on startup

**Solution**: Check environment variables are set correctly
```bash
# In Railway, verify:
- DATABASE_URL (should be a reference: ${{Postgres.DATABASE_URL}})
- REDIS_URL (should be a reference: ${{Redis.REDIS_URL}})
- SECRET_KEY (should be set)
```

### Issue: Database connection failed

**Solution**: Ensure PostgreSQL service is running and DATABASE_URL is correct
```bash
# Check PostgreSQL service status in Railway
# Verify DATABASE_URL format: postgresql://user:pass@host:5432/dbname
```

### Issue: Import errors

**Solution**: All imports are relative (no 'app.' prefix)
```python
# Correct:
from core.config import settings

# Wrong:
from app.core.config import settings
```

## 📞 Support

For issues or questions:
- Check Railway logs first
- Review this README
- Check `/docs` endpoint for API documentation
- Verify environment variables are set correctly

## 📄 License

This project is proprietary to OneStopSolution / RapidReportz.

---

**Built with ❤️ by OneStopSolution Team**

**Deployed on Railway: https://railway.app**
