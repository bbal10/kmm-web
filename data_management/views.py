import csv
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.http import urlencode
from django.utils.text import slugify
from django.views.generic import DetailView, UpdateView, ListView, CreateView, DeleteView

from .forms import (
    get_country_code_choices,
    UserRegistrationForm,
    UserLoginForm,
    StudentForm,
    StaffStudentForm,
    StaffStudentCreateForm,
)
from .models import EmailVerification, Interest, InterestCategory, Student, StudentInterest
from .utils.logging_utils import security_logger, audit_logger, get_user_info, log_user_action

# Configure logger with proper naming convention
logger = logging.getLogger(__name__)

User = get_user_model()


def _generate_verification_code():
    """Generate a secure 6-digit numeric verification code."""
    return str(secrets.randbelow(1000000)).zfill(6)


def _create_email_verification(user):
    """Create (or refresh) an EmailVerification record for *user* and return it.

    Note: ``last_resend_at`` is intentionally left as ``None`` here. Callers
    must update it to ``timezone.now()`` only *after* the verification email
    has been sent successfully, so that a failed send does not start the
    resend cooldown.
    """
    expires_at = timezone.now() + timedelta(minutes=EmailVerification.EXPIRY_MINUTES)
    code = _generate_verification_code()
    verification, _ = EmailVerification.objects.update_or_create(
        user=user,
        defaults={
            'code': code,
            'expires_at': expires_at,
            'attempt_count': 0,
            'last_resend_at': None,
        },
    )
    return verification


def _send_verification_email(user, code):
    """Send an email verification code to *user*.

    Returns ``True`` on success, ``False`` on failure (the error is logged but
    *not* re-raised so the view can show a friendly message instead of a 500).
    """
    subject = 'Verifikasi Email - KMM Mesir'
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


def _get_interest_categories_context():
    """Return InterestCategory queryset with prefetched interests for template context."""
    return InterestCategory.objects.prefetch_related('interests').all()


def _get_interests_grouped(student):
    """Return interests grouped by category for detail templates."""
    categories = InterestCategory.objects.prefetch_related('interests').all()
    selected = {
        si.interest_id: si
        for si in student.student_interests.select_related('interest__category').all()
    }
    result = []
    for cat in categories:
        items = [selected[i.pk] for i in cat.interests.all() if i.pk in selected]
        if items:
            result.append({'category': cat, 'items': items})
    return result


def _save_student_interests(student, post_data):
    """Sync StudentInterest records from POST data.

    Expected POST keys:
      - interest_ids   : list of Interest PKs that are checked
      - custom_interest_<pk> : custom text for 'Isi Sendiri' interests
    """
    checked_ids = set(map(int, post_data.getlist('interest_ids')))

    # Remove unchecked
    StudentInterest.objects.filter(student=student).exclude(interest_id__in=checked_ids).delete()

    # Upsert checked
    existing = {si.interest_id: si for si in StudentInterest.objects.filter(student=student)}
    for interest_id in checked_ids:
        custom = post_data.get(f'custom_interest_{interest_id}', '').strip()
        if interest_id in existing:
            si = existing[interest_id]
            if si.custom_value != custom:
                si.custom_value = custom
                si.save(update_fields=['custom_value'])
        else:
            StudentInterest.objects.create(student=student, interest_id=interest_id, custom_value=custom)


@login_required
@log_user_action('data_management.views')
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
        logger.error(f"Dashboard view error - User: {request.user.username}, Error: {str(e)}", exc_info=True)
        raise


class StudentDataDetailView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = 'dashboard/student_data/student_data_detail.html'
    context_object_name = 'student_data'

    def dispatch(self, request, *args, **kwargs):
        """Override dispatch                                            to add logging."""
        user_info = get_user_info(request)
        logger.info(f"Student data detail view accessed - User: {user_info['username']}, IP: {user_info['ip']}")
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
            logger.error(f"Error retrieving student data - User: {self.request.user.username}, Error: {str(e)}",
                         exc_info=True)
            return None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        is_staff = user.is_staff or user.groups.filter(name="data_management_staff").exists()
        ctx['is_staff_view'] = is_staff
        ctx['basic_user'] = user if is_staff else None
        if self.object:
            ctx['interests_by_category'] = _get_interests_grouped(self.object)
        else:
            ctx['interests_by_category'] = []
        return ctx


