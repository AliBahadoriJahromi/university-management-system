from django import forms
from .models import Course, Workflow

class CourseForm(forms.ModelForm):
    """فرم مدیر گروه برای افزودن درس جدید."""

    class Meta:
        model = Course
        fields = [
            "code", "title", "units", "capacity",
            "semester", "professor", "prerequisites",
        ]
        labels = {
            "code": "کد درس",
            "title": "عنوان درس",
            "units": "تعداد واحد",
            "capacity": "ظرفیت",
            "semester": "ترم",
            "professor": "استاد",
            "prerequisites": "پیش‌نیازها",
        }


class WorkflowForm(forms.ModelForm):
    """فرم مدیر گروه برای تعریف گردش کار."""

    class Meta:
        model = Workflow
        fields = ["name", "description", "is_active"]
        labels = {
            "name": "نام",
            "description": "توضیحات",
            "is_active": "فعال باشد",
        }
