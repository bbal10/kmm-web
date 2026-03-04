from django import forms
from django.contrib.auth import get_user_model

from .models import Interest, InterestCategory, Student, StudentInterest

User = get_user_model()


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
                'class': 'mt-1 w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary'}),
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
        print(cleaned_data)
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
                'class': 'mt-1 w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:border-blue-500 text-sm'}),
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
