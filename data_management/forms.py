from django import forms
from django.contrib.auth import get_user_model
import json
import logging
import re
from functools import lru_cache
from urllib.request import urlopen

from .models import Interest, InterestCategory, Student, StudentInterest

User = get_user_model()

logger = logging.getLogger(__name__)

COUNTRY_CODES_JSON_URL = (
    'https://gist.githubusercontent.com/anubhavshrimal/75f6183458db8c453306f93521e93d37/raw/'
    'f77e7598a8503f1f70528ae1cbf9f66755698a16/CountryCodes.json'
)

FALLBACK_COUNTRY_CODE_CHOICES = [
    ('+20', 'Mesir (+20)'),
    ('+62', 'Indonesia (+62)'),
    ('+60', 'Malaysia (+60)'),
    ('+65', 'Singapura (+65)'),
    ('+966', 'Arab Saudi (+966)'),
    ('+971', 'Uni Emirat Arab (+971)'),
    ('+974', 'Qatar (+974)'),
    ('+965', 'Kuwait (+965)'),
    ('+968', 'Oman (+968)'),
    ('+90', 'Turki (+90)'),
    ('+44', 'United Kingdom (+44)'),
    ('+1', 'United States / Canada (+1)'),
    ('+61', 'Australia (+61)'),
    ('+81', 'Jepang (+81)'),
    ('+82', 'Korea Selatan (+82)'),
    ('+49', 'Jerman (+49)'),
    ('+33', 'Prancis (+33)'),
    ('+39', 'Italia (+39)'),
    ('+31', 'Belanda (+31)'),
    ('+34', 'Spanyol (+34)'),
]


def _normalize_country_code(value):
    if value is None:
        return None
    digits = re.sub(r'\D', '', str(value))
    if not digits:
        return None
    return f'+{digits}'


@lru_cache(maxsize=1)
def get_country_code_choices():
    """Get country codes from remote JSON with safe fallback."""
    try:
        with urlopen(COUNTRY_CODES_JSON_URL, timeout=8) as response:
            payload = json.loads(response.read().decode('utf-8'))

        choices = []
        seen = set()
        for item in payload if isinstance(payload, list) else []:
            if not isinstance(item, dict):
                continue
            code = _normalize_country_code(item.get('dial_code') or item.get('dialCode'))
            if not code or code in seen:
                continue

            name = (item.get('name') or '').strip() or f'Country {code}'
            choices.append((code, f'{name} ({code})'))
            seen.add(code)

        if choices:
            return sorted(choices, key=lambda x: (len(x[0]), x[0]))

    except Exception as exc:
        logger.warning('Failed to load country codes from remote JSON: %s', exc)

    return FALLBACK_COUNTRY_CODE_CHOICES


def _get_country_codes_for_validation():
    return sorted([code for code, _ in get_country_code_choices()], key=len, reverse=True)


def _validate_whatsapp_number(form, cleaned_data):
    raw_value = cleaned_data.get('whatsapp_number')
    if not raw_value:
        cleaned_data['whatsapp_number'] = ''
        return cleaned_data

    normalized = re.sub(r'[\u200e\u200f\u202a-\u202e\u2066-\u2069]', '', str(raw_value)).strip()
    if not normalized:
        cleaned_data['whatsapp_number'] = ''
        return cleaned_data

    if not normalized.startswith('+'):
        form.add_error('whatsapp_number', 'Gunakan format internasional, contoh: +628123456789.')
        return cleaned_data

    if not re.fullmatch(r'^\+\d[\d\s\-().]{5,24}$', normalized):
        form.add_error('whatsapp_number', 'Format nomor WhatsApp tidak valid.')
        return cleaned_data

    digits_only = '+' + re.sub(r'\D', '', normalized)
    matched_code = next((code for code in _get_country_codes_for_validation() if digits_only.startswith(code)), None)

    if not matched_code:
        form.add_error('whatsapp_number', 'Kode negara tidak dikenali. Pilih dari daftar kode negara.')
        return cleaned_data

    national_number = digits_only[len(matched_code):]
    if len(national_number) < 5:
        form.add_error('whatsapp_number', 'Nomor setelah kode negara terlalu pendek.')
        return cleaned_data

    cleaned_data['whatsapp_number'] = f'{matched_code}{national_number}'
    return cleaned_data


