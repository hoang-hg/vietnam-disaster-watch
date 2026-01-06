# Docker Deployment Guide

## Quick Start

### Development Environment

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Start all services
docker-compose up -d

# 3. Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Production Environment

```bash
# 1. Create production environment file
cp .env.production.example .env

# 2. Edit .env and set secure values:
#    - DB_PASSWORD: Strong database password
#    - SECRET_KEY: Random string for JWT (generate with: openssl rand -hex 32)
#    - DOMAIN: Your actual domain name

# 3. Update nginx/nginx.conf:
#    - Replace example.com with your domain

# 4. Build and start services
docker-compose -f docker-compose.prod.yml up -d --build

# 5. Setup SSL certificate (Let's Encrypt)
docker-compose -f docker-compose.prod.yml run --rm certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  --email your@email.com \
  --agree-tos \
  --no-eff-email \
  -d yourdomain.com -d www.yourdomain.com

# 6. Restart nginx to apply SSL
docker-compose -f docker-compose.prod.yml restart nginx
```

## Architecture

### Development (docker-compose.yml)
- **Frontend**: Nginx serving React SPA on port 80 with proxy to backend
- **Backend**: FastAPI with auto-reload on port 8000
- **Database**: PostgreSQL 15 (internal network only)
- **Redis**: Redis 7 (internal network only)
- **Volumes**: Source code mounted for hot-reload

### Production (docker-compose.prod.yml)
- **Nginx Proxy**: Handles SSL termination and routing (ports 80, 443)
- **Frontend**: React SPA served by Nginx
- **Backend**: FastAPI with Gunicorn (4 workers)
- **Database**: PostgreSQL 15 with persistent volume
- **Redis**: Redis 7 for caching
- **Certbot**: Automatic SSL certificate renewal
- **Healthchecks**: All services monitored
- **Volumes**: Named volumes for persistence, no source code mounting

## Key Differences: Dev vs Prod

| Feature | Development | Production |
|---------|------------|------------|
| Hot Reload | ✅ Enabled | ❌ Disabled |
| Source Mounting | ✅ Yes | ❌ No |
| Workers | 1 (uvicorn) | 4 (gunicorn) |
| SSL/HTTPS | ❌ No | ✅ Yes |
| Port Exposure | DB & Redis exposed | Only 80/443 exposed |
| Healthchecks | ❌ No | ✅ Yes |
| Auto-restart | Always | Always |

## Environment Variables

### Required for Production
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password (must be strong)
- `DB_NAME`: Database name
- `SECRET_KEY`: JWT secret key (use `openssl rand -hex 32`)
- `DOMAIN`: Your domain name

### Optional
- `CRAWLER_PROXIES`: JSON array of proxy URLs
- `REDIS_URL`: Redis connection string (default: redis://redis:6379/0)
- `APP_TIMEZONE`: Timezone (default: Asia/Ho_Chi_Minh)

## Common Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# Production
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Restart Services
```bash
# All services
docker-compose restart

# Specific service
docker-compose restart backend

# Production
docker-compose -f docker-compose.prod.yml restart backend
```

### Rebuild After Code Changes
```bash
# Development (with hot-reload, usually no rebuild needed)
docker-compose up -d

# Production (requires rebuild)
docker-compose -f docker-compose.prod.yml up -d --build
```

### Access Database
```bash
# Development
docker exec -it viet_disaster_db psql -U postgres -d postgres

# Production (update credentials accordingly)
docker exec -it viet_disaster_db psql -U disaster_admin -d disaster_watch
```

### Clean Everything (⚠️ DANGER: Deletes all data)
```bash
# Stop and remove containers, networks, volumes
docker-compose down -v

# Also remove images
docker-compose down -v --rmi all
```

## Healthcheck Endpoints

- **Backend**: `http://backend:8000/health`
- **Database**: `pg_isready` command
- **Redis**: `redis-cli ping`

Production automatically checks these and restarts unhealthy containers.

## Troubleshooting

### Backend won't start
```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Database not ready: Wait for healthcheck to pass
# - Port 8000 in use: Stop other services using port 8000
# - Missing dependencies: Rebuild image
```

### Frontend shows "Failed to fetch"
```bash
# 1. Check if backend is running
docker-compose ps

# 2. Check backend logs
docker-compose logs backend

# 3. Verify VITE_API_BASE is empty (not /api)
# 4. Verify nginx.conf has correct proxy settings
```

### SSL Certificate Issues
```bash
# Test SSL renewal
docker-compose -f docker-compose.prod.yml run --rm certbot renew --dry-run

# Force renewal
docker-compose -f docker-compose.prod.yml run --rm certbot renew --force-renewal

# Restart nginx after renewal
docker-compose -f docker-compose.prod.yml restart nginx
```

### Database Connection Issues
```bash
# Check if database is healthy
docker-compose ps

# Access database directly
docker exec -it viet_disaster_db psql -U postgres

# Check environment variables
docker-compose config
```

## Performance Tuning

### Backend Workers
Edit `backend/Dockerfile` line 30:
```dockerfile
# Change -w 4 to desired number of workers
# Rule of thumb: (2 x CPU cores) + 1
CMD ["gunicorn", "app.main:app", "-w", "8", ...]
```

### Database Connections
Gunicorn workers × connections per worker should not exceed PostgreSQL max_connections (default: 100).

### Nginx Caching
Static files are automatically cached. API responses are not cached for data freshness.

## Security Checklist

- [ ] Changed default database password
- [ ] Generated strong SECRET_KEY
- [ ] Updated domain in nginx.conf
- [ ] SSL certificate installed and working
- [ ] Firewall allows only ports 80 and 443
- [ ] Regular backup strategy in place
- [ ] Environment variables not committed to git
- [ ] HTTPS redirect enabled
- [ ] Security headers configured in nginx

## Backup & Restore

### Backup Database
```bash
docker exec viet_disaster_db pg_dump -U postgres postgres > backup.sql
```

### Restore Database
```bash
cat backup.sql | docker exec -i viet_disaster_db psql -U postgres postgres
```

### Backup Volumes
```bash
docker run --rm -v viet-disaster-watch_db_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/db_data_backup.tar.gz -C /data .
```
