"""Authentication and account views: registration, login/logout, email
verification, and password reset."""

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.forms import PasswordResetForm
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from ..forms import UserLoginForm, UserRegistrationForm
from ..models import EmailVerification
from ..utils.logging_utils import audit_logger, get_user_info, security_logger
from .helpers import create_email_verification, send_verification_email

logger = logging.getLogger("data_management.views")
User = get_user_model()


def register(request):
    """User registration view."""
    user_info = get_user_info(request)

    if request.method == "POST":
        try:
            form = UserRegistrationForm(request.POST)

            if form.is_valid():
                user = form.save(commit=False)
                # Deactivate until email is verified
                user.is_active = False
                user.save()
                username = user.username

                # Log successful registration
                audit_logger.log_user_registration(request=request, username=username, success=True)

                security_logger.log_data_modification(
                    request=request,
                    action="CREATE",
                    model="User",
                    record_id=str(user.id),
                    success=True,
                )

                # Create verification record and send email
                verification = create_email_verification(user)
                email_sent = send_verification_email(user, verification.code)
                if email_sent:
                    verification.last_resend_at = timezone.now()
                    verification.save(update_fields=["last_resend_at"])

                # Store pending user in session for the verify-email view
                request.session["pending_verification_user_id"] = user.id

                if email_sent:
                    messages.info(
                        request,
                        f"Pendaftaran berhasil! Kode verifikasi telah dikirim ke {user.email}. "
                        f"Silakan cek email Anda.",
                    )
                else:
                    messages.warning(
                        request,
                        f"Pendaftaran berhasil, namun gagal mengirim email ke {user.email}. "
                        f'Gunakan tombol "Kirim Ulang" untuk mencoba lagi.',
                    )

                return redirect("data_management:verify_email")
            else:
                # Log failed registration
                audit_logger.log_user_registration(
                    request=request,
                    username=form.data.get("username", "Unknown"),
                    success=False,
                    errors=dict(form.errors),
                )

        except Exception as e:
            logger.error(
                f"Registration error - IP: {user_info['ip']}, Error: {str(e)}", exc_info=True
            )
            # Re-initialize form on error
            form = UserRegistrationForm()
    else:
        logger.info(f"Registration page accessed from IP: {user_info['ip']}")
        form = UserRegistrationForm()

    return render(request, "register.html", {"form": form})


def user_login(request):
    """User login view with HTMX support."""
    user_info = get_user_info(request)

    if request.method == "POST":
        try:
            form = UserLoginForm(request.POST)

            if form.is_valid():
                username = form.cleaned_data["username"]
                password = form.cleaned_data["password"]

                user = authenticate(request, username=username, password=password)
                if user is not None:
                    login(request, user)

                    # Log successful login
                    security_logger.log_login_attempt(
                        request=request, username=username, success=True, is_staff=False
                    )

                    # Add success message for login
                    messages.success(
                        request,
                        f"Selamat datang kembali, {user.get_full_name() or user.username}! Login berhasil.",
                    )

                    # For HTMX requests, return redirect header
                    if request.htmx:
                        response = HttpResponse()
                        response["HX-Redirect"] = reverse_lazy("data_management:dashboard")
                        return response

                    return redirect("data_management:dashboard")
                else:
                    # Check if the user exists but is inactive (email not yet verified)
                    try:
                        inactive_user = User.objects.get(username=username, is_active=False)
                        if inactive_user.check_password(password) and hasattr(
                            inactive_user, "email_verification"
                        ):
                            # Re-use (or refresh) the pending verification session
                            request.session["pending_verification_user_id"] = inactive_user.id
                            security_logger.log_login_attempt(
                                request=request,
                                username=username,
                                success=False,
                                is_staff=False,
                                additional_info="Email not verified",
                            )
                            messages.warning(
                                request,
                                "Akun Anda belum diverifikasi. Silakan cek email Anda untuk kode verifikasi.",
                            )
                            if request.htmx:
                                response = HttpResponse()
                                response["HX-Redirect"] = reverse_lazy(
                                    "data_management:verify_email"
                                )
                                return response
                            return redirect("data_management:verify_email")
                    except User.DoesNotExist:
                        pass

                    # Log failed login
                    security_logger.log_login_attempt(
                        request=request,
                        username=username,
                        success=False,
                        is_staff=False,
                        additional_info="Invalid credentials",
                    )

                    form.add_error(None, "Nama pengguna atau kata sandi salah")
            else:
                logger.warning(
                    f"Login failed - Invalid form data, IP: {user_info['ip']}, Errors: {form.errors}"
                )

            # For HTMX requests, return only the form partial
            if request.htmx:
                return render(request, "partials/login_form.html", {"form": form})

        except Exception as e:
            logger.error(f"Login error - IP: {user_info['ip']}, Error: {str(e)}", exc_info=True)
            form = UserLoginForm()
            if request.htmx:
                return render(request, "partials/login_form.html", {"form": form})
    else:
        logger.info(f"Login page accessed from IP: {user_info['ip']}")
        form = UserLoginForm()

    return render(request, "login.html", {"form": form})


