"""
Health check views for monitoring application status.
"""

import logging

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views import View

logger = logging.getLogger(__name__)


class HealthCheckView(View):
    """
    Simple health check endpoint for load balancers and monitoring systems.
    """

    def get(self, request):
        """
        Perform basic health checks and return status.
        """
        health_status = {
            "status": "healthy",
            "database": "unknown",
            "cache": "unknown",
            "debug": settings.DEBUG,
        }

        status_code = 200

        # Check database connectivity
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_status["database"] = "healthy"
        except Exception as e:
            health_status["database"] = "unhealthy"
            health_status["status"] = "unhealthy"
            status_code = 503
            logger.error(f"Database health check failed: {e}")

        # Check cache connectivity
        try:
            cache.set("health_check", "ok", 30)
            if cache.get("health_check") == "ok":
                health_status["cache"] = "healthy"
            else:
                health_status["cache"] = "unhealthy"
        except Exception as e:
            health_status["cache"] = "unhealthy"
            health_status["status"] = "degraded"
            logger.warning(f"Cache health check failed: {e}")

        return JsonResponse(health_status, status=status_code)


class ReadinessCheckView(View):
    """
    Readiness check endpoint for Kubernetes/container orchestration.
    """

    def get(self, request):
        """
        Check if the application is ready to receive traffic.
        """
        try:
            # Check database migrations are up to date
            from django.db import connections
            from django.db.migrations.executor import MigrationExecutor

            executor = MigrationExecutor(connections["default"])
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

            if plan:
                return JsonResponse(
                    {"status": "not_ready", "reason": "pending_migrations"}, status=503
                )

            return JsonResponse({"status": "ready"}, status=200)

        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return JsonResponse({"status": "not_ready", "reason": str(e)}, status=503)


class LivenessCheckView(View):
    """
    Liveness check endpoint for Kubernetes/container orchestration.
    """

    def get(self, request):
        """
        Basic liveness check - just return 200 if Django is running.
        """
        return JsonResponse({"status": "alive"}, status=200)
