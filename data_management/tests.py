from unittest.mock import patch
from typing import cast

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, UserManager
from .models import Student
from .forms import StaffStudentCreateForm
from .views import StudentDataUpdateView

class TestStaffStudentCreation(TestCase):
    def setUp(self):
        User = get_user_model()
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
            'nik': '',
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