def _validate_other_choice(form, cleaned_data, choice_field, custom_field):
    choice_value = cleaned_data.get(choice_field)
    custom_value = (cleaned_data.get(custom_field) or '').strip()

    if choice_value == 'other':
        if not custom_value:
            form.add_error(custom_field, 'Wajib diisi ketika memilih "Lainnya".')
        cleaned_data[custom_field] = custom_value
    else:
        # Prevent stale custom text when selection is no longer "other"
        cleaned_data[custom_field] = ''

    return cleaned_data


class UserRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserLoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm',
            'placeholder': 'Username'
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm',
            'placeholder': 'Password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if not User.objects.filter(username=username).exists():
            raise forms.ValidationError("User does not exist")

        user = User.objects.get(username=username)
        if not user.check_password(password):
            raise forms.ValidationError("Incorrect password")

        return cleaned_data


class StaffLoginForm(forms.Form):
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if not User.objects.filter(username=username, is_staff=True).exists():
            raise forms.ValidationError("Staff does not exist")

        user = User.objects.get(username=username)
        if not user.check_password(password):
            raise forms.ValidationError("Incorrect password")

        return cleaned_data


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        exclude = ['user', 'interests']  # interests handled manually via StudentInterest
        widgets = {
            # Text inputs dengan styling konsisten
            'whatsapp_number': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': '+628123456789',
                'list': 'country-code-list'}),
            'birth_place': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'birth_date': forms.DateInput(attrs={'type': 'date',
                                                 'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'gender': forms.Select(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'marital_status': forms.Select(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'citizenship_status': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'region_origin': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'id': 'region-origin-input'}),
            'parents_name': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'parents_phone': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),

            # Academic fields
            'institution': forms.Select(attrs={'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'institution_custom': forms.TextInput(attrs={'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'faculty': forms.Select(attrs={'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'faculty_custom': forms.TextInput(attrs={'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'major': forms.Select(attrs={'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'major_custom': forms.TextInput(attrs={'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'membership_status': forms.Select(attrs={'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'degree_level': forms.Select(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'semester_level': forms.Select(attrs={'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'latest_grade': forms.Select(attrs={'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),

            # Health Information
            'disease_history': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'disease_status': forms.Select(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),

            # Achievements (interest checkboxes handled manually in views/templates)
            'sport_achievement': forms.Textarea(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'rows': 3}),
            'art_achievement': forms.Textarea(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'rows': 3}),
            'literacy_achievement': forms.Textarea(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'rows': 3}),
            'science_achievement': forms.Textarea(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'rows': 3}),
            'mtq_achievement': forms.Textarea(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'rows': 3}),
            'media_achievement': forms.Textarea(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'rows': 3}),

            # Organizational History
            'organization_history': forms.Textarea(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'rows': 4}),

            # Identity fields
            'passport_number': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'nik': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'lapdik_number': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'arrival_date': forms.DateInput(attrs={'type': 'date',
                                                   'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'home_name': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'home_location': forms.Select(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'school_origin': forms.Select(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'scholarship_source': forms.Select(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'level': forms.Select(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),

            # Guardian Information
            'photo_url': forms.URLInput(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary',
                'placeholder': 'https://drive.google.com/...'}),
            'guardian_name': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'guardian_phone': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),

            # Financial fields
            'education_funding': forms.Select(attrs={
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'living_cost': forms.Select(attrs={'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
            'monthly_income': forms.Select(attrs={'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        _validate_other_choice(self, cleaned_data, 'institution', 'institution_custom')
        _validate_other_choice(self, cleaned_data, 'faculty', 'faculty_custom')
        _validate_other_choice(self, cleaned_data, 'major', 'major_custom')
        _validate_whatsapp_number(self, cleaned_data)
        return cleaned_data


class StaffStudentForm(forms.ModelForm):
    # User fields that are not part of Student model
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'})
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'})
    )

    class Meta:
        model = Student
        fields = [
            'whatsapp_number', 'birth_place', 'birth_date', 'gender',
            'marital_status', 'membership_status', 'citizenship_status', 'region_origin',
            'parents_name', 'parents_phone',
            'institution', 'institution_custom', 'faculty', 'faculty_custom',
            'major', 'major_custom', 'degree_level', 'semester_level', 'latest_grade',
            'passport_number', 'nik', 'lapdik_number', 'arrival_date', 'school_origin',
            'home_name', 'home_location', 'level',
            'disease_history', 'disease_status',
            'sport_achievement', 'art_achievement',
            'literacy_achievement', 'science_achievement',
            'mtq_achievement', 'media_achievement',
            'organization_history', 'is_draft',
            'education_funding', 'scholarship_source',
            'living_cost', 'monthly_income',
        ]
        widgets = {
            # Text inputs dengan styling konsisten
            'whatsapp_number': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm',
                'placeholder': '+628123456789',
                'list': 'country-code-list'}),
            'birth_place': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'citizenship_status': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'region_origin': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'parents_name': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'parents_phone': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'institution': forms.Select(attrs={'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'institution_custom': forms.TextInput(attrs={'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'faculty': forms.Select(attrs={'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'faculty_custom': forms.TextInput(attrs={'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'major': forms.Select(attrs={'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'major_custom': forms.TextInput(attrs={'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'membership_status': forms.Select(attrs={'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'latest_grade': forms.Select(attrs={'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'passport_number': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'nik': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'lapdik_number': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'home_name': forms.TextInput(attrs={'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'home_location': forms.Select(attrs={'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'school_origin': forms.Select(attrs={'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'scholarship_source': forms.Select(attrs={'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),

            # Hidden fields
            'is_draft': forms.HiddenInput(),

            # Date fields
            'birth_date': forms.DateInput(attrs={'type': 'date',
                                                 'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'arrival_date': forms.DateInput(attrs={'type': 'date',
                                                   'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),

            # Select fields (was NumberInput)
            'semester_level': forms.Select(attrs={'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),

            # Select fields
            'gender': forms.Select(attrs={
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'marital_status': forms.Select(attrs={
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'degree_level': forms.Select(attrs={
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'level': forms.Select(attrs={
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'disease_status': forms.Select(attrs={
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),

            # Textarea fields
            'sport_achievement': forms.Textarea(attrs={'rows': 2,
                                                       'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'art_achievement': forms.Textarea(attrs={'rows': 2,
                                                     'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'literacy_achievement': forms.Textarea(attrs={'rows': 2,
                                                          'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'science_achievement': forms.Textarea(attrs={'rows': 2,
                                                         'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'mtq_achievement': forms.Textarea(attrs={'rows': 2,
                                                     'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'media_achievement': forms.Textarea(attrs={'rows': 2,
                                                       'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),

            # Organizational History
            'organization_history': forms.Textarea(attrs={'rows': 3,
                                                          'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),

            # Disease History
            'disease_history': forms.TextInput(attrs={
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),

            # Financial fields
            'education_funding': forms.Select(attrs={
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'living_cost': forms.Select(attrs={'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
            'monthly_income': forms.Select(attrs={'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        _validate_other_choice(self, cleaned_data, 'institution', 'institution_custom')
        _validate_other_choice(self, cleaned_data, 'faculty', 'faculty_custom')
        _validate_other_choice(self, cleaned_data, 'major', 'major_custom')
        _validate_whatsapp_number(self, cleaned_data)
        return cleaned_data


class StaffStudentCreateForm(StaffStudentForm):
    # User fields that are not part of Student model
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'})
    )
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'})
    )

    class Meta(StaffStudentForm.Meta):
        pass

    def clean(self):
        cleaned = super().clean()
        # Trim whitespace for some fields
        for f in ['passport_number', 'nik', 'email', 'first_name', 'last_name']:
            if cleaned.get(f):
                cleaned[f] = cleaned[f].strip()
        # Required core fields enforcement (model might allow but we want explicit feedback)
        required_fields = ['email', 'first_name', 'gender', 'marital_status', 'degree_level', 'semester_level']
        for f in required_fields:
            if not cleaned.get(f):
                self.add_error(f, 'Field is required.')
        # Semester range guard (model already has but earlier feedback)
        sem = cleaned.get('semester_level')
        if sem is not None and (sem < 1 or sem > 14):
            self.add_error('semester_level', 'Must be between 1 and 14.')
        from .models import Student
        passport = cleaned.get('passport_number')
        if passport:
            if Student.objects.filter(passport_number=passport).exists():
                self.add_error('passport_number', 'Passport already registered.')
        nik = cleaned.get('nik')
        if nik:
            if Student.objects.filter(nik=nik).exists():
                self.add_error('nik', 'NIK already registered.')
        return cleaned
