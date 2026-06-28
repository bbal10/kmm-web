"""Staff-facing student management views: list/search, detail, create, update,
delete, password reset, and CSV export."""

import csv
import logging
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.crypto import get_random_string
from django.utils.http import urlencode
from django.utils.text import slugify
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from ..forms import StaffStudentCreateForm, StaffStudentForm
from ..models import Student
from ..utils.logging_utils import audit_logger, security_logger
from .helpers import (
    ACADEMIC_FIELDS,
    HEALTH_FIELDS,
    IDENTITY_EXTRA_FIELDS,
    STAFF_BASIC_FIELDS,
    STUDENT_FILTER_PARAMS,
    apply_student_filters,
    build_interest_context,
    capture_previous_values,
    country_code_options,
    get_interests_grouped,
    log_student_update,
    save_student_interests,
)

logger = logging.getLogger("data_management.views")


class StaffDashboardDataListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = "dashboard/staff/staff_dashboard_list.html"
    context_object_name = "students"
    paginate_by = 10
    ordering = ["user__first_name"]
    allowed_sort_fields = [
        "user__first_name",
        "user__email",
        "degree_level",
        "semester_level",
        "faculty",
        "major",
        "level",
    ]

    def dispatch(self, request, *args, **kwargs):
        # Permission check
        if not request.user.is_staff:
            security_logger.log_access_attempt(
                request=request,
                resource="Staff Dashboard Data List",
                granted=False,
                reason="User is not a staff member",
            )
            raise Http404("You do not have permission to view this page.")
        security_logger.log_access_attempt(
            request=request, resource="Staff Dashboard Data List", granted=True
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = apply_student_filters(super().get_queryset().select_related("user"), self.request.GET)
        sort = self.request.GET.get("sort", "").strip()
        direction = self.request.GET.get("dir", "asc")
        if sort in self.allowed_sort_fields:
            ordering = f"{'-' if direction == 'desc' else ''}{sort}"
            qs = qs.order_by(ordering)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["query"] = self.request.GET.get("q", "")
        ctx["selected_gender"] = self.request.GET.get("gender", "")
        ctx["selected_degree_level"] = self.request.GET.get("degree_level", "")
        ctx["selected_level"] = self.request.GET.get("level", "")
        ctx["selected_marital_status"] = self.request.GET.get("marital_status", "")
        ctx["gender_choices"] = Student.GENDER_CHOICES
        ctx["degree_choices"] = Student.DEGREE_LEVEL_CHOICES
        ctx["level_choices"] = Student.LEVEL_CHOICES
        ctx["marital_choices"] = Student.MARITAL_STATUS_CHOICES
        ctx["current_sort"] = self.request.GET.get("sort", "")
        ctx["current_dir"] = self.request.GET.get("dir", "asc")
        filter_params = {}
        for p in STUDENT_FILTER_PARAMS:
            val = self.request.GET.get(p)
            if val:
                filter_params[p] = val
        ctx["base_filter_query"] = urlencode(filter_params)
        # Stats
        ctx["total_students"] = Student.objects.count()
        ctx["filtered_students"] = (
            ctx["paginator"].count if "paginator" in ctx else ctx["total_students"]
        )
        ctx["is_filtered"] = ctx["filtered_students"] != ctx["total_students"]
        return ctx


class StaffStudentDetailView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = "dashboard/staff/staff_student_detail.html"
    context_object_name = "student"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            security_logger.log_access_attempt(
                request=request,
                resource="Staff Student Detail",
                granted=False,
                reason="User is not a staff member",
            )
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        creds = self.request.session.pop("new_student_credentials", None)
        if creds:
            ctx["new_student_credentials"] = creds
        reset_creds = self.request.session.pop("reset_student_credentials", None)
        if reset_creds:
            ctx["reset_student_credentials"] = reset_creds
        ctx["interests_by_category"] = get_interests_grouped(self.object)
        return ctx


class StaffStudentUpdateView(LoginRequiredMixin, UpdateView):
    model = Student
    form_class = StaffStudentForm
    template_name = "dashboard/staff/staff_student_form.html"
    context_object_name = "student"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            security_logger.log_access_attempt(
                request=request,
                resource="Staff Student Edit",
                granted=False,
                reason="User is not a staff member",
            )
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if self.object and self.object.user:
            initial["email"] = self.object.user.email
            initial["first_name"] = self.object.user.first_name
            initial["last_name"] = self.object.user.last_name
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "basic_fields": STAFF_BASIC_FIELDS,
                "academic_fields": ACADEMIC_FIELDS,
                "identity_extra_fields": IDENTITY_EXTRA_FIELDS,
                "health_fields": HEALTH_FIELDS,
                "organization_field": "organization_history",
                "next_url": self.request.GET.get("next") or self.request.POST.get("next") or "",
                "country_code_options": country_code_options(),
                **build_interest_context(self.object),
            }
        )
        return ctx

    def form_valid(self, form):
        # Save user fields first
        if self.object and self.object.user:
            self.object.user.email = form.cleaned_data.get("email", "")
            self.object.user.first_name = form.cleaned_data.get("first_name", "")
            self.object.user.last_name = form.cleaned_data.get("last_name", "")
            self.object.user.save()

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

    def get_success_url(self):
        action = self.request.POST.get("action") or self.request.GET.get("action")
        if action == "save_back":
            return (
                self.request.POST.get("next")
                or self.request.GET.get("next")
                or reverse_lazy("data_management:staff_student_list")
            )
        # For draft remain on edit page
        if action == "save_draft":
            return reverse_lazy("data_management:staff_student_edit", kwargs={"pk": self.object.pk})
        # Default behavior
        next_param = self.request.GET.get("next") or self.request.POST.get("next")
        if next_param:
            return next_param
        return reverse_lazy("data_management:staff_student_detail", kwargs={"pk": self.object.pk})


