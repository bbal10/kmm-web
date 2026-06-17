#!/bin/bash
# Production Deployment Script for Docker

set -e

echo "🚀 KMM Web - Docker Production Deployment"
echo "=========================================="

# Check if docker and docker-compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.docker .env
    echo "✅ Created .env file. Please edit it with your configuration."
    echo "   IMPORTANT: Update SECRET_KEY, POSTGRES_PASSWORD, ALLOWED_HOSTS"
    read -p "Press Enter to continue after editing .env file..."
fi

# Validate critical environment variables
source .env

if [ "$SECRET_KEY" == "your-very-secure-secret-key-here-minimum-50-characters-CHANGE-THIS-IN-PRODUCTION" ]; then
    echo "❌ ERROR: Please change SECRET_KEY in .env file"
    echo "   Generate one with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
    exit 1
fi

if [ "$POSTGRES_PASSWORD" == "changeme_secure_password_here" ]; then
    echo "⚠️  WARNING: Using default database password. Please change POSTGRES_PASSWORD in .env"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create required directories
echo "📁 Creating required directories..."
mkdir -p logs backups nginx/ssl media staticfiles

# Set permissions
echo "🔒 Setting permissions..."
chmod +x docker-entrypoint.sh

# Build images using production config
echo "🏗️  Building Docker images (Production Mode)..."
docker compose -f docker-compose.prod.yml build --no-cache

# Start services using production config
echo "🚀 Starting services..."
docker compose -f docker-compose.prod.yml up -d

# Wait for services (postgres/redis/web) to be healthy using healthchecks
echo "⏳ Waiting for services to be healthy..."
if docker compose -f docker-compose.prod.yml up -d --wait --wait-timeout 120; then
    echo "✅ All services healthy"
else
    echo "⚠️  Wait completed (some services may still be starting)"
    sleep 5
fi

# Verify web container is actually running before continuing
WEB_RUNNING=$(docker compose -f docker-compose.prod.yml ps -q web | head -1)
if [ -z "$WEB_RUNNING" ] || ! docker inspect "$WEB_RUNNING" --format '{{.State.Running}}' 2>/dev/null | grep -q true; then
    echo "❌ ERROR: web container is not running"
    echo "📝 Last logs from web:"
    docker compose -f docker-compose.prod.yml logs --tail=100 web || true
    exit 1
fi

# Note: migrate + collectstatic are performed inside the container entrypoint on startup.
# No need to run them again here unless you want to force re-collection.

# Check service status
echo "📊 Service Status:"
docker compose -f docker-compose.prod.yml ps

# Show logs
echo ""
echo "📝 Recent Logs:"
docker compose -f docker-compose.prod.yml logs --tail=50

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "🌐 Access your application (via Nginx):"
echo "   - Web: http://localhost"
echo "   - Admin: http://localhost/admin"
echo "   - Health: http://localhost/health/"
echo ""
echo "   If using a custom domain:"
echo "   - Make sure ALLOWED_HOSTS in .env includes your domain"
echo "   - Update server_name in nginx/conf.d/default.conf"
echo "   - Point DNS A record to this server"
echo ""
echo "📋 Useful commands:"
echo "   - View logs: docker compose -f docker-compose.prod.yml logs -f"
echo "   - Stop: docker compose -f docker-compose.prod.yml down"
echo "   - Restart: docker compose -f docker-compose.prod.yml restart"
echo "   - Shell: docker compose -f docker-compose.prod.yml exec web uv run python manage.py shell"
echo "   - Migrate: docker compose -f docker-compose.prod.yml exec web uv run python manage.py migrate"
echo ""
echo "📖 For more information, see DOCKER_DEPLOYMENT.md"

