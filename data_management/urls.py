from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'data_management'
urlpatterns = [
    path('register/', views.register, name='register'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('verify-email/resend/', views.resend_verification_code, name='resend_verification_code'),
    path("reset-password/", views.password_reset_request, name='password_reset'),
    path("reset-password/done/", auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path("reset-password/confirm/<uidb64>/<token>/", views.password_reset_confirm, name='password_reset_confirm'),
    path("reset-password/complete/", auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('staff/', views.staff_login, name='staff_login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path("dashboard/profile/", views.StudentDataDetailView.as_view(), name='profile'),
    path("dashboard/profile/edit/", views.StudentDataUpdateView.as_view(), name='profile_edit'),
    path('dashboard/staff/students/', views.StaffDashboardDataListView.as_view(), name='staff_student_list'),
    path('dashboard/staff/students/add/', views.StaffStudentCreateView.as_view(), name='staff_student_create'),
    path('dashboard/staff/students/<int:pk>/', views.StaffStudentDetailView.as_view(), name='staff_student_detail'),
    path('dashboard/staff/students/export/csv/', views.export_students_csv, name='export_students_csv'),
    path('dashboard/staff/students/<int:pk>/edit/', views.StaffStudentUpdateView.as_view(), name='staff_student_edit'),
    path('dashboard/staff/students/<int:pk>/reset-password/', views.staff_student_reset_password,
         name='staff_student_reset_password'),
    path('dashboard/staff/students/<int:pk>/delete/', views.StaffStudentDeleteView.as_view(),
         name='staff_student_delete'),
]
