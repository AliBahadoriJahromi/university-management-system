from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Course, Enrollment, Workflow, ActivityLog

admin.site.site_header = "مدیریت سامانه آموزشی"
admin.site.site_title = "سامانه آموزشی"
admin.site.index_title = "پنل مدیریت"

class MyUserAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "role", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Extra info", {"fields": ("role", "student_number", "national_id")}),
    )

admin.site.register(User, MyUserAdmin)
admin.site.register(Course)
admin.site.register(Enrollment)
admin.site.register(Workflow)
admin.site.register(ActivityLog)