def staff_login(request):
    """Staff login view with HTMX support."""
    user_info = get_user_info(request)

    if request.method == "POST":
        try:
            form = UserLoginForm(request.POST)

            if form.is_valid():
                username = form.cleaned_data["username"]
                password = form.cleaned_data["password"]

                user = authenticate(request, username=username, password=password)
                if user is not None and user.is_staff:
                    login(request, user)

                    # Log successful staff login
                    security_logger.log_login_attempt(
                        request=request, username=username, success=True, is_staff=True
                    )

                    # Add success message for staff login
                    messages.success(
                        request,
                        f"Selamat datang, {user.get_full_name() or user.username}! Login staff berhasil.",
                    )

                    # For HTMX requests, return redirect header
                    if request.htmx:
                        response = HttpResponse()
                        response["HX-Redirect"] = reverse_lazy("data_management:dashboard")
                        return response

                    return redirect("data_management:dashboard")
                else:
                    if user is not None:
                        # Non-staff user attempted staff login
                        security_logger.log_login_attempt(
                            request=request,
                            username=username,
                            success=False,
                            is_staff=True,
                            additional_info="User is not staff member",
                        )
                    else:
                        # Invalid credentials
                        security_logger.log_login_attempt(
                            request=request,
                            username=username,
                            success=False,
                            is_staff=True,
                            additional_info="Invalid credentials",
                        )

                    form.add_error(
                        None, "Nama pengguna atau kata sandi salah atau bukan anggota staff"
                    )
            else:
                logger.warning(
                    f"Staff login failed - Invalid form data, IP: {user_info['ip']}, Errors: {form.errors}"
                )

            # For HTMX requests, return only the form partial
            if request.htmx:
                return render(request, "partials/staff_login_form.html", {"form": form})

        except Exception as e:
            logger.error(
                f"Staff login error - IP: {user_info['ip']}, Error: {str(e)}", exc_info=True
            )
            form = UserLoginForm()
            if request.htmx:
                return render(request, "partials/staff_login_form.html", {"form": form})
    else:
        logger.info(f"Staff login page accessed from IP: {user_info['ip']}")
        form = UserLoginForm()

    return render(request, "staff_login.html", {"form": form})


def user_logout(request):
    """Unified logout for student or staff, with security logging and proper redirect.
    Only accepts POST for safety.
    Adds success flash message after logout.
    """
    if request.method != "POST":
        return (
            redirect("data_management:dashboard")
            if request.user.is_authenticated
            else redirect("data_management:login")
        )
    was_staff = False
    if request.user.is_authenticated:
        was_staff = (
            request.user.is_staff
            or request.user.groups.filter(name="data_management_staff").exists()
        )
        security_logger.log_logout(request)
    logout(request)
    # Add success message on new (clean) session after logout
    messages.success(request, "Berhasil logout.")
    return redirect("data_management:staff_login" if was_staff else "data_management:login")


