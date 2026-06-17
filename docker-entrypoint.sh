#!/bin/bash
set -e

# Activate virtual environment
export VIRTUAL_ENV=/app/.venv
export PATH="/app/.venv/bin:$PATH"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting KMM Web Application...${NC}"

# Verify Python is using the correct environment
echo -e "${YELLOW}🐍 Python: $(which python)${NC}"
echo -e "${YELLOW}📦 Checking psycopg installation...${NC}"
python -c "import psycopg; print(f'✅ psycopg {psycopg.__version__} installed')" || echo -e "${RED}❌ psycopg not found${NC}"

# Function to wait for PostgreSQL
wait_for_postgres() {
    echo -e "${YELLOW}⏳ Waiting for PostgreSQL...${NC}"

    # Extract database connection details from DATABASE_URL
    # Format: postgresql://user:password@host:port/dbname
    if [ -z "$DATABASE_URL" ]; then
        echo -e "${RED}❌ DATABASE_URL is not set${NC}"
        exit 1
    fi

    # Simple retry logic
    max_retries=30
    retry_count=0

    until python << END
import sys
import os
import time
try:
    import psycopg
    conn = psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=5)
    conn.close()
    print("Database is ready!")
    sys.exit(0)
except Exception as e:
    print(f"Database not ready: {e}")
    sys.exit(1)
END
    do
        retry_count=$((retry_count+1))
        if [ $retry_count -ge $max_retries ]; then
            echo -e "${RED}❌ Database connection timeout after $max_retries attempts${NC}"
            exit 1
        fi
        echo -e "${YELLOW}Waiting for database... (attempt $retry_count/$max_retries)${NC}"
        sleep 2
    done

    echo -e "${GREEN}✅ PostgreSQL is ready!${NC}"
}

# Function to wait for Redis (optional)
wait_for_redis() {
    if [ -n "$REDIS_URL" ]; then
        echo -e "${YELLOW}⏳ Waiting for Redis...${NC}"

        max_retries=30
        retry_count=0

        until python << END
import sys
import os
try:
    from redis import Redis
    redis_url = os.environ.get('REDIS_URL')
    r = Redis.from_url(redis_url, socket_connect_timeout=5)
    r.ping()
    print("Redis is ready!")
    sys.exit(0)
except Exception as e:
    print(f"Redis not ready: {e}")
    sys.exit(1)
END
        do
            retry_count=$((retry_count+1))
            if [ $retry_count -ge $max_retries ]; then
                echo -e "${YELLOW}⚠️  Redis connection timeout - continuing without cache${NC}"
                break
            fi
            echo -e "${YELLOW}Waiting for Redis... (attempt $retry_count/$max_retries)${NC}"
            sleep 2
        done

        echo -e "${GREEN}✅ Redis is ready!${NC}"
    fi
}

# Wait for dependencies
wait_for_postgres
wait_for_redis

# Run database migrations
echo -e "${YELLOW}🔄 Running database migrations...${NC}"
python manage.py migrate --noinput

# Collect static files
echo -e "${YELLOW}📁 Collecting static files...${NC}"
python manage.py collectstatic --noinput --clear

# Create superuser if it doesn't exist
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo -e "${YELLOW}👤 Creating superuser...${NC}"
    python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created successfully!')
else:
    print('Superuser already exists.')
END
fi

# Run deployment checks (warnings are expected in many production setups; do not fail startup)
echo -e "${YELLOW}🔍 Running deployment checks...${NC}"
python manage.py check --deploy || echo -e "${YELLOW}⚠️  Deployment check completed with warnings (non-fatal)${NC}"

echo -e "${GREEN}✅ Application is ready!${NC}"
echo -e "${GREEN}🎯 Starting application server...${NC}"

# Execute the main command (gunicorn or whatever was passed)
exec "$@"