class StudentDataUpdateView(LoginRequiredMixin, UpdateView):
    model = Student
    template_name = 'dashboard/student_data/student_data_form.html'
    form_class = StudentForm
    success_url = reverse_lazy('data_management:profile')

    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to add logging."""
        user_info = get_user_info(request)
        logger.info(f"Student data update view accessed - User: {user_info['username']}, IP: {user_info['ip']}")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        """Get student object for update."""
        try:
            logger.info(f"Student data update requested - User: {self.request.user.username}")
            return get_object_or_404(self.model, user=self.request.user)
        except Exception as e:
            logger.error(
                f"Error getting student object for update - User: {self.request.user.username}, Error: {str(e)}",
                exc_info=True)
            raise

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'basic_fields': [
                'whatsapp_number', 'birth_place', 'birth_date', 'gender',
                'marital_status', 'membership_status', 'region_origin',
                'parents_name', 'parents_phone'
            ],
            'academic_fields': [
                'institution', 'institution_custom', 'faculty', 'faculty_custom',
                'major', 'major_custom', 'degree_level', 'semester_level', 'latest_grade', 'level'
            ],
            'identity_extra_fields': [
                'passport_number', 'nik', 'lapdik_number', 'arrival_date', 'school_origin',
                'home_name', 'home_location'
            ],
            'guardian_fields': ['photo_url', 'guardian_name', 'guardian_phone'],
            'health_fields': ['disease_history', 'disease_status'],
            'interest_categories': _get_interest_categories_context(),
            'selected_interest_ids': set(
                self.object.student_interests.values_list('interest_id', flat=True)
            ) if self.object.pk else set(),
            'student_interest_customs': {
                si.interest_id: si.custom_value
                for si in self.object.student_interests.all()
            } if self.object.pk else {},
            'financial_fields': [
                'education_funding', 'scholarship_source',
                'living_cost', 'monthly_income'
            ],
            'organization_field': 'organization_history',
            'photo_field': 'photo',
            'country_code_options': get_country_code_choices(),
        })
        return ctx

    def form_valid(self, form):
        action = self.request.POST.get('action', 'save')
        # Capture previous values before save for change detection
        # Get form fields dynamically since StudentForm uses 'exclude' instead of 'fields'
        form_fields = list(form.fields.keys())
        previous_values = {f: getattr(self.get_object(), f) for f in form_fields if hasattr(self.get_object(), f)}
        # Set draft status based on action prior to saving
        form.instance.is_draft = (action == 'save_draft')
        response = super().form_valid(form)
        _save_student_interests(self.object, self.request.POST)
        if action in ['save', 'save_back', 'save_draft']:
            changed = []
            for f in form_fields:
                if not hasattr(self.object, f):
                    continue
                if previous_values.get(f) != getattr(self.object, f):
                    changed.append(f)
            if changed:
                audit_logger.log_profile_update(
                    request=self.request,
                    updated_fields=changed,
                    success=True,
                    errors=None
                )
                security_logger.log_data_modification(
                    request=self.request,
                    action="UPDATE" if not self.object.is_draft else "UPDATE_DRAFT",
                    model="Student",
                    record_id=str(self.object.pk),
                    success=True
                )
        return response


def register(request):
    """User registration view."""
    user_info = get_user_info(request)

    if request.method == 'POST':
        try:
            form = UserRegistrationForm(request.POST)

            if form.is_valid():
                user = form.save(commit=False)
                # Deactivate until email is verified
                user.is_active = False
                user.save()
                username = user.username

                # Log successful registration
                audit_logger.log_user_registration(
                    request=request,
                    username=username,
                    success=True
                )

                security_logger.log_data_modification(
                    request=request,
                    action="CREATE",
                    model="User",
                    record_id=str(user.id),
                    success=True
                )

                # Create verification record and send email
                verification = _create_email_verification(user)
                email_sent = _send_verification_email(user, verification.code)
                if email_sent:
                    verification.last_resend_at = timezone.now()
                    verification.save(update_fields=['last_resend_at'])

                # Store pending user in session for the verify-email view
                request.session['pending_verification_user_id'] = user.id

                if email_sent:
                    messages.info(
                        request,
                        f'Pendaftaran berhasil! Kode verifikasi telah dikirim ke {user.email}. '
                        f'Silakan cek email Anda.'
                    )
                else:
                    messages.warning(
                        request,
                        f'Pendaftaran berhasil, namun gagal mengirim email ke {user.email}. '
                        f'Gunakan tombol "Kirim Ulang" untuk mencoba lagi.'
                    )

                return redirect('data_management:verify_email')
            else:
                # Log failed registration
                audit_logger.log_user_registration(
                    request=request,
                    username=form.data.get('username', 'Unknown'),
                    success=False,
                    errors=dict(form.errors)
                )

        except Exception as e:
            logger.error(f"Registration error - IP: {user_info['ip']}, Error: {str(e)}", exc_info=True)
            # Re-initialize form on error
            form = UserRegistrationForm()
    else:
        logger.info(f"Registration page accessed from IP: {user_info['ip']}")
        form = UserRegistrationForm()

    return render(request, 'register.html', {'form': form})


def user_login(request):
    """User login view with HTMX support."""
    user_info = get_user_info(request)

    if request.method == 'POST':
        try:
            form = UserLoginForm(request.POST)

            if form.is_valid():
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']

                user = authenticate(request, username=username, password=password)
                if user is not None:
                    login(request, user)

                    # Log successful login
                    security_logger.log_login_attempt(
                        request=request,
                        username=username,
                        success=True,
                        is_staff=False
                    )

                    # Add success message for login
                    messages.success(
                        request,
                        f'Selamat datang kembali, {user.get_full_name() or user.username}! Login berhasil.'
                    )

                    # For HTMX requests, return redirect header
                    if request.htmx:
                        response = HttpResponse()
                        response['HX-Redirect'] = reverse_lazy('data_management:dashboard')
                        return response

                    return redirect('data_management:dashboard')
                else:
                    # Check if the user exists but is inactive (email not yet verified)
                    try:
                        inactive_user = User.objects.get(username=username, is_active=False)
                        if inactive_user.check_password(password) and hasattr(inactive_user, 'email_verification'):
                            # Re-use (or refresh) the pending verification session
                            request.session['pending_verification_user_id'] = inactive_user.id
                            security_logger.log_login_attempt(
                                request=request,
                                username=username,
                                success=False,
                                is_staff=False,
                                additional_info="Email not verified"
                            )
                            messages.warning(
                                request,
                                'Akun Anda belum diverifikasi. Silakan cek email Anda untuk kode verifikasi.'
                            )
                            if request.htmx:
                                response = HttpResponse()
                                response['HX-Redirect'] = reverse_lazy('data_management:verify_email')
                                return response
                            return redirect('data_management:verify_email')
                    except User.DoesNotExist:
                        pass

                    # Log failed login
                    security_logger.log_login_attempt(
                        request=request,
                        username=username,
                        success=False,
                        is_staff=False,
                        additional_info="Invalid credentials"
                    )

                    form.add_error(None, 'Nama pengguna atau kata sandi salah')
            else:
                logger.warning(f"Login failed - Invalid form data, IP: {user_info['ip']}, Errors: {form.errors}")

            # For HTMX requests, return only the form partial
            if request.htmx:
                return render(request, 'partials/login_form.html', {'form': form})

        except Exception as e:
            logger.error(f"Login error - IP: {user_info['ip']}, Error: {str(e)}", exc_info=True)
            form = UserLoginForm()
            if request.htmx:
                return render(request, 'partials/login_form.html', {'form': form})
    else:
        logger.info(f"Login page accessed from IP: {user_info['ip']}")
        form = UserLoginForm()

    return render(request, 'login.html', {'form': form})


def verify_email(request):
    """Display the email verification page and handle code submission."""
    user_id = request.session.get('pending_verification_user_id')
    if not user_id:
        return redirect('data_management:login')

    user = User.objects.filter(id=user_id, is_active=False).first()
    if user is None:
        request.session.pop('pending_verification_user_id', None)
        messages.info(
            request,
            'Verifikasi email tidak lagi diperlukan. Silakan login dengan akun Anda.'
        )
        return redirect('data_management:login')

    try:
        verification = user.email_verification
    except EmailVerification.DoesNotExist:
        messages.error(request, 'Data verifikasi tidak ditemukan. Silakan daftar ulang.')
        return redirect('data_management:register')

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()

        if verification.is_expired():
            messages.error(
                request,
                'Kode verifikasi telah kedaluwarsa. Silakan kirim ulang kode.'
            )
        elif verification.attempt_count >= EmailVerification.MAX_ATTEMPTS:
            messages.error(
                request,
                'Terlalu banyak percobaan kode yang salah. Silakan kirim ulang kode baru.'
            )
        elif code == verification.code:
            # Activate user
            user.is_active = True
            user.save(update_fields=['is_active'])
            verification.delete()
            del request.session['pending_verification_user_id']

            audit_logger.log_user_registration(
                request=request,
                username=user.username,
                success=True,
            )
            logger.info("Email verified for user=%s", user.username)
            messages.success(
                request,
                'Email berhasil diverifikasi! Silakan login dengan akun Anda.'
            )
            return redirect('data_management:login')
        else:
            verification.attempt_count += 1
            verification.save(update_fields=['attempt_count'])
            remaining = EmailVerification.MAX_ATTEMPTS - verification.attempt_count
            messages.error(
                request,
                f'Kode verifikasi salah. Sisa percobaan: {remaining}.'
                if remaining > 0
                else 'Kode verifikasi salah. Tidak ada sisa percobaan. Silakan kirim ulang kode.'
            )

    context = {
        'email': user.email,
        'can_resend': verification.can_resend(),
        'seconds_until_resend': verification.seconds_until_resend(),
    }
    return render(request, 'verify_email.html', context)


def resend_verification_code(request):
    """Resend a new verification code to the user's email."""
    if request.method != 'POST':
        return redirect('data_management:verify_email')

    user_id = request.session.get('pending_verification_user_id')
    if not user_id:
        return redirect('data_management:login')

    user = User.objects.filter(id=user_id, is_active=False).first()
    if user is None:
        request.session.pop('pending_verification_user_id', None)
        messages.info(
            request,
            'Verifikasi email tidak lagi diperlukan. Silakan login dengan akun Anda.'
        )
        return redirect('data_management:login')

    try:
        verification = user.email_verification
    except EmailVerification.DoesNotExist:
        messages.error(request, 'Data verifikasi tidak ditemukan. Silakan daftar ulang.')
        return redirect('data_management:register')

    if not verification.can_resend():
        seconds = verification.seconds_until_resend()
        messages.warning(
            request,
            f'Mohon tunggu {seconds} detik sebelum mengirim ulang kode.'
        )
        return redirect('data_management:verify_email')

    verification = _create_email_verification(user)
    email_sent = _send_verification_email(user, verification.code)
    if email_sent:
        verification.last_resend_at = timezone.now()
        verification.save(update_fields=['last_resend_at'])
        logger.info("Resent verification code for user=%s", user.username)
        messages.success(
            request,
            f'Kode verifikasi baru telah dikirim ke {user.email}.'
        )
    else:
        messages.error(
            request,
            f'Gagal mengirim email ke {user.email}. Silakan coba lagi.'
        )
    return redirect('data_management:verify_email')


