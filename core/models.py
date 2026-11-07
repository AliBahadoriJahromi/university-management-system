from django.contrib.auth.models import AbstractUser
from django.db import models

# Database models.
#- User: a person who logs in (student, professor, manager)
#- Course: a class that a professor teaches
#- Enrollment: connects one student to one course
#- Workflow: a simple rule/process created by the manager
#- ActivityLog: a record of what users do in the system
class User(AbstractUser):
    STUDENT = "student"
    PROFESSOR = "professor"
    MANAGER = "manager"

    ROLE_CHOICES = [
        (STUDENT, "دانشجو"),
        (PROFESSOR, "استاد"),
        (MANAGER, "مدیر گروه"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=STUDENT)
    student_number = models.CharField(max_length=20, blank=True)
    national_id = models.CharField(max_length=20, blank=True)

    def is_student(self):
        return self.role == self.STUDENT

    def is_professor(self):
        return self.role == self.PROFESSOR

    def is_manager(self):
        return self.role == self.MANAGER

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=120)
    units = models.PositiveSmallIntegerField(default=3)
    capacity = models.PositiveSmallIntegerField(default=30)
    semester = models.CharField(max_length=20, default="2026-1")
    professor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"role": User.PROFESSOR},
        related_name="courses_taught",
    )

    prerequisites = models.ManyToManyField(
        "self", symmetrical=False, blank=True, related_name="needed_for"
    )

    def taken_seats(self):
        return self.enrollments.count()

    def free_seats(self):
        return self.capacity - self.taken_seats()

    def is_full(self):
        return self.free_seats() <= 0

    def __str__(self):
        return f"{self.code} - {self.title}"


class Enrollment(models.Model):

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role": User.STUDENT},
        related_name="enrollments",
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="enrollments"
    )
    grade = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")

    def is_passed(self):
        return self.grade is not None and self.grade >= 10

    def __str__(self):
        return f"{self.student.username} -> {self.course.code}"


class Workflow(models.Model):
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "active" if self.is_active else "closed"
        return f"{self.name} ({status})"


class ActivityLog(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    action = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        who = self.user.username if self.user else "anonymous"
        return f"{who}: {self.action}"
