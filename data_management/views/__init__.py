"""data_management views package.

Views are organised by concern:
  - ``auth``    : registration, login/logout, email verification, password reset
  - ``profile`` : student-facing dashboard and profile detail/edit
  - ``staff``   : staff student management (list, detail, create, update, delete,
                  password reset, CSV export)

Public names are re-exported here so ``data_management.urls`` and tests can keep
importing ``from data_management import views`` unchanged.
"""

from .auth import (
    password_reset_confirm,
    password_reset_request,
    register,
    resend_verification_code,
    staff_login,
    user_login,
    user_logout,
    verify_email,
)
from .profile import (
    StudentDataDetailView,
    StudentDataUpdateView,
    dashboard,
)
from .staff import (
    StaffDashboardDataListView,
    StaffStudentCreateView,
    StaffStudentDeleteView,
    StaffStudentDetailView,
    StaffStudentUpdateView,
    export_students_csv,
    staff_student_reset_password,
)

__all__ = [
    # auth
    "register",
    "user_login",
    "staff_login",
    "user_logout",
    "verify_email",
    "resend_verification_code",
    "password_reset_request",
    "password_reset_confirm",
    # profile
    "dashboard",
    "StudentDataDetailView",
    "StudentDataUpdateView",
    # staff
    "StaffDashboardDataListView",
    "StaffStudentDetailView",
    "StaffStudentUpdateView",
    "StaffStudentCreateView",
    "StaffStudentDeleteView",
    "staff_student_reset_password",
    "export_students_csv",
]