def staff_login(request):
    """Staff login view with HTMX support."""
    user_info = get_user_info(request)

    if request.method == 'POST':
        try:
            form = UserLoginForm(request.POST)

            if form.is_valid():
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']

                user = authenticate(request, username=username, password=password)
                if user is not None and user.is_staff:
                    login(request, user)

                    # Log successful staff login
                    security_logger.log_login_attempt(
                        request=request,
                        username=username,
                        success=True,
                        is_staff=True
                    )

                    # Add success message for staff login
                    messages.success(
                        request,
                        f'Selamat datang, {user.get_full_name() or user.username}! Login staff berhasil.'
                    )

                    # For HTMX requests, return redirect header
                    if request.htmx:
                        response = HttpResponse()
                        response['HX-Redirect'] = reverse_lazy('data_management:dashboard')
                        return response

                    return redirect('data_management:dashboard')
                else:
                    if user is not None:
                        # Non-staff user attempted staff login
                        security_logger.log_login_attempt(
                            request=request,
                            username=username,
                            success=False,
                            is_staff=True,
                            additional_info="User is not staff member"
                        )
                    else:
                        # Invalid credentials
                        security_logger.log_login_attempt(
                            request=request,
                            username=username,
                            success=False,
                            is_staff=True,
                            additional_info="Invalid credentials"
                        )

                    form.add_error(None, 'Nama pengguna atau kata sandi salah atau bukan anggota staff')
            else:
                logger.warning(f"Staff login failed - Invalid form data, IP: {user_info['ip']}, Errors: {form.errors}")

            # For HTMX requests, return only the form partial
            if request.htmx:
                return render(request, 'partials/staff_login_form.html', {'form': form})

        except Exception as e:
            logger.error(f"Staff login error - IP: {user_info['ip']}, Error: {str(e)}", exc_info=True)
            form = UserLoginForm()
            if request.htmx:
                return render(request, 'partials/staff_login_form.html', {'form': form})
    else:
        logger.info(f"Staff login page accessed from IP: {user_info['ip']}")
        form = UserLoginForm()

    return render(request, 'staff_login.html', {'form': form})


class StaffDashboardDataListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = 'dashboard/staff/staff_dashboard_list.html'
    context_object_name = 'students'
    paginate_by = 10
    ordering = ['user__first_name']
    allowed_sort_fields = ['user__first_name', 'user__email', 'degree_level', 'semester_level', 'faculty', 'major',
                           'level']

    def dispatch(self, request, *args, **kwargs):
        # Permission check
        if not request.user.is_staff:
            security_logger.log_access_attempt(
                request=request,
                resource="Staff Dashboard Data List",
                granted=False,
                reason="User is not a staff member"
            )
            raise Http404("You do not have permission to view this page.")
        security_logger.log_access_attempt(
            request=request,
            resource="Staff Dashboard Data List",
            granted=True
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset().select_related('user')
        q = self.request.GET.get('q', '').strip()
        gender = self.request.GET.get('gender', '').strip()
        degree_level = self.request.GET.get('degree_level', '').strip()
        level = self.request.GET.get('level', '').strip()
        marital_status = self.request.GET.get('marital_status', '').strip()
        sort = self.request.GET.get('sort', '').strip()
        direction = self.request.GET.get('dir', 'asc')

        from django.db.models import Q
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(user__email__icontains=q) |
                Q(passport_number__icontains=q) |
                Q(nik__icontains=q) |
                Q(faculty__icontains=q) |
                Q(major__icontains=q)
            )
        if gender:
            qs = qs.filter(gender=gender)
        if degree_level:
            qs = qs.filter(degree_level=degree_level)
        if level:
            qs = qs.filter(level=level)
        if marital_status:
            qs = qs.filter(marital_status=marital_status)
        if sort in self.allowed_sort_fields:
            ordering = f"{'-' if direction == 'desc' else ''}{sort}"
            qs = qs.order_by(ordering)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['query'] = self.request.GET.get('q', '')
        ctx['selected_gender'] = self.request.GET.get('gender', '')
        ctx['selected_degree_level'] = self.request.GET.get('degree_level', '')
        ctx['selected_level'] = self.request.GET.get('level', '')
        ctx['selected_marital_status'] = self.request.GET.get('marital_status', '')
        ctx['gender_choices'] = Student.GENDER_CHOICES
        ctx['degree_choices'] = Student.DEGREE_LEVEL_CHOICES
        ctx['level_choices'] = Student.LEVEL_CHOICES
        ctx['marital_choices'] = Student.MARITAL_STATUS_CHOICES
        ctx['current_sort'] = self.request.GET.get('sort', '')
        ctx['current_dir'] = self.request.GET.get('dir', 'asc')
        filter_params = {}
        for p in ['q', 'gender', 'degree_level', 'level', 'marital_status']:
            val = self.request.GET.get(p)
            if val:
                filter_params[p] = val
        ctx['base_filter_query'] = urlencode(filter_params)
        # Stats
        ctx['total_students'] = Student.objects.count()
        ctx['filtered_students'] = ctx['paginator'].count if 'paginator' in ctx else ctx['total_students']
        ctx['is_filtered'] = ctx['filtered_students'] != ctx['total_students']
        return ctx