class StaffStudentCreateView(LoginRequiredMixin, CreateView):
    model = Student
    form_class = StaffStudentCreateForm
    template_name = "dashboard/staff/staff_student_create_form.html"
    context_object_name = "student"

    def dispatch(self, request, *args, **kwargs):
        logger.info(
            "[StaffStudentCreateView] dispatch start user=%s path=%s",
            request.user.username,
            request.path,
        )
        if not request.user.is_staff:
            logger.warning(
                "[StaffStudentCreateView] access denied user=%s not in staff group",
                request.user.username,
            )
            security_logger.log_access_attempt(
                request=request,
                resource="Staff Student Create",
                granted=False,
                reason="User is not a staff member",
            )
            raise Http404()
        security_logger.log_access_attempt(
            request=request, resource="Staff Student Create", granted=True
        )
        logger.info("[StaffStudentCreateView] access granted user=%s", request.user.username)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "basic_fields": STAFF_BASIC_FIELDS,
                "academic_fields": ACADEMIC_FIELDS,
                "identity_extra_fields": IDENTITY_EXTRA_FIELDS,
                "health_fields": HEALTH_FIELDS,
                "organization_field": "organization_history",
                "next_url": self.request.GET.get("next") or self.request.POST.get("next") or "",
                "country_code_options": country_code_options(),
                **build_interest_context(self.object),
            }
        )
        return ctx

    def form_valid(self, form):
        action = self.request.POST.get("action", "save")
        logger.info(
            "[StaffStudentCreateView] form_valid start user=%s action=%s draft=%s incoming_fields=%s",
            self.request.user.username,
            action,
            (action == "save_draft"),
            list(form.cleaned_data.keys()),
        )
        form.instance.is_draft = action == "save_draft"
        try:
            with transaction.atomic():
                pending_student = form.instance
                User = get_user_model()

                # Get user data from form cleaned_data
                email = form.cleaned_data.get("email", "")
                first_name = form.cleaned_data.get("first_name", "")
                last_name = form.cleaned_data.get("last_name", "")

                # Generate username from email or first name
                base_username_source = email.split("@")[0] if email else first_name
                base_username = slugify(base_username_source) or "user"
                username = base_username
                i = 1
                while User.objects.filter(username=username).exists():
                    i += 1
                    username = f"{base_username}{i}"
                logger.info(
                    "[StaffStudentCreateView] generated username=%s base=%s",
                    username,
                    base_username,
                )
                password_plain = get_random_string(12)

                # Create user with form data
                user = User(
                    username=username, email=email, first_name=first_name, last_name=last_name
                )
                user.set_password(password_plain)
                user.save()
                logger.info(
                    "[StaffStudentCreateView] user created id=%s email=%s", user.id, user.email
                )
                existing_student = Student.objects.filter(user=user).first()
                if existing_student:
                    logger.info(
                        "[StaffStudentCreateView] reusing signal-created student id=%s",
                        existing_student.id,
                    )
                    updated_fields = []
                    for field in form.fields.keys():
                        if hasattr(existing_student, field) and field in form.cleaned_data:
                            old_val = getattr(existing_student, field)
                            new_val = form.cleaned_data[field]
                            if old_val != new_val:
                                updated_fields.append(field)
                                setattr(existing_student, field, new_val)
                    existing_student.is_draft = pending_student.is_draft
                    existing_student.save()
                    logger.info(
                        "[StaffStudentCreateView] student updated id=%s changed_fields=%s",
                        existing_student.id,
                        updated_fields,
                    )
                    self.object = existing_student
                else:
                    logger.warning(
                        "[StaffStudentCreateView] no signal-created student found; using fallback creation path"
                    )
                    pending_student.user = user
                    response = super().form_valid(form)
                    self.object = form.instance
                    logger.info(
                        "[StaffStudentCreateView] fallback student created id=%s", self.object.id
                    )
                self.request.session["new_student_credentials"] = {
                    "username": user.username,
                    "password": password_plain,
                    "student_id": str(self.object.pk),
                }
                logger.info(
                    "[StaffStudentCreateView] credentials stored in session for student_id=%s",
                    self.object.pk,
                )
                if self.object.email:
                    try:
                        login_url = self.request.build_absolute_uri("/")
                        message = (
                            f"Halo {self.object.full_name},\n\n"
                            f"Akun Anda telah dibuat di sistem KMM Mesir.\n\n"
                            f"Username: {user.username}\nPassword: {password_plain}\n\n"
                            f"Silakan login di: {login_url}\nSegera ganti password setelah login.\n\n"
                            f"Terima kasih."
                        )
                        send_mail(
                            subject="Akun KMM Mesir Anda",
                            message=message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[self.object.email],
                            fail_silently=True,
                        )
                        logger.info(
                            "[StaffStudentCreateView] credential email queued to %s",
                            self.object.email,
                        )
                    except Exception as mail_exc:
                        logger.error(
                            "[StaffStudentCreateView] email send failure student_id=%s error=%s",
                            self.object.pk,
                            mail_exc,
                            exc_info=True,
                        )
                security_logger.log_data_modification(
                    request=self.request,
                    action="CREATE",
                    model="User",
                    record_id=str(user.pk),
                    success=True,
                )
                audit_logger.log_profile_update(
                    request=self.request,
                    updated_fields=list(form.cleaned_data.keys()),
                    success=True,
                )
                security_logger.log_data_modification(
                    request=self.request,
                    action="CREATE_DRAFT" if self.object.is_draft else "CREATE",
                    model="Student",
                    record_id=str(self.object.id),
                    success=True,
                )
                save_student_interests(self.object, self.request.POST)
            if existing_student:
                target_url = self.get_success_url()
                logger.info(
                    "[StaffStudentCreateView] redirecting (reuse path) student_id=%s to %s",
                    self.object.pk,
                    target_url,
                )
                return redirect(target_url)
            logger.info(
                "[StaffStudentCreateView] redirecting (fallback path) student_id=%s", self.object.pk
            )
            return response
        except Exception as e:
            logger.error(
                "[StaffStudentCreateView] form_valid exception user=%s error=%s",
                self.request.user.username,
                e,
                exc_info=True,
            )
            audit_logger.log_profile_update(
                request=self.request,
                updated_fields=list(getattr(form, "cleaned_data", {}).keys()),
                success=False,
                errors={"general": str(e)},
            )
            raise

    def get_success_url(self):
        action = self.request.POST.get("action") or self.request.GET.get("action")
        if action == "save_back":
            url = (
                self.request.POST.get("next")
                or self.request.GET.get("next")
                or reverse_lazy("data_management:staff_student_list")
            )
            logger.info("[StaffStudentCreateView] get_success_url action=save_back url=%s", url)
            return url
        if action == "save_draft":
            url = reverse_lazy("data_management:staff_student_edit", kwargs={"pk": self.object.pk})
            logger.info("[StaffStudentCreateView] get_success_url action=save_draft url=%s", url)
            return url
        next_param = self.request.GET.get("next") or self.request.POST.get("next")
        if next_param:
            logger.info("[StaffStudentCreateView] get_success_url next_param=%s", next_param)
            return next_param
        url = reverse_lazy("data_management:staff_student_detail", kwargs={"pk": self.object.pk})
        logger.info("[StaffStudentCreateView] get_success_url default detail url=%s", url)
        return url