def verify_email(request):
    """Display the email verification page and handle code submission."""
    user_id = request.session.get("pending_verification_user_id")
    if not user_id:
        return redirect("data_management:login")

    user = User.objects.filter(id=user_id, is_active=False).first()
    if user is None:
        request.session.pop("pending_verification_user_id", None)
        messages.info(
            request, "Verifikasi email tidak lagi diperlukan. Silakan login dengan akun Anda."
        )
        return redirect("data_management:login")

    try:
        verification = user.email_verification
    except EmailVerification.DoesNotExist:
        messages.error(request, "Data verifikasi tidak ditemukan. Silakan daftar ulang.")
        return redirect("data_management:register")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()

        if verification.is_expired():
            messages.error(request, "Kode verifikasi telah kedaluwarsa. Silakan kirim ulang kode.")
        elif verification.attempt_count >= EmailVerification.MAX_ATTEMPTS:
            messages.error(
                request, "Terlalu banyak percobaan kode yang salah. Silakan kirim ulang kode baru."
            )
        elif code == verification.code:
            # Activate user
            user.is_active = True
            user.save(update_fields=["is_active"])
            verification.delete()
            del request.session["pending_verification_user_id"]

            audit_logger.log_user_registration(
                request=request,
                username=user.username,
                success=True,
            )
            logger.info("Email verified for user=%s", user.username)
            messages.success(
                request, "Email berhasil diverifikasi! Silakan login dengan akun Anda."
            )
            return redirect("data_management:login")
        else:
            verification.attempt_count += 1
            verification.save(update_fields=["attempt_count"])
            remaining = EmailVerification.MAX_ATTEMPTS - verification.attempt_count
            messages.error(
                request,
                (
                    f"Kode verifikasi salah. Sisa percobaan: {remaining}."
                    if remaining > 0
                    else "Kode verifikasi salah. Tidak ada sisa percobaan. Silakan kirim ulang kode."
                ),
            )

    context = {
        "email": user.email,
        "can_resend": verification.can_resend(),
        "seconds_until_resend": verification.seconds_until_resend(),
    }
    return render(request, "verify_email.html", context)


def resend_verification_code(request):
    """Resend a new verification code to the user's email."""
    if request.method != "POST":
        return redirect("data_management:verify_email")

    user_id = request.session.get("pending_verification_user_id")
    if not user_id:
        return redirect("data_management:login")

    user = User.objects.filter(id=user_id, is_active=False).first()
    if user is None:
        request.session.pop("pending_verification_user_id", None)
        messages.info(
            request, "Verifikasi email tidak lagi diperlukan. Silakan login dengan akun Anda."
        )
        return redirect("data_management:login")

    try:
        verification = user.email_verification
    except EmailVerification.DoesNotExist:
        messages.error(request, "Data verifikasi tidak ditemukan. Silakan daftar ulang.")
        return redirect("data_management:register")

    if not verification.can_resend():
        seconds = verification.seconds_until_resend()
        messages.warning(request, f"Mohon tunggu {seconds} detik sebelum mengirim ulang kode.")
        return redirect("data_management:verify_email")

    verification = create_email_verification(user)
    email_sent = send_verification_email(user, verification.code)
    if email_sent:
        verification.last_resend_at = timezone.now()
        verification.save(update_fields=["last_resend_at"])
        logger.info("Resent verification code for user=%s", user.username)
        messages.success(request, f"Kode verifikasi baru telah dikirim ke {user.email}.")
    else:
        messages.error(request, f"Gagal mengirim email ke {user.email}. Silakan coba lagi.")
    return redirect("data_management:verify_email")


