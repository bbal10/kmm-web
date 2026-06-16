from unittest.mock import patch
from datetime import timedelta
from typing import cast

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, UserManager
from django.utils import timezone

from .models import EmailVerification, Student
from .forms import StaffStudentCreateForm
from .views import StudentDataUpdateView

User = get_user_model()


class TestStaffStudentCreation(TestCase):
    def setUp(self):
        user_manager = cast(UserManager, User.objects)
        # Ensure staff group exists
        self.staff_group, _ = Group.objects.get_or_create(name="data_management_staff")
        self.staff_user = user_manager.create_user(username='staff', email='staff@example.com', password='pass12345', is_staff=True)
        self.staff_user.groups.add(self.staff_group)
        self.client.login(username='staff', password='pass12345')

    def _base_post_data(self, **overrides):
        data = {
            'email': 'jane@example.com',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'whatsapp_number': '',
            'birth_place': '',
            'birth_date': '',
            'gender': 'F',
            'marital_status': 'single',
            'membership_status': '',
            'region_origin': '',
            'parents_name': '',
            'parents_phone': '',
            'institution': '',
            'faculty': '',
            'major': '',
            'degree_level': 'S2',
            'semester_level': '4',
            'latest_grade': '',
            'passport_number': '',
            'lapdik_number': '',
            'arrival_date': '',
            'school_origin': '',
            'home_name': '',
            'home_location': '',
            'level': 'maba',
            'disease_history': '',
            'disease_status': '',
            'sport_interest': '',
            'sport_achievement': '',
            'art_interest': '',
            'art_achievement': '',
            'literacy_interest': '',
            'literacy_achievement': '',
            'science_interest': '',
            'science_achievement': '',
            'mtq_interest': '',
            'mtq_achievement': '',
            'media_interest': '',
            'media_achievement': '',
            'organization_history': '',
            'is_draft': '',
            'action': 'save',
        }
        data.update(overrides)
        return data

    @patch('data_management.forms.get_region_origin_choices', return_value=[('Kabupaten A', 'Kabupaten A')])
    def test_create_student_reuses_signal_student(self, _mock_region_choices):
        url = reverse('data_management:staff_student_create')
        post_data = self._base_post_data(region_origin='Kabupaten A')
        pre_user_count = get_user_model().objects.count()
        response = self.client.post(url, data=post_data, follow=False)
        # Expect redirect (302)
        self.assertIn(response.status_code, (302, 303))
        # New user created
        self.assertEqual(get_user_model().objects.count(), pre_user_count + 1)
        # Only one student with the given user email
        students = Student.objects.filter(user__email='jane@example.com')
        self.assertEqual(students.count(), 1, "Exactly one Student should exist for the created user")
        student = students.first()
        # Ensure updated values (not the defaults from the signal)
        self.assertEqual(student.degree_level, 'S2')
        self.assertEqual(student.semester_level, '4')
        self.assertEqual(student.gender, 'F')
        self.assertEqual(student.region_origin, 'Kabupaten A')

    @patch('data_management.forms.get_region_origin_choices', return_value=[('Kabupaten A', 'Kabupaten A')])
    def test_staff_student_create_form_rejects_invalid_region_origin(self, _mock_region_choices):
        form = StaffStudentCreateForm(data=self._base_post_data(region_origin='Kabupaten B'))

        self.assertFalse(form.is_valid())
        self.assertIn('region_origin', form.errors)


class TestStudentProfileUpdateRedirect(TestCase):
    def test_success_url_uses_namespaced_profile_route(self):
        self.assertEqual(str(StudentDataUpdateView.success_url), reverse('data_management:profile'))