class StaffStudentDeleteView(LoginRequiredMixin, DeleteView):
    model = Student
    template_name = "dashboard/staff/staff_student_confirm_delete.html"
    context_object_name = "student"
    success_url = reverse_lazy("data_management:staff_student_list")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            security_logger.log_access_attempt(
                request=request,
                resource="Staff Student Delete",
                granted=False,
                reason="User is not a staff member",
            )
            raise Http404()
        security_logger.log_access_attempt(
            request=request, resource="Staff Student Delete", granted=True
        )
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        student_id = str(self.object.pk)
        student_name = self.object.full_name
        response = super().delete(request, *args, **kwargs)
        security_logger.log_data_modification(
            request=request, action="DELETE", model="Student", record_id=student_id, success=True
        )
        messages.success(request, f"Data mahasiswa '{student_name}' berhasil dihapus.")
        return response


@login_required
def staff_student_reset_password(request, pk):
    """Reset a student's password (staff action)."""
    if request.method != "POST":
        raise Http404()
    if not request.user.is_staff:
        raise Http404()
    student = get_object_or_404(Student, pk=pk)
    if not student.user:
        raise Http404()
    user = student.user
    # Generate new secure password
    new_password = secrets.token_urlsafe(10)
    user.set_password(new_password)
    user.save()
    # Store one-time display
    request.session["reset_student_credentials"] = {
        "username": user.username,
        "password": new_password,
        "student_id": str(student.pk),
    }
    # Email the new password
    if student.email:
        try:
            message = (
                f"Halo {student.full_name},\n\nPassword akun Anda telah direset oleh staff.\n\n"
                f"Username: {user.username}\nPassword baru: {new_password}\n\n"
                f"Segera login dan ganti password ini demi keamanan.\n\nTerima kasih."
            )
            send_mail(
                subject="Reset Password Akun KMM Mesir",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student.email],
                fail_silently=True,
            )
        except Exception:
            pass
    security_logger.log_data_modification(
        request=request, action="UPDATE", model="User", record_id=str(user.pk), success=True
    )
    return redirect("data_management:staff_student_detail", pk=student.pk)


def export_students_csv(request):
    if (
        not request.user.is_authenticated
        or not request.user.groups.filter(name="data_management_staff").exists()
    ):
        raise Http404()
    # Reuse the same filtering logic as the list view so the export matches
    # what the staff member sees on screen.
    qs = apply_student_filters(Student.objects.all(), request.GET)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="students.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "Full Name",
            "Email",
            "Passport",
            "Degree",
            "Tingkat",
            "Faculty",
            "Major",
            "Level",
            "Membership",
        ]
    )
    for s in qs.iterator():
        writer.writerow(
            [
                s.full_name,
                s.email,
                s.passport_number or "",
                s.degree_level,
                s.get_semester_level_display() if s.semester_level else "",
                s.faculty_display,
                s.major_display,
                s.get_level_display(),
                s.get_membership_status_display() if s.membership_status else "",
            ]
        )
    return response