def password_reset_request(request):
    """Custom password reset view with HTMX support."""
    user_info = get_user_info(request)

    if request.method == "POST":
        try:
            form = PasswordResetForm(request.POST)

            if form.is_valid():
                # Get email from form
                email = form.cleaned_data["email"]

                # Send password reset email
                form.save(
                    request=request,
                    use_https=request.is_secure(),
                    email_template_name="registration/password_reset_email.html",
                    subject_template_name="registration/password_reset_subject.txt",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                )

                # Log the password reset request
                logger.info(f"Password reset requested - Email: {email}, IP: {user_info['ip']}")
                security_logger.log_access_attempt(
                    request=request,
                    resource="Password Reset",
                    granted=True,
                    reason=f"Email: {email}",
                )

                # For HTMX requests, return the form partial with success message
                if request.htmx:
                    return render(
                        request,
                        "registration/partials/password_reset_form_partial.html",
                        {
                            "form": PasswordResetForm(),  # Return clean form
                            "success_message": "Link reset password telah dikirim ke email Anda. Silakan cek inbox atau spam folder.",
                        },
                    )

                # For regular requests, redirect to done page
                return redirect("data_management:password_reset_done")
            else:
                logger.warning(
                    f"Password reset failed - Invalid form data, IP: {user_info['ip']}, Errors: {form.errors}"
                )

            # For HTMX requests with errors, return only the form partial
            if request.htmx:
                return render(
                    request,
                    "registration/partials/password_reset_form_partial.html",
                    {"form": form},
                )

        except Exception as e:
            logger.error(
                f"Password reset error - IP: {user_info['ip']}, Error: {str(e)}", exc_info=True
            )
            # Return error response for HTMX or re-render form page
            if request.htmx:
                error_form = PasswordResetForm()
                # Add non-field error to the form errors dict directly
                error_form._errors = {"__all__": ["Terjadi kesalahan. Silakan coba lagi."]}
                return render(
                    request,
                    "registration/partials/password_reset_form_partial.html",
                    {"form": error_form},
                )
            # For non-HTMX, re-render the page with an empty form and show the error via messages
            messages.error(request, "Terjadi kesalahan. Silakan coba lagi.")
            form = PasswordResetForm()
            return render(request, "registration/password_reset_form.html", {"form": form})
    else:
        logger.info(f"Password reset page accessed from IP: {user_info['ip']}")
        form = PasswordResetForm()

    return render(request, "registration/password_reset_form.html", {"form": form})


def password_reset_confirm(request, uidb64=None, token=None):
    """Custom password reset confirm view with HTMX support."""
    from django.contrib.auth.forms import SetPasswordForm
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_str
    from django.utils.http import urlsafe_base64_decode

    user_info = get_user_info(request)

    # Decode the user ID
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Check if token is valid
    validlink = user is not None and default_token_generator.check_token(user, token)

    if request.method == "POST" and validlink:
        try:
            form = SetPasswordForm(user, request.POST)

            if form.is_valid():
                # Save the new password
                form.save()

                # Log successful password reset
                logger.info(
                    f"Password reset completed - User: {user.username}, IP: {user_info['ip']}"
                )
                security_logger.log_data_modification(
                    request=request,
                    action="UPDATE",
                    model="User",
                    record_id=str(user.pk),
                    success=True,
                )

                # For HTMX requests, return success partial
                if request.htmx:
                    return render(
                        request,
                        "registration/partials/password_reset_confirm_success.html",
                        {"success": True},
                    )

                # For regular requests, redirect to complete page
                return redirect("data_management:password_reset_complete")
            else:
                logger.warning(
                    f"Password reset confirm failed - Invalid form data, User: {user.username}, IP: {user_info['ip']}, Errors: {form.errors}"
                )

                # For HTMX requests with errors, return only the form partial
                if request.htmx:
                    return render(
                        request,
                        "registration/partials/password_reset_confirm_form.html",
                        {"form": form, "validlink": True},
                    )

        except Exception as e:
            logger.error(
                f"Password reset confirm error - IP: {user_info['ip']}, Error: {str(e)}",
                exc_info=True,
            )
            if request.htmx:
                error_form = SetPasswordForm(user)
                return render(
                    request,
                    "registration/partials/password_reset_confirm_form.html",
                    {
                        "form": error_form,
                        "validlink": True,
                        "error_message": "Terjadi kesalahan. Silakan coba lagi.",
                    },
                )
    else:
        if validlink:
            logger.info(
                f"Password reset confirm page accessed - User: {user.username}, IP: {user_info['ip']}"
            )
            form = SetPasswordForm(user)
        else:
            form = None
            logger.warning(f"Invalid password reset link accessed - IP: {user_info['ip']}")

    return render(
        request, "registration/password_reset_confirm.html", {"form": form, "validlink": validlink}
    )