class StaffStudentDetailView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = 'dashboard/staff/staff_student_detail.html'
    context_object_name = 'student'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            security_logger.log_access_attempt(
                request=request,
                resource="Staff Student Detail",
                granted=False,
                reason="User is not a staff member"
            )
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        creds = self.request.session.pop('new_student_credentials', None)
        if creds:
            ctx['new_student_credentials'] = creds
        reset_creds = self.request.session.pop('reset_student_credentials', None)
        if reset_creds:
            ctx['reset_student_credentials'] = reset_creds
        ctx['interests_by_category'] = self._get_interests_grouped(self.object)
        return ctx

    @staticmethod
    def _get_interests_grouped(student):
        return _get_interests_grouped(student)


class StaffStudentUpdateView(LoginRequiredMixin, UpdateView):
    model = Student
    form_class = StaffStudentForm
    template_name = 'dashboard/staff/staff_student_form.html'
    context_object_name = 'student'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            security_logger.log_access_attempt(
                request=request,
                resource="Staff Student Edit",
                granted=False,
                reason="User is not a staff member"
            )
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if self.object and self.object.user:
            initial['email'] = self.object.user.email
            initial['first_name'] = self.object.user.first_name
            initial['last_name'] = self.object.user.last_name
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'basic_fields': [
                'email', 'first_name', 'last_name', 'whatsapp_number', 'birth_place', 'birth_date', 'gender',
                'marital_status', 'membership_status', 'region_origin',
                'parents_name', 'parents_phone'
            ],
            'academic_fields': [
                'institution', 'institution_custom', 'faculty', 'faculty_custom',
                'major', 'major_custom', 'degree_level', 'semester_level', 'latest_grade', 'level'
            ],
            'identity_extra_fields': [
                'passport_number', 'nik', 'lapdik_number', 'arrival_date', 'school_origin', 'home_name', 'home_location'
            ],
            'health_fields': ['disease_history', 'disease_status'],
            'interest_categories': _get_interest_categories_context(),
            'selected_interest_ids': set(
                self.object.student_interests.values_list('interest_id', flat=True)
            ) if self.object.pk else set(),
            'student_interest_customs': {
                si.interest_id: si.custom_value
                for si in self.object.student_interests.all()
            } if self.object.pk else {},
            'organization_field': 'organization_history',
            'next_url': self.request.GET.get('next') or self.request.POST.get('next') or '',
            'country_code_options': get_country_code_choices(),
        })
        return ctx

    def form_valid(self, form):
        # Save user fields first
        if self.object and self.object.user:
            self.object.user.email = form.cleaned_data.get('email', '')
            self.object.user.first_name = form.cleaned_data.get('first_name', '')
            self.object.user.last_name = form.cleaned_data.get('last_name', '')
            self.object.user.save()

        action = self.request.POST.get('action', 'save')
        # Capture previous values before save for change detection
        # Get form fields dynamically since StudentForm uses 'exclude' instead of 'fields'
        form_fields = list(form.fields.keys())
        previous_values = {f: getattr(self.get_object(), f) for f in form_fields if hasattr(self.get_object(), f)}
        # Set draft status based on action prior to saving
        form.instance.is_draft = (action == 'save_draft')
        response = super().form_valid(form)
        _save_student_interests(self.object, self.request.POST)
        if action in ['save', 'save_back', 'save_draft']:
            changed = []
            for f in form_fields:
                if not hasattr(self.object, f):
                    continue
                if previous_values.get(f) != getattr(self.object, f):
                    changed.append(f)
            if changed:
                audit_logger.log_profile_update(
                    request=self.request,
                    updated_fields=changed,
                    success=True,
                    errors=None
                )
                security_logger.log_data_modification(
                    request=self.request,
                    action="UPDATE" if not self.object.is_draft else "UPDATE_DRAFT",
                    model="Student",
                    record_id=str(self.object.pk),
                    success=True
                )
        return response

    def get_success_url(self):
        action = self.request.POST.get('action') or self.request.GET.get('action')
        if action == 'save_back':
            return self.request.POST.get('next') or self.request.GET.get('next') or reverse_lazy('data_management:staff_student_list')
        # For draft remain on edit page
        if action == 'save_draft':
            return reverse_lazy('data_management:staff_student_edit', kwargs={'pk': self.object.pk})
        # Default behavior
        next_param = self.request.GET.get('next') or self.request.POST.get('next')
        if next_param:
            return next_param
        return reverse_lazy('data_management:staff_student_detail', kwargs={'pk': self.object.pk})


