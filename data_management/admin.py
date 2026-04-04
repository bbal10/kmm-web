from django.contrib import admin

from .models import District, Interest, InterestCategory, ScholarshipSource, SchoolOrigin, Student, StudentInterest


class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'level', 'institution', 'faculty', 'major')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'passport_number', 'nik')
    list_filter = ('level', 'institution', 'faculty', 'gender', 'membership_status', 'home_location')
    fieldsets = (
        ('Personal Info', {
            'fields': ('user', 'whatsapp_number', 'gender', 'birth_place', 'birth_date', 'marital_status',
                       'membership_status', 'region_origin')
        }),
        ('Academic Info', {
            'fields': ('level', 'institution', 'institution_custom', 'faculty', 'faculty_custom',
                       'major', 'major_custom', 'degree_level', 'semester_level', 'latest_grade',
                       'school_origin')
        }),
        ('Identity Info', {
            'fields': ('passport_number', 'nik', 'lapdik_number', 'arrival_date')
        }),
        ('Contact & Residence', {
            'fields': ('parents_name', 'parents_phone', 'home_name', 'home_location')
        }),
        ('Guardian Information', {
            'fields': ('photo_url', 'guardian_name', 'guardian_phone')
        }),
        ('Health Information', {
            'fields': ('disease_history', 'disease_status')
        }),
        ('Interests and Talents', {
            'fields': ('sport_interest', 'sport_achievement', 'art_interest', 'art_achievement', 'literacy_interest',
                       'literacy_achievement', 'science_interest', 'science_achievement', 'mtq_interest',
                       'mtq_achievement', 'media_interest', 'media_achievement')
        }),
        ('Organizational History', {
            'fields': ('organization_history',)
        }),
        ('Financial Information', {
            'fields': ('education_funding', 'scholarship_source',
                       'living_cost', 'monthly_income')
        }),
    )
    readonly_fields = ('id',)


class InterestInline(admin.TabularInline):
    model = Interest
    extra = 1
    fields = ('name', 'allow_custom', 'order')


@admin.register(InterestCategory)
class InterestCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    inlines = [InterestInline]


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'allow_custom', 'order')
    list_filter = ('category',)


class StudentInterestInline(admin.TabularInline):
    model = StudentInterest
    extra = 1
    fields = ('interest', 'custom_value')
    autocomplete_fields = ['interest']


# Register your models here.
admin.site.register(Student, StudentAdmin)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    search_fields = ('name',)
    ordering = ('order', 'name')


@admin.register(SchoolOrigin)
class SchoolOriginAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    search_fields = ('name',)
    ordering = ('order', 'name')


@admin.register(ScholarshipSource)
class ScholarshipSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    search_fields = ('name',)
    ordering = ('order', 'name')
