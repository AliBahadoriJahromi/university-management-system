"""
Automated tests for the educational system.

Run them with:  python manage.py test

These tests check the most important rules of the program:
- a student can take a course and drop it
- course selection respects the manager's workflow
- a professor can give a grade and the GPA is calculated
- a course cannot go over its capacity
"""

from django.test import TestCase
from django.urls import reverse

from .models import User, Course, Enrollment, Workflow


class EduSystemTests(TestCase):
    def setUp(self):
        # one of each role
        self.manager = User.objects.create_user(
            username="m", password="1234", role=User.MANAGER
        )
        self.professor = User.objects.create_user(
            username="p", password="1234", role=User.PROFESSOR
        )
        self.student = User.objects.create_user(
            username="s", password="1234", role=User.STUDENT
        )
        self.course = Course.objects.create(
            code="C1", title="Test Course", units=3, capacity=1,
            semester="2026-1", professor=self.professor,
        )

    def test_student_can_take_and_drop_course(self):
        self.client.login(username="s", password="1234")

        # take the course
        self.client.post(reverse("enroll", args=[self.course.id]))
        self.assertEqual(Enrollment.objects.count(), 1)

        # drop the course
        self.client.post(reverse("drop", args=[self.course.id]))
        self.assertEqual(Enrollment.objects.count(), 0)

    def test_course_selection_can_be_closed_by_manager(self):
        # manager closes course selection
        Workflow.objects.create(name="انتخاب واحد", is_active=False)

        self.client.login(username="s", password="1234")
        self.client.post(reverse("enroll", args=[self.course.id]))

        # no enrollment because selection is closed
        self.assertEqual(Enrollment.objects.count(), 0)

    def test_course_capacity_is_respected(self):
        # capacity is 1, so the second student should fail
        other = User.objects.create_user(
            username="s2", password="1234", role=User.STUDENT
        )

        self.client.login(username="s", password="1234")
        self.client.post(reverse("enroll", args=[self.course.id]))
        self.client.logout()

        self.client.login(username="s2", password="1234")
        self.client.post(reverse("enroll", args=[self.course.id]))

        # still only 1 student
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertFalse(
            Enrollment.objects.filter(student=other).exists()
        )

    def test_professor_can_set_grade_and_gpa_is_calculated(self):
        enrollment = Enrollment.objects.create(
            student=self.student, course=self.course
        )

        self.client.login(username="p", password="1234")
        self.client.post(
            reverse("enter_grades", args=[self.course.id]),
            {f"grade_{enrollment.id}": "18"},
        )

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.grade, 18)
        self.assertTrue(enrollment.is_passed())

    def test_prerequisite_blocks_enrollment(self):
        # intro must be passed before advanced
        intro = Course.objects.create(
            code="INTRO", title="Intro", units=3, capacity=10, semester="2026-1"
        )
        advanced = Course.objects.create(
            code="ADV", title="Advanced", units=3, capacity=10, semester="2026-1"
        )
        advanced.prerequisites.add(intro)

        self.client.login(username="s", password="1234")

        # student has NOT passed intro -> cannot take advanced
        self.client.post(reverse("enroll", args=[advanced.id]))
        self.assertFalse(
            Enrollment.objects.filter(student=self.student, course=advanced).exists()
        )

        # now the student passes intro (grade 15) -> can take advanced
        Enrollment.objects.create(student=self.student, course=intro, grade=15)
        self.client.post(reverse("enroll", args=[advanced.id]))
        self.assertTrue(
            Enrollment.objects.filter(student=self.student, course=advanced).exists()
        )

    def test_units_limit_per_semester(self):
        # fill the student up to the limit (20 units) with a 18-unit load,
        # then try to add a course that pushes over the limit.
        big = Course.objects.create(
            code="BIG", title="Big", units=18, capacity=10, semester="2026-1"
        )
        Enrollment.objects.create(student=self.student, course=big)

        # self.course is 3 units -> 18 + 3 = 21 > 20, should be refused
        self.client.login(username="s", password="1234")
        self.client.post(reverse("enroll", args=[self.course.id]))
        self.assertFalse(
            Enrollment.objects.filter(student=self.student, course=self.course).exists()
        )

    def test_profile_change_name(self):
        self.client.login(username="s", password="1234")
        self.client.post("/profile/", {
            "action": "update_name",
            "first_name": "نام جدید",
            "last_name": "فامیل جدید",
        })
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, "نام جدید")

    def test_profile_change_password_wrong_old(self):
        self.client.login(username="s", password="1234")
        resp = self.client.post("/profile/", {
            "action": "change_password",
            "old_password": "wrong",
            "new_password1": "newpass",
            "new_password2": "newpass",
        })
        # should show an error, not change
        self.assertContains(resp, "اشتباه")
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password("1234"))

    def test_export_students_csv(self):
        self.client.login(username="m", password="1234")
        response = self.client.get(reverse("export_students_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("شماره دانشجویی", response.content.decode("utf-8"))

    def test_professor_cannot_grade_another_professors_course(self):
        other_prof = User.objects.create_user(
            username="p2", password="1234", role=User.PROFESSOR
        )
        self.client.login(username="p2", password="1234")
        response = self.client.get(reverse("enter_grades", args=[self.course.id]))
        # they get redirected away (not their course)
        self.assertEqual(response.status_code, 302)
