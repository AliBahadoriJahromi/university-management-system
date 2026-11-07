from django.urls import path
from . import views

urlpatterns = [
    # login / logout
    path("", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    # student
    path("courses/select/", views.course_selection, name="course_selection"),
    path("courses/<int:course_id>/enroll/", views.enroll, name="enroll"),
    path("courses/<int:course_id>/drop/", views.drop, name="drop"),
    path("transcript/", views.transcript, name="transcript"),
    # professor
    path("courses/<int:course_id>/grades/", views.enter_grades, name="enter_grades"),
    # manager
    path("manage/courses/add/", views.add_course, name="add_course"),
    path("manage/courses/", views.course_list, name="course_list"),
    path("manage/reports/", views.reports, name="reports"),
    path("manage/reports/export/", views.export_students_csv, name="export_students_csv"),
    path("manage/workflows/", views.workflows, name="workflows"),
    path(
        "manage/workflows/<int:workflow_id>/toggle/",
        views.toggle_workflow,
        name="toggle_workflow",
    ),
    path("manage/logs/", views.activity_logs, name="activity_logs"),
    # profile
    path("profile/", views.profile, name="profile"),
    # JSON API
    path("api/courses/", views.api_courses, name="api_courses"),
    path("api/my-transcript/", views.api_my_transcript, name="api_my_transcript"),
    path("api/stats/", views.api_stats, name="api_stats"),
]
