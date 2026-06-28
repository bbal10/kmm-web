"""Shared helpers and constants for the data_management views package.

This module centralises logic that was previously duplicated across the
profile and staff views: email verification, interest syncing, student
queryset filtering, audit/security logging on update, and the field-group
context dictionaries used by the form templates.
"""

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone

from ..forms import get_country_code_choices
from ..models import EmailVerification, InterestCategory, Student, StudentInterest
from ..utils.logging_utils import audit_logger, security_logger

logger = logging.getLogger("data_management.views")


# --- Field groups shared by the student form templates -----------------------

STUDENT_BASIC_FIELDS = [
    "whatsapp_number",
    "birth_place",
    "birth_date",
    "gender",
    "marital_status",
    "membership_status",
    "region_origin",
    "parents_name",
    "parents_phone",
]

# Staff forms additionally edit the underlying User fields.
STAFF_BASIC_FIELDS = ["email", "first_name", "last_name"] + STUDENT_BASIC_FIELDS

ACADEMIC_FIELDS = [
    "institution",
    "institution_custom",
    "faculty",
    "faculty_custom",
    "major",
    "major_custom",
    "degree_level",
    "semester_level",
    "latest_grade",
    "level",
]

IDENTITY_EXTRA_FIELDS = [
    "passport_number",
    "lapdik_number",
    "arrival_date",
    "school_origin",
    "home_name",
    "home_location",
]

GUARDIAN_FIELDS = ["photo_url", "guardian_name", "guardian_phone"]

HEALTH_FIELDS = ["disease_history", "disease_status"]

FINANCIAL_FIELDS = [
    "education_funding",
    "scholarship_source",
    "living_cost",
    "monthly_income",
]

# Fields a staff member can filter the student list by.
STUDENT_FILTER_PARAMS = ["q", "gender", "degree_level", "level", "marital_status"]


# --- Email verification -------------------------------------------------------


def generate_verification_code():
    """Generate a secure 6-digit numeric verification code."""
    return str(secrets.randbelow(1000000)).zfill(6)


def create_email_verification(user):
    """Create (or refresh) an EmailVerification record for *user* and return it.

    Note: ``last_resend_at`` is intentionally left as ``None`` here. Callers
    must update it to ``timezone.now()`` only *after* the verification email
    has been sent successfully, so that a failed send does not start the
    resend cooldown.
    """
    expires_at = timezone.now() + timedelta(minutes=EmailVerification.EXPIRY_MINUTES)
    code = generate_verification_code()
    verification, _ = EmailVerification.objects.update_or_create(
        user=user,
        defaults={
            "code": code,
            "expires_at": expires_at,
            "attempt_count": 0,
            "last_resend_at": None,
        },
    )
    return verification


def send_verification_email(user, code):
    """Send an email verification code to *user*.

    Returns ``True`` on success, ``False`` on failure (the error is logged but
    *not* re-raised so the view can show a friendly message instead of a 500).
    """
    subject = "Verifikasi Email - KMM Mesir"
    message = (
        f"Halo {user.get_full_name() or user.username},\n\n"
        f"Terima kasih telah mendaftar di KMM Mesir.\n\n"
        f"Kode verifikasi email Anda adalah:\n\n"
        f"    {code}\n\n"
        f"Kode ini berlaku selama {EmailVerification.EXPIRY_MINUTES} menit.\n\n"
        f"Jika Anda tidak mendaftar, abaikan email ini.\n\n"
        f"Salam,\nTim KMM Mesir"
    )
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as exc:
        logger.error("Failed to send verification email to %s: %s", user.email, exc)
        return False


# --- Interests ----------------------------------------------------------------


def get_interest_categories_context():
    """Return InterestCategory queryset with prefetched interests for template context."""
    return InterestCategory.objects.prefetch_related("interests").all()


def get_interests_grouped(student):
    """Return interests grouped by category for detail templates."""
    categories = InterestCategory.objects.prefetch_related("interests").all()
    selected = {
        si.interest_id: si
        for si in student.student_interests.select_related("interest__category").all()
    }
    result = []
    for cat in categories:
        items = [selected[i.pk] for i in cat.interests.all() if i.pk in selected]
        if items:
            result.append({"category": cat, "items": items})
    return result