class StaffStudentCreateView(LoginRequiredMixin, CreateView):
    model = Student
    form_class = StaffStudentCreateForm
    template_name = 'dashboard/staff/staff_student_create_form.html'
    context_object_name = 'student'

    def dispatch(self, request, *args, **kwargs):
        logger.info("[StaffStudentCreateView] dispatch start user=%s path=%s", request.user.username, request.path)
        if not request.user.is_staff:
            logger.warning("[StaffStudentCreateView] access denied user=%s not in staff group", request.user.username)
            security_logger.log_access_attempt(
                request=request,
                resource="Staff Student Create",
                granted=False,
                reason="User is not a staff member"
            )
            raise Http404()
        security_logger.log_access_attempt(
            request=request,
            resource="Staff Student Create",
            granted=True
        )
        logger.info("[StaffStudentCreateView] access granted user=%s", request.user.username)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'basic_fields': [
                'email', 'first_name', 'last_name', 'whatsapp_number', 'birth_place', 'birth_date', 'gender',
                'marital_status', 'membership_status', 'region_origin',
                'parents_name', 'parents_phone'
            ],
            'academic_fields': [
                'institution', 'institution_custom', 'faculty', 'faculty_custom',
                'major', 'major_custom', 'degree_level', 'semester_level', 'latest_grade', 'level'
            ],
            'identity_extra_fields': [
                'passport_number', 'nik', 'lapdik_number', 'arrival_date', 'school_origin', 'home_name', 'home_location'
            ],
            'health_fields': ['disease_history', 'disease_status'],
            'interest_categories': _get_interest_categories_context(),
            'selected_interest_ids': set(),
            'student_interest_customs': {},
            'organization_field': 'organization_history',
            'next_url': self.request.GET.get('next') or self.request.POST.get('next') or '',
            'country_code_options': get_country_code_choices(),
        })
        return ctx

    def form_valid(self, form):
        action = self.request.POST.get('action', 'save')
        logger.info(
            "[StaffStudentCreateView] form_valid start user=%s action=%s draft=%s incoming_fields=%s",
            self.request.user.username, action, (action == 'save_draft'), list(form.cleaned_data.keys())
        )
        form.instance.is_draft = (action == 'save_draft')
        try:
            with transaction.atomic():
                pending_student = form.instance
                User = get_user_model()

                # Get user data from form cleaned_data
                email = form.cleaned_data.get('email', '')
                first_name = form.cleaned_data.get('first_name', '')
                last_name = form.cleaned_data.get('last_name', '')

                # Generate username from email or first name
                base_username_source = email.split('@')[0] if email else first_name
                base_username = slugify(base_username_source) or 'user'
                username = base_username
                i = 1
                while User.objects.filter(username=username).exists():
                    i += 1
                    username = f"{base_username}{i}"
                logger.info("[StaffStudentCreateView] generated username=%s base=%s", username, base_username)
                password_plain = get_random_string(12)

                # Create user with form data
                user = User(username=username, email=email, first_name=first_name, last_name=last_name)
                user.set_password(password_plain)
                user.save()
                logger.info("[StaffStudentCreateView] user created id=%s email=%s", user.id, user.email)
                existing_student = Student.objects.filter(user=user).first()
                if existing_student:
                    logger.info("[StaffStudentCreateView] reusing signal-created student id=%s", existing_student.id)
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
                    logger.info("[StaffStudentCreateView] student updated id=%s changed_fields=%s", existing_student.id,
                                updated_fields)
                    self.object = existing_student
                else:
                    logger.warning(
                        "[StaffStudentCreateView] no signal-created student found; using fallback creation path")
                    pending_student.user = user
                    response = super().form_valid(form)
                    self.object = form.instance
                    logger.info("[StaffStudentCreateView] fallback student created id=%s", self.object.id)
                self.request.session['new_student_credentials'] = {
                    'username': user.username,
                    'password': password_plain,
                    'student_id': str(self.object.pk)
                }
                logger.info("[StaffStudentCreateView] credentials stored in session for student_id=%s", self.object.pk)
                if self.object.email:
                    try:
                        login_url = self.request.build_absolute_uri('/')
                        message = (
                            f"Halo {self.object.full_name},\n\n"
                            f"Akun Anda telah dibuat di sistem KMM Mesir.\n\n"
                            f"Username: {user.username}\nPassword: {password_plain}\n\n"
                            f"Silakan login di: {login_url}\nSegera ganti password setelah login.\n\n"
                            f"Terima kasih."
                        )
                        send_mail(
                            subject='Akun KMM Mesir Anda',
                            message=message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[self.object.email],
                            fail_silently=True
                        )
                        logger.info("[StaffStudentCreateView] credential email queued to %s", self.object.email)
                    except Exception as mail_exc:
                        logger.error("[StaffStudentCreateView] email send failure student_id=%s error=%s",
                                     self.object.pk, mail_exc, exc_info=True)
                security_logger.log_data_modification(
                    request=self.request,
                    action="CREATE",
                    model="User",
                    record_id=str(user.pk),
                    success=True
                )
                audit_logger.log_profile_update(
                    request=self.request,
                    updated_fields=list(form.cleaned_data.keys()),
                    success=True
                )
                security_logger.log_data_modification(
                    request=self.request,
                    action="CREATE_DRAFT" if self.object.is_draft else "CREATE",
                    model="Student",
                    record_id=str(self.object.id),
                    success=True
                )
                _save_student_interests(self.object, self.request.POST)
            if existing_student:
                target_url = self.get_success_url()
                logger.info("[StaffStudentCreateView] redirecting (reuse path) student_id=%s to %s", self.object.pk,
                            target_url)
                return redirect(target_url)
            logger.info("[StaffStudentCreateView] redirecting (fallback path) student_id=%s", self.object.pk)
            return response
        except Exception as e:
            logger.error("[StaffStudentCreateView] form_valid exception user=%s error=%s", self.request.user.username,
                         e, exc_info=True)
            audit_logger.log_profile_update(
                request=self.request,
                updated_fields=list(getattr(form, 'cleaned_data', {}).keys()),
                success=False,
                errors={'general': str(e)}
            )
            raise

    def get_success_url(self):
        action = self.request.POST.get('action') or self.request.GET.get('action')
        if action == 'save_back':
            url = self.request.POST.get('next') or self.request.GET.get('next') or reverse_lazy('data_management:staff_student_list')
            logger.info("[StaffStudentCreateView] get_success_url action=save_back url=%s", url)
            return url
        if action == 'save_draft':
            url = reverse_lazy('data_management:staff_student_edit', kwargs={'pk': self.object.pk})
            logger.info("[StaffStudentCreateView] get_success_url action=save_draft url=%s", url)
            return url
        next_param = self.request.GET.get('next') or self.request.POST.get('next')
        if next_param:
            logger.info("[StaffStudentCreateView] get_success_url next_param=%s", next_param)
            return next_param
        url = reverse_lazy('data_management:staff_student_detail', kwargs={'pk': self.object.pk})
        logger.info("[StaffStudentCreateView] get_success_url default detail url=%s", url)
        return url


