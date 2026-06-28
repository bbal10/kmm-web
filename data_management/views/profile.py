"""Student-facing profile views: dashboard redirect, profile detail, and
profile edit."""

import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, UpdateView

from ..forms import StudentForm
from ..models import Student
from ..utils.logging_utils import get_user_info, log_user_action
from .helpers import (
    ACADEMIC_FIELDS,
    FINANCIAL_FIELDS,
    GUARDIAN_FIELDS,
    HEALTH_FIELDS,
    IDENTITY_EXTRA_FIELDS,
    STUDENT_BASIC_FIELDS,
    build_interest_context,
    capture_previous_values,
    country_code_options,
    get_interests_grouped,
    log_student_update,
    save_student_interests,
)

logger = logging.getLogger("data_management.views")


@login_required
@log_user_action("data_management.views")
def dashboard(request):
    """Dashboard view for authenticated users."""
    try:
        user_info = get_user_info(request)

        if request.user.groups.filter(name="data_management_staff").exists():
            logger.info(f"Staff member accessed dashboard - User: {user_info['username']}")
        else:
            logger.info(f"Regular user accessed dashboard - User: {user_info['username']}")

        return redirect("data_management:profile")
    except Exception as e:
        logger.error(
            f"Dashboard view error - User: {request.user.username}, Error: {str(e)}", exc_info=True
        )
        raise


class StudentDataDetailView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = "dashboard/student_data/student_data_detail.html"
    context_object_name = "student_data"

    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to add logging."""
        user_info = get_user_info(request)
        logger.info(
            f"Student data detail view accessed - User: {user_info['username']}, IP: {user_info['ip']}"
        )
        # Removed redirect so staff remain on profile page with summary
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        """Get student data for the authenticated user unless staff (staff sees only basic user info)."""
        try:
            user = self.request.user
            if user.is_staff or user.groups.filter(name="data_management_staff").exists():
                logger.info("Student data detail skipped for staff user=%s", user.username)
                return None
            logger.info(f"Student data detail requested - User: {user.username}")
            student_data = self.model.objects.get(user=user)
            logger.info(f"Student data retrieved successfully - User: {user.username}")
            return student_data
        except self.model.DoesNotExist:
            logger.warning(f"Student data not found - User: {self.request.user.username}")
            return None
        except Exception as e:
            logger.error(
                f"Error retrieving student data - User: {self.request.user.username}, Error: {str(e)}",
                exc_info=True,
            )
            return None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        is_staff = user.is_staff or user.groups.filter(name="data_management_staff").exists()
        ctx["is_staff_view"] = is_staff
        ctx["basic_user"] = user if is_staff else None
        if self.object:
            ctx["interests_by_category"] = get_interests_grouped(self.object)
        else:
            ctx["interests_by_category"] = []
        return ctx


class StudentDataUpdateView(LoginRequiredMixin, UpdateView):
    model = Student
    template_name = "dashboard/student_data/student_data_form.html"
    form_class = StudentForm
    success_url = reverse_lazy("data_management:profile")

    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to add logging."""
        user_info = get_user_info(request)
        logger.info(
            f"Student data update view accessed - User: {user_info['username']}, IP: {user_info['ip']}"
        )
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        """Get student object for update."""
        try:
            logger.info(f"Student data update requested - User: {self.request.user.username}")
            return get_object_or_404(self.model, user=self.request.user)
        except Exception as e:
            logger.error(
                f"Error getting student object for update - User: {self.request.user.username}, Error: {str(e)}",
                exc_info=True,
            )
            raise

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "basic_fields": STUDENT_BASIC_FIELDS,
                "academic_fields": ACADEMIC_FIELDS,
                "identity_extra_fields": IDENTITY_EXTRA_FIELDS,
                "guardian_fields": GUARDIAN_FIELDS,
                "health_fields": HEALTH_FIELDS,
                "financial_fields": FINANCIAL_FIELDS,
                "organization_field": "organization_history",
                "photo_field": "photo",
                "country_code_options": country_code_options(),
                **build_interest_context(self.object),
            }
        )
        return ctx

    def form_valid(self, form):
        action = self.request.POST.get("action", "save")
        # Capture previous values before save for change detection.
        previous_values = capture_previous_values(form, self.get_object())
        # Set draft status based on action prior to saving
        form.instance.is_draft = action == "save_draft"
        response = super().form_valid(form)
        save_student_interests(self.object, self.request.POST)
        if action in ["save", "save_back", "save_draft"]:
            log_student_update(self.request, form, previous_values, self.object)
        return response
