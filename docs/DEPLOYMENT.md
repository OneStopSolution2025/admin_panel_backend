# Deployment Guide

## Prerequisites

- Server with Ubuntu 22.04 LTS or later
- Docker and Docker Compose installed
- Domain name configured (for production)
- SSL certificate (Let's Encrypt recommended)
- Minimum 2GB RAM, 2 CPU cores
- 20GB disk space

## Production Deployment Steps

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
```

### 2. Clone Repository

```bash
cd /opt
sudo git clone <repository-url> admin_panel
cd admin_panel
```

### 3. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Critical Production Settings:**

```env
# Application
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<generate-secure-random-key-min-32-chars>

# Database
DATABASE_URL=postgresql+asyncpg://prod_user:secure_password@postgres:5432/prod_db

# Security
CORS_ORIGINS=["https://yourdomain.com"]
ALLOWED_HOSTS=["yourdomain.com"]

# Redis (optional password)
REDIS_PASSWORD=secure_redis_password

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

**Generate Secure Keys:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. SSL Certificate Setup

#### Using Let's Encrypt:

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Generate certificate
sudo certbot certonly --nginx -d api.yourdomain.com

# Certificates will be in:
# /etc/letsencrypt/live/api.yourdomain.com/
```

#### Configure Nginx (Reverse Proxy):

```nginx
# /etc/nginx/sites-available/admin-panel
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/admin-panel /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Database Initialization

```bash
# Start only database first
docker-compose up -d postgres redis

# Wait for database to be ready
sleep 10

# Run migrations
docker-compose run --rm api alembic upgrade head

# Create super admin (optional)
docker-compose run --rm api python scripts/create_super_admin.py
```

### 6. Start All Services

```bash
# Start all containers
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

### 7. Verify Deployment

```bash
# Health check
curl https://api.yourdomain.com/health

# Test API documentation
open https://api.yourdomain.com/api/docs
```

## Monitoring Setup

### 1. Access Prometheus

```
http://your-server-ip:9090
```

### 2. Access Grafana

```
http://your-server-ip:3000
Default: admin/admin
```

### 3. Configure Alerts

Edit `monitoring/prometheus.yml` to add alert rules.

## Backup Strategy

### Database Backup

```bash
# Create backup script
cat > /opt/admin_panel/scripts/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/admin_panel"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
docker exec admin_panel_postgres pg_dump -U admin_user admin_panel_db | gzip > $BACKUP_DIR/db_$TIMESTAMP.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete

echo "Backup completed: db_$TIMESTAMP.sql.gz"
EOF

chmod +x /opt/admin_panel/scripts/backup.sh

# Add to crontab
crontab -e
# Add: 0 2 * * * /opt/admin_panel/scripts/backup.sh
```

### Restore from Backup

```bash
# Stop application
docker-compose stop api celery_worker celery_beat

# Restore database
gunzip < /opt/backups/admin_panel/db_20250106_020000.sql.gz | docker exec -i admin_panel_postgres psql -U admin_user admin_panel_db

# Start application
docker-compose start api celery_worker celery_beat
```

## Logging

### View Application Logs

```bash
# Real-time logs
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api

# Specific time range
docker-compose logs --since 2h api
```

### Log Rotation

Logs are automatically rotated using the configuration in `app/core/logging.py`:
- Max size: 10MB per file
- Backups: 5 files kept

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.prod.yml
services:
  api:
    deploy:
      replicas: 3
    
  celery_worker:
    deploy:
      replicas: 2
```

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale api=3
```

### Load Balancing

Use Nginx or AWS ELB to distribute traffic:

```nginx
upstream backend {
    least_conn;
    server api1:8000;
    server api2:8000;
    server api3:8000;
}

server {
    location / {
        proxy_pass http://backend;
    }
}
```

## Security Hardening

### 1. Firewall Configuration

```bash
# Install UFW
sudo apt install ufw -y

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

### 2. Fail2Ban Setup

```bash
# Install Fail2Ban
sudo apt install fail2ban -y

# Configure
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 3. Regular Updates

```bash
# Create update script
cat > /opt/admin_panel/scripts/update.sh << 'EOF'
#!/bin/bash
cd /opt/admin_panel

# Pull latest changes
git pull origin main

# Rebuild containers
docker-compose build

# Stop services
docker-compose stop

# Run migrations
docker-compose run --rm api alembic upgrade head

# Start services
docker-compose up -d

echo "Update completed"
EOF

chmod +x /opt/admin_panel/scripts/update.sh
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs api

# Check resource usage
docker stats

# Restart container
docker-compose restart api
```

### Database connection issues

```bash
# Check database status
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Test connection
docker exec admin_panel_postgres psql -U admin_user -d admin_panel_db -c "SELECT 1"
```

### High memory usage

```bash
# Check memory usage
docker stats

# Adjust resource limits in docker-compose.yml
services:
  api:
    mem_limit: 1g
    mem_reservation: 512m
```

## Performance Optimization

### 1. Database Optimization

```sql
-- Add indexes for frequently queried columns
CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_transaction_date ON transactions(created_at DESC);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';
```

### 2. Redis Cache Tuning

```bash
# In docker-compose.yml, set Redis memory limit
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

### 3. Application Tuning

```env
# In .env
WORKERS=4  # Number of CPU cores
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

## Maintenance Windows

Schedule regular maintenance:

```bash
# Weekly maintenance script
cat > /opt/admin_panel/scripts/maintenance.sh << 'EOF'
#!/bin/bash
# Stop application
docker-compose stop api celery_worker

# Run database maintenance
docker exec admin_panel_postgres vacuumdb -U admin_user -d admin_panel_db -z

# Clear old logs
find /opt/admin_panel/logs -name "*.log.*" -mtime +30 -delete

# Restart services
docker-compose start api celery_worker
EOF

chmod +x /opt/admin_panel/scripts/maintenance.sh

# Schedule weekly
# crontab: 0 3 * * 0 /opt/admin_panel/scripts/maintenance.sh
```

## Rollback Procedure

```bash
# 1. Stop services
docker-compose stop

# 2. Restore database backup
gunzip < /opt/backups/admin_panel/db_backup.sql.gz | docker exec -i admin_panel_postgres psql -U admin_user admin_panel_db

# 3. Checkout previous version
git checkout <previous-commit>

# 4. Rebuild and start
docker-compose build
docker-compose up -d
```

## Support Contacts

- Technical Support: support@yourcompany.com
- Emergency Hotline: +1-XXX-XXX-XXXX
- Documentation: https://docs.yourcompany.com
