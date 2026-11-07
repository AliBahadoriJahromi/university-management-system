"""
A management command that fills the database with sample (fake) data
so we can test the program right away.

Run it with:   python manage.py seed_data

It creates:
- 1 manager, 3 professors, 8 students
- some courses
- random course selections and some grades
- a couple of workflows

All users have the password: 1234
"""

import random

from django.core.management.base import BaseCommand

from core.models import User, Course, Enrollment, Workflow


class Command(BaseCommand):
    help = "Fill the database with sample data for testing."

    def handle(self, *args, **options):
        self.stdout.write("Deleting old data...")
        Enrollment.objects.all().delete()
        Course.objects.all().delete()
        Workflow.objects.all().delete()
        # keep superusers, delete the rest
        User.objects.filter(is_superuser=False).delete()

        password = "1234"

        # ---- Manager ----
        manager = User.objects.create_user(
            username="manager",
            password=password,
            first_name="سارا",
            last_name="احمدی",
            role=User.MANAGER,
        )

        # ---- Professors ----
        professor_names = [
            ("علی", "رضایی"),
            ("مریم", "حسینی"),
            ("رضا", "کریمی"),
        ]
        professors = []
        for i, (first, last) in enumerate(professor_names, start=1):
            p = User.objects.create_user(
                username=f"prof{i}",
                password=password,
                first_name=first,
                last_name=last,
                role=User.PROFESSOR,
            )
            professors.append(p)

        # ---- Students ----
        student_names = [
            ("محمد", "احمدی"),
            ("زهرا", "مرادی"),
            ("حسین", "جعفری"),
            ("فاطمه", "باقری"),
            ("امیر", "صادقی"),
            ("نازنین", "قربانی"),
            ("مهدی", "اکبری"),
            ("سارا", "موسوی"),
        ]
        students = []
        for i, (first, last) in enumerate(student_names, start=1):
            s = User.objects.create_user(
                username=f"student{i}",
                password=password,
                first_name=first,
                last_name=last,
                role=User.STUDENT,
                student_number=f"40{i:05d}",
            )
            students.append(s)

        # ---- Courses ----
        course_data = [
            ("CS101", "مبانی برنامه‌نویسی", 3, "2026-1"),
            ("CS102", "ساختمان داده‌ها", 3, "2026-1"),
            ("MTH101", "ریاضی ۱", 4, "2026-1"),
            ("DB201", "پایگاه داده‌ها", 3, "2026-1"),
            ("NET301", "شبکه‌های کامپیوتری", 3, "2026-1"),
            ("CS103", "برنامه‌نویسی وب", 3, "2025-2"),
            ("MTH102", "ریاضی ۲", 4, "2025-2"),
        ]
        courses = []
        for code, title, units, semester in course_data:
            c = Course.objects.create(
                code=code,
                title=title,
                units=units,
                capacity=30,
                semester=semester,
                professor=random.choice(professors),
            )
            courses.append(c)

        # ---- Prerequisites ----
        # Make a small dictionary so we can find a course by its code.
        by_code = {c.code: c for c in courses}
        # "X needs Y" pairs:
        prereq_pairs = [
            ("CS102", "CS101"),   # Data Structures needs Intro to Programming
            ("DB201", "CS102"),   # Databases needs Data Structures
            ("NET301", "CS102"),  # Networks needs Data Structures
            ("MTH102", "MTH101"), # Calculus 2 needs Calculus 1
        ]
        for course_code, needs_code in prereq_pairs:
            by_code[course_code].prerequisites.add(by_code[needs_code])

        # ---- Random course selections + grades ----
        for student in students:
            chosen = random.sample(courses, k=random.randint(3, 5))
            for course in chosen:
                # courses from the past semester get a grade, current ones may be empty
                if course.semester == "2025-2":
                    grade = round(random.uniform(8, 20), 1)
                else:
                    grade = round(random.uniform(8, 20), 1) if random.random() < 0.5 else None
                Enrollment.objects.create(
                    student=student, course=course, grade=grade
                )

        # ---- Workflows ----
        # نکته: نام «انتخاب واحد» در views.py به‌عنوان کلید استفاده می‌شود،
        # پس باید دقیقاً همین متن باشد.
        Workflow.objects.create(
            name="انتخاب واحد",
            description="وقتی فعال باشد، دانشجویان می‌توانند درس انتخاب کنند.",
            is_active=True,
        )
        Workflow.objects.create(
            name="درخواست تجدیدنظر نمره",
            description="وقتی فعال باشد، دانشجویان می‌توانند درخواست بازبینی نمره بدهند.",
            is_active=False,
        )

        # نکته: پیام‌های کنسول را انگلیسی نگه می‌داریم چون کنسول ویندوز
        # گاهی نمی‌تواند متن فارسی را چاپ کند. رابط کاربری سامانه فارسی است.
        self.stdout.write(self.style.SUCCESS("Done! Sample (Persian) data created."))
        self.stdout.write("Login accounts (password: 1234):")
        self.stdout.write("  manager   -> Group Manager")
        self.stdout.write("  prof1     -> Professor")
        self.stdout.write("  student1  -> Student")