@override_settings(VITE_DEV_MODE=True)
class TestEmailVerificationRegistration(TestCase):
    """Tests for the email verification flow after registration."""

    REGISTER_URL = '/register/'
    VERIFY_URL = '/verify-email/'
    RESEND_URL = '/verify-email/resend/'
    LOGIN_URL = '/'

    def _register(self, username='testuser', email='test@example.com',
                  password='SecurePass123!'):
        return self.client.post(self.REGISTER_URL, {
            'username': username,
            'email': email,
            'first_name': 'Test',
            'last_name': 'User',
            'password1': password,
            'password2': password,
        })

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def test_registration_creates_inactive_user(self):
        """After registration the user account must be inactive."""
        self._register()
        user = User.objects.get(username='testuser')
        self.assertFalse(user.is_active)

    def test_registration_creates_email_verification_record(self):
        """After registration an EmailVerification record must exist."""
        self._register()
        user = User.objects.get(username='testuser')
        self.assertTrue(EmailVerification.objects.filter(user=user).exists())

    def test_registration_redirects_to_verify_page(self):
        """After registration the client must be redirected to the verify-email page."""
        response = self._register()
        self.assertRedirects(response, self.VERIFY_URL)

    def test_registration_stores_user_id_in_session(self):
        """Pending verification user id is stored in session after registration."""
        self._register()
        user = User.objects.get(username='testuser')
        self.assertEqual(
            self.client.session.get('pending_verification_user_id'),
            user.id,
        )

    # ------------------------------------------------------------------
    # Verification – success
    # ------------------------------------------------------------------

    def test_correct_code_activates_user(self):
        """Submitting the correct code activates the user and redirects to login."""
        self._register()
        user = User.objects.get(username='testuser')
        verification = EmailVerification.objects.get(user=user)

        response = self.client.post(self.VERIFY_URL, {'code': verification.code})

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertRedirects(response, self.LOGIN_URL)

    def test_correct_code_removes_verification_record(self):
        """EmailVerification record must be deleted after successful verification."""
        self._register()
        user = User.objects.get(username='testuser')
        verification = EmailVerification.objects.get(user=user)
        self.client.post(self.VERIFY_URL, {'code': verification.code})
        self.assertFalse(EmailVerification.objects.filter(user=user).exists())

    def test_correct_code_clears_session(self):
        """Session key must be cleared after successful verification."""
        self._register()
        user = User.objects.get(username='testuser')
        verification = EmailVerification.objects.get(user=user)
        self.client.post(self.VERIFY_URL, {'code': verification.code})
        self.assertNotIn('pending_verification_user_id', self.client.session)

    # ------------------------------------------------------------------
    # Verification – wrong code
    # ------------------------------------------------------------------

    def test_wrong_code_increments_attempt_count(self):
        """Wrong code must increment the attempt counter."""
        self._register()
        user = User.objects.get(username='testuser')

        self.client.post(self.VERIFY_URL, {'code': '000000'})

        verification = EmailVerification.objects.get(user=user)
        self.assertEqual(verification.attempt_count, 1)

    def test_wrong_code_keeps_user_inactive(self):
        """Wrong code must NOT activate the user."""
        self._register()
        user = User.objects.get(username='testuser')
        self.client.post(self.VERIFY_URL, {'code': '000000'})
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_max_attempts_blocks_further_verification(self):
        """After MAX_ATTEMPTS wrong codes the verify view must show an error."""
        self._register()
        user = User.objects.get(username='testuser')
        verification = EmailVerification.objects.get(user=user)
        verification.attempt_count = EmailVerification.MAX_ATTEMPTS
        verification.save()

        response = self.client.post(self.VERIFY_URL, {'code': '000000'})

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    # ------------------------------------------------------------------
    # Verification – expired code
    # ------------------------------------------------------------------

    def test_expired_code_shows_error_and_keeps_user_inactive(self):
        """An expired code must not activate the user and must show an error."""
        self._register()
        user = User.objects.get(username='testuser')
        verification = EmailVerification.objects.get(user=user)

        # Expire the code by moving expires_at to the past
        verification.expires_at = timezone.now() - timedelta(seconds=1)
        verification.save()

        response = self.client.post(self.VERIFY_URL, {'code': verification.code})

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    # ------------------------------------------------------------------
    # Resend
    # ------------------------------------------------------------------

    def test_resend_generates_new_code(self):
        """Resending must replace the old verification code."""
        self._register()
        user = User.objects.get(username='testuser')
        old_code = EmailVerification.objects.get(user=user).code

        # Allow immediate resend by clearing last_resend_at
        verification = EmailVerification.objects.get(user=user)
        verification.last_resend_at = None
        verification.save()

        response = self.client.post(self.RESEND_URL)

        self.assertRedirects(response, self.VERIFY_URL)
        new_code = EmailVerification.objects.get(user=user).code
        self.assertIsNotNone(new_code)
        self.assertNotEqual(new_code, old_code)

    def test_resend_rate_limited(self):
        """Resend within the cooldown period must show a warning and not change the code."""
        self._register()
        user = User.objects.get(username='testuser')
        verification = EmailVerification.objects.get(user=user)
        # last_resend_at is recent (set during _create_email_verification), so resend should be blocked
        old_code = verification.code

        self.client.post(self.RESEND_URL)

        verification.refresh_from_db()
        # Code should remain the same because rate-limit blocked the resend
        self.assertEqual(verification.code, old_code)

    def test_resend_without_session_redirects_to_login(self):
        """Resend without a pending session must redirect to login."""
        response = self.client.post(self.RESEND_URL)
        self.assertRedirects(response, self.LOGIN_URL)

    # ------------------------------------------------------------------
    # Login blocked before verification
    # ------------------------------------------------------------------

    def test_unverified_user_cannot_login(self):
        """An unverified user must not be logged in successfully."""
        self._register()
        response = self.client.post(self.LOGIN_URL, {
            'username': 'testuser',
            'password': 'SecurePass123!',
        })
        # User should NOT be authenticated
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_unverified_user_login_redirects_to_verify(self):
        """Attempting to login with an unverified account must redirect to verify-email."""
        self._register()
        # Clear the session so we start fresh (simulating a new browser session)
        self.client.session.flush()

        response = self.client.post(self.LOGIN_URL, {
            'username': 'testuser',
            'password': 'SecurePass123!',
        })
        self.assertRedirects(response, self.VERIFY_URL)