def export_students_csv(request):
    if not request.user.is_authenticated or not request.user.groups.filter(name="data_management_staff").exists():
        raise Http404()
    # replicate filtering logic
    qs = Student.objects.all()
    q = request.GET.get('q', '').strip()
    gender = request.GET.get('gender', '').strip()
    degree_level = request.GET.get('degree_level', '').strip()
    level = request.GET.get('level', '').strip()
    marital_status = request.GET.get('marital_status', '').strip()

    from django.db.models import Q
    if q:
        qs = qs.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q) |
            Q(passport_number__icontains=q) |
            Q(nik__icontains=q) |
            Q(faculty__icontains=q) |
            Q(major__icontains=q)
        )
    if gender:
        qs = qs.filter(gender=gender)
    if degree_level:
        qs = qs.filter(degree_level=degree_level)
    if level:
        qs = qs.filter(level=level)
    if marital_status:
        qs = qs.filter(marital_status=marital_status)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students.csv"'
    writer = csv.writer(response)
    writer.writerow(['Full Name', 'Email', 'Passport', 'NIK', 'Degree', 'Tingkat', 'Faculty', 'Major', 'Level', 'Membership'])
    for s in qs.iterator():
        writer.writerow([
            s.full_name,
            s.email,
            s.passport_number or '',
            s.nik or '',
            s.degree_level,
            s.get_semester_level_display() if s.semester_level else '',
            s.faculty_display,
            s.major_display,
            s.get_level_display(),
            s.get_membership_status_display() if s.membership_status else '',
        ])
    return response


# Password reset for a student (staff action)
@login_required
def staff_student_reset_password(request, pk):
    if request.method != 'POST':
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
    request.session['reset_student_credentials'] = {
        'username': user.username,
        'password': new_password,
        'student_id': str(student.pk)
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
                subject='Reset Password Akun KMM Mesir',
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student.email],
                fail_silently=True
            )
        except Exception:
            pass
    security_logger.log_data_modification(
        request=request,
        action="UPDATE",
        model="User",
        record_id=str(user.pk),
        success=True
    )
    return redirect('data_management:staff_student_detail', pk=student.pk)


class StaffStudentDeleteView(LoginRequiredMixin, DeleteView):
    model = Student
    template_name = 'dashboard/staff/staff_student_confirm_delete.html'
    context_object_name = 'student'
    success_url = reverse_lazy('data_management:staff_student_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            security_logger.log_access_attempt(
                request=request,
                resource="Staff Student Delete",
                granted=False,
                reason="User is not a staff member"
            )
            raise Http404()
        security_logger.log_access_attempt(
            request=request,
            resource="Staff Student Delete",
            granted=True
        )
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        student_id = str(self.object.pk)
        student_name = self.object.full_name
        response = super().delete(request, *args, **kwargs)
        security_logger.log_data_modification(
            request=request,
            action="DELETE",
            model="Student",
            record_id=student_id,
            success=True
        )
        messages.success(request, f"Data mahasiswa '{student_name}' berhasil dihapus.")
        return response