def save_student_interests(student, post_data):
    """Sync StudentInterest records from POST data.

    Expected POST keys:
      - interest_ids   : list of Interest PKs that are checked
      - custom_interest_<pk> : custom text for 'Isi Sendiri' interests
    """
    checked_ids = set(map(int, post_data.getlist("interest_ids")))

    # Remove unchecked
    StudentInterest.objects.filter(student=student).exclude(interest_id__in=checked_ids).delete()

    # Upsert checked
    existing = {si.interest_id: si for si in StudentInterest.objects.filter(student=student)}
    for interest_id in checked_ids:
        custom = post_data.get(f"custom_interest_{interest_id}", "").strip()
        if interest_id in existing:
            si = existing[interest_id]
            if si.custom_value != custom:
                si.custom_value = custom
                si.save(update_fields=["custom_value"])
        else:
            StudentInterest.objects.create(
                student=student, interest_id=interest_id, custom_value=custom
            )


def build_interest_context(student):
    """Return the interest-related context keys shared by the form views."""
    has_pk = bool(student and student.pk)
    return {
        "interest_categories": get_interest_categories_context(),
        "selected_interest_ids": (
            set(student.student_interests.values_list("interest_id", flat=True))
            if has_pk
            else set()
        ),
        "student_interest_customs": (
            {si.interest_id: si.custom_value for si in student.student_interests.all()}
            if has_pk
            else {}
        ),
    }


# --- Student queryset filtering -----------------------------------------------


def apply_student_filters(qs, params):
    """Apply the shared search/filter parameters to a Student queryset.

    Used by both the staff list view and the CSV export so filtering stays
    consistent between what is displayed and what is exported.
    """
    q = params.get("q", "").strip()
    gender = params.get("gender", "").strip()
    degree_level = params.get("degree_level", "").strip()
    level = params.get("level", "").strip()
    marital_status = params.get("marital_status", "").strip()

    if q:
        qs = qs.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__email__icontains=q)
            | Q(passport_number__icontains=q)
            | Q(faculty__icontains=q)
            | Q(major__icontains=q)
        )
    if gender:
        qs = qs.filter(gender=gender)
    if degree_level:
        qs = qs.filter(degree_level=degree_level)
    if level:
        qs = qs.filter(level=level)
    if marital_status:
        qs = qs.filter(marital_status=marital_status)
    return qs


# --- Audit logging on update --------------------------------------------------


def log_student_update(request, form, previous_values, instance):
    """Log audit + security events for a changed Student, comparing pre/post values.

    Shared by the regular profile update and the staff update views.
    """
    changed = [
        f
        for f in form.fields.keys()
        if hasattr(instance, f) and previous_values.get(f) != getattr(instance, f)
    ]
    if not changed:
        return
    audit_logger.log_profile_update(
        request=request, updated_fields=changed, success=True, errors=None
    )
    security_logger.log_data_modification(
        request=request,
        action="UPDATE" if not instance.is_draft else "UPDATE_DRAFT",
        model="Student",
        record_id=str(instance.pk),
        success=True,
    )


def capture_previous_values(form, instance):
    """Snapshot the current model field values for later change detection."""
    return {f: getattr(instance, f) for f in form.fields.keys() if hasattr(instance, f)}


def country_code_options():
    """Thin wrapper so views import the choices from one place."""
    return get_country_code_choices()


# Re-export for convenience.
__all__ = [
    "Student",
    "EmailVerification",
    "logger",
    "STUDENT_BASIC_FIELDS",
    "STAFF_BASIC_FIELDS",
    "ACADEMIC_FIELDS",
    "IDENTITY_EXTRA_FIELDS",
    "GUARDIAN_FIELDS",
    "HEALTH_FIELDS",
    "FINANCIAL_FIELDS",
    "STUDENT_FILTER_PARAMS",
    "generate_verification_code",
    "create_email_verification",
    "send_verification_email",
    "get_interest_categories_context",
    "get_interests_grouped",
    "save_student_interests",
    "build_interest_context",
    "apply_student_filters",
    "log_student_update",
    "capture_previous_values",
    "country_code_options",
]
