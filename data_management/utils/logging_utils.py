"""
Logging utilities for the data_management app.
Provides centralized logging functions with security and audit considerations.
"""

import logging
from functools import wraps
from typing import Dict, Optional

from django.http import HttpRequest


def get_client_ip(request: HttpRequest) -> str:
    """
    Extract client IP address from request.

    Args:
        request: Django HttpRequest object

    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "Unknown")
    return ip


def get_user_info(request: HttpRequest) -> Dict[str, str]:
    """
    Extract user information from request.

    Args:
        request: Django HttpRequest object

    Returns:
        dict: User information including username and IP
    """
    return {
        "username": request.user.username if request.user.is_authenticated else "Anonymous",
        "user_id": str(request.user.id) if request.user.is_authenticated else "N/A",
        "ip": get_client_ip(request),
        "is_staff": str(request.user.is_staff) if request.user.is_authenticated else "False",
        "is_authenticated": str(request.user.is_authenticated),
    }


def log_user_action(logger_name: str = None):
    """
    Decorator to automatically log user actions in views.

    Args:
        logger_name: Optional logger name, defaults to module name

    Usage:
        @log_user_action()
        def my_view(request):
            # view logic
            pass
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            logger = logging.getLogger(logger_name or func.__module__)
            user_info = get_user_info(request)

            # Log the action start
            logger.info(
                f"Action started: {func.__name__} - "
                f"User: {user_info['username']}, "
                f"IP: {user_info['ip']}, "
                f"Method: {request.method}"
            )

            try:
                # Execute the view
                result = func(request, *args, **kwargs)

                # Log successful completion
                logger.info(
                    f"Action completed: {func.__name__} - "
                    f"User: {user_info['username']}, "
                    f"IP: {user_info['ip']}"
                )

                return result

            except Exception as e:
                # Log any errors
                logger.error(
                    f"Action failed: {func.__name__} - "
                    f"User: {user_info['username']}, "
                    f"IP: {user_info['ip']}, "
                    f"Error: {str(e)}",
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


class SecurityLogger:
    """
    Centralized security event logging.
    """

    def __init__(self, logger_name: str = "data_management.security"):
        self.logger = logging.getLogger(logger_name)

    def log_login_attempt(
        self,
        request: HttpRequest,
        username: str,
        success: bool,
        is_staff: bool = False,
        additional_info: str = "",
    ):
        """
        Log login attempts with security context.

        Args:
            request: Django HttpRequest object
            username: Attempted username
            success: Whether login was successful
            is_staff: Whether this is a staff login attempt
            additional_info: Additional information to log
        """
        user_info = get_user_info(request)
        login_type = "Staff" if is_staff else "User"
        status = "SUCCESS" if success else "FAILED"

        message = (
            f"{login_type} login {status} - " f"Username: {username}, " f"IP: {user_info['ip']}"
        )

        if additional_info:
            message += f", Info: {additional_info}"

        if success:
            self.logger.info(message)
        else:
            self.logger.warning(message)

    def log_logout(self, request: HttpRequest):
        """Log a successful logout action."""
        user_info = get_user_info(request)
        self.logger.info(
            f"User logout SUCCESS - User: {user_info['username']}, IP: {user_info['ip']}"
        )

    def log_access_attempt(
        self, request: HttpRequest, resource: str, granted: bool, reason: str = ""
    ):
        """
        Log access attempts to protected resources.

        Args:
            request: Django HttpRequest object
            resource: Resource being accessed
            granted: Whether access was granted
            reason: Reason for denial if applicable
        """
        user_info = get_user_info(request)
        status = "GRANTED" if granted else "DENIED"

        message = (
            f"Access {status} - "
            f"Resource: {resource}, "
            f"User: {user_info['username']}, "
            f"IP: {user_info['ip']}"
        )

        if reason:
            message += f", Reason: {reason}"

        if granted:
            self.logger.info(message)
        else:
            self.logger.warning(message)

    def log_data_modification(
        self,
        request: HttpRequest,
        action: str,
        model: str,
        record_id: Optional[str] = None,
        success: bool = True,
        error_msg: str = "",
    ):
        """
        Log data modification events.

        Args:
            request: Django HttpRequest object
            action: Type of action (CREATE, UPDATE, DELETE)
            model: Model being modified
            record_id: ID of the record if applicable
            success: Whether the action was successful
            error_msg: Error message if action failed
        """
        user_info = get_user_info(request)
        status = "SUCCESS" if success else "FAILED"

        message = (
            f"Data {action} {status} - "
            f"Model: {model}, "
            f"User: {user_info['username']}, "
            f"IP: {user_info['ip']}"
        )

        if record_id:
            message += f", Record ID: {record_id}"

        if error_msg:
            message += f", Error: {error_msg}"

        if success:
            self.logger.info(message)
        else:
            self.logger.error(message)


class AuditLogger:
    """
    Audit trail logging for compliance and monitoring.
    """

    def __init__(self, logger_name: str = "data_management.audit"):
        self.logger = logging.getLogger(logger_name)

    def log_user_registration(
        self, request: HttpRequest, username: str, success: bool, errors: Dict = None
    ):
        """Log user registration events."""
        user_info = get_user_info(request)
        status = "SUCCESS" if success else "FAILED"

        message = (
            f"User registration {status} - " f"New username: {username}, " f"IP: {user_info['ip']}"
        )

        if errors:
            message += f", Errors: {errors}"

        self.logger.info(message)

    def log_profile_update(
        self, request: HttpRequest, updated_fields: list, success: bool, errors: Dict = None
    ):
        """Log profile update events."""
        user_info = get_user_info(request)
        status = "SUCCESS" if success else "FAILED"

        message = (
            f"Profile update {status} - "
            f"User: {user_info['username']}, "
            f"Fields: {', '.join(updated_fields)}, "
            f"IP: {user_info['ip']}"
        )

        if errors:
            message += f", Errors: {errors}"

        self.logger.info(message)


# Create singleton instances for easy import
security_logger = SecurityLogger()
audit_logger = AuditLogger()