def user_logout(request):
    """Unified logout for student or staff, with security logging and proper redirect.
    Only accepts POST for safety.
    Adds success flash message after logout.
    """
    if request.method != 'POST':
        return redirect('data_management:dashboard') if request.user.is_authenticated else redirect(
            'data_management:login')
    was_staff = False
    if request.user.is_authenticated:
        was_staff = request.user.is_staff or request.user.groups.filter(name="data_management_staff").exists()
        security_logger.log_logout(request)
    logout(request)
    # Add success message on new (clean) session after logout
    messages.success(request, 'Berhasil logout.')
    return redirect('data_management:staff_login' if was_staff else 'data_management:login')


def password_reset_request(request):
    """Custom password reset view with HTMX support."""
    user_info = get_user_info(request)

    if request.method == 'POST':
        try:
            form = PasswordResetForm(request.POST)

            if form.is_valid():
                # Get email from form
                email = form.cleaned_data['email']

                # Send password reset email
                form.save(
                    request=request,
                    use_https=request.is_secure(),
                    email_template_name='registration/password_reset_email.html',
                    subject_template_name='registration/password_reset_subject.txt',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                )

                # Log the password reset request
                logger.info(f"Password reset requested - Email: {email}, IP: {user_info['ip']}")
                security_logger.log_access_attempt(
                    request=request,
                    resource="Password Reset",
                    granted=True,
                    reason=f"Email: {email}"
                )

                # For HTMX requests, return the form partial with success message
                if request.htmx:
                    return render(request, 'registration/partials/password_reset_form_partial.html', {
                        'form': PasswordResetForm(),  # Return clean form
                        'success_message': 'Link reset password telah dikirim ke email Anda. Silakan cek inbox atau spam folder.'
                    })

                # For regular requests, redirect to done page
                return redirect('data_management:password_reset_done')
            else:
                logger.warning(
                    f"Password reset failed - Invalid form data, IP: {user_info['ip']}, Errors: {form.errors}")

            # For HTMX requests with errors, return only the form partial
            if request.htmx:
                return render(request, 'registration/partials/password_reset_form_partial.html', {'form': form})

        except Exception as e:
            logger.error(f"Password reset error - IP: {user_info['ip']}, Error: {str(e)}", exc_info=True)
            # Return error response for HTMX or re-render form page
            if request.htmx:
                error_form = PasswordResetForm()
                # Add non-field error to the form errors dict directly
                error_form._errors = {'__all__': ['Terjadi kesalahan. Silakan coba lagi.']}
                return render(request, 'registration/partials/password_reset_form_partial.html', {'form': error_form})
            # For non-HTMX, re-render the page with an empty form and show the error via messages
            messages.error(request, 'Terjadi kesalahan. Silakan coba lagi.')
            form = PasswordResetForm()
            return render(request, 'registration/password_reset_form.html', {'form': form})
    else:
        logger.info(f"Password reset page accessed from IP: {user_info['ip']}")
        form = PasswordResetForm()

    return render(request, 'registration/password_reset_form.html', {'form': form})


def password_reset_confirm(request, uidb64=None, token=None):
    """Custom password reset confirm view with HTMX support."""
    from django.contrib.auth import get_user_model
    from django.contrib.auth.forms import SetPasswordForm
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str

    user_info = get_user_info(request)
    User = get_user_model()

    # Decode the user ID
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Check if token is valid
    validlink = user is not None and default_token_generator.check_token(user, token)

    if request.method == 'POST' and validlink:
        try:
            form = SetPasswordForm(user, request.POST)

            if form.is_valid():
                # Save the new password
                form.save()

                # Log successful password reset
                logger.info(f"Password reset completed - User: {user.username}, IP: {user_info['ip']}")
                security_logger.log_data_modification(
                    request=request,
                    action="UPDATE",
                    model="User",
                    record_id=str(user.pk),
                    success=True
                )

                # For HTMX requests, return success partial
                if request.htmx:
                    return render(request, 'registration/partials/password_reset_confirm_success.html', {
                        'success': True
                    })

                # For regular requests, redirect to complete page
                return redirect('data_management:password_reset_complete')
            else:
                logger.warning(
                    f"Password reset confirm failed - Invalid form data, User: {user.username}, IP: {user_info['ip']}, Errors: {form.errors}")

                # For HTMX requests with errors, return only the form partial
                if request.htmx:
                    return render(request, 'registration/partials/password_reset_confirm_form.html', {
                        'form': form,
                        'validlink': True
                    })

        except Exception as e:
            logger.error(f"Password reset confirm error - IP: {user_info['ip']}, Error: {str(e)}", exc_info=True)
            if request.htmx:
                error_form = SetPasswordForm(user)
                return render(request, 'registration/partials/password_reset_confirm_form.html', {
                    'form': error_form,
                    'validlink': True,
                    'error_message': 'Terjadi kesalahan. Silakan coba lagi.'
                })
    else:
        if validlink:
            logger.info(f"Password reset confirm page accessed - User: {user.username}, IP: {user_info['ip']}")
            form = SetPasswordForm(user)
        else:
            form = None
            logger.warning(f"Invalid password reset link accessed - IP: {user_info['ip']}")

    return render(request, 'registration/password_reset_confirm.html', {
        'form': form,
        'validlink': validlink
    })
