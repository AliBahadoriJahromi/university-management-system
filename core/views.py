import csv
import io
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CourseForm, WorkflowForm
from .models import ActivityLog, Course, Enrollment, User, Workflow


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def course_selection_is_open():
    wf = Workflow.objects.filter(name="انتخاب واحد").first()
    if wf is None:
        return True
    return wf.is_active


def missing_prerequisites(student, course):
    missing = []
    for prereq in course.prerequisites.all():
        passed = Enrollment.objects.filter(
            student=student, course=prereq, grade__gte=10
        ).exists()
        if not passed:
            missing.append(prereq)
    return missing


def units_taken_this_semester(student, semester):
    total = 0
    for e in student.enrollments.select_related("course"):
        if e.course.semester == semester:
            total += e.course.units
    return total


def calculate_gpa(enrollments):
    total_points = 0
    total_units = 0
    for e in enrollments:
        if e.grade is not None:
            total_points += e.grade * e.course.units
            total_units += e.course.units
    if total_units == 0:
        return None
    return round(total_points / total_units, 2)


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------
def login_view(request):
    """The login page. Everyone starts here."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "نام کاربری یا رمز عبور اشتباه است.")

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


# ---------------------------------------------------------------------------
# Dashboard - sends each role to the right page
# ---------------------------------------------------------------------------
@login_required
def dashboard(request):
    user = request.user
    if user.is_student():
        return student_dashboard(request)
    elif user.is_professor():
        return professor_dashboard(request)
    elif user.is_manager():
        return manager_dashboard(request)
    return render(request, "dashboard_other.html")


# ---------------------------------------------------------------------------
# STUDENT pages
# ---------------------------------------------------------------------------
def student_dashboard(request):
    enrollments = request.user.enrollments.select_related("course")
    gpa = calculate_gpa(enrollments)
    context = {
        "enrollments": enrollments,
        "gpa": gpa,
        "selection_open": course_selection_is_open(),
    }
    return render(request, "student/dashboard.html", context)


@login_required
def course_selection(request):
    if not request.user.is_student():
        messages.error(request, "فقط دانشجویان می‌توانند انتخاب واحد کنند.")
        return redirect("dashboard")

    my_course_ids = request.user.enrollments.values_list("course_id", flat=True)
    courses = Course.objects.all().select_related("professor")

    semester_units = {}
    for e in request.user.enrollments.select_related("course"):
        sem = e.course.semester
        semester_units[sem] = semester_units.get(sem, 0) + e.course.units

    context = {
        "courses": courses,
        "my_course_ids": list(my_course_ids),
        "selection_open": course_selection_is_open(),
        "semester_units": semester_units,
        "max_units": settings.MAX_UNITS_PER_SEMESTER,
    }
    return render(request, "student/course_selection.html", context)


@login_required
def enroll(request, course_id):
    if not request.user.is_student():
        return redirect("dashboard")

    if not course_selection_is_open():
        messages.error(request, "انتخاب واحد توسط مدیر گروه بسته شده است.")
        return redirect("course_selection")

    course = get_object_or_404(Course, id=course_id)

    if course.is_full():
        messages.error(request, f"ظرفیت درس {course.title} تکمیل است.")
        return redirect("course_selection")

    # قانون ۱: دانشجو باید همه پیش‌نیازها را پاس کرده باشد.
    missing = missing_prerequisites(request.user, course)
    if missing:
        names = "، ".join(p.title for p in missing)
        messages.error(request, f"ابتدا باید این دروس را بگذرانید: {names}")
        return redirect("course_selection")

    # قانون ۲: دانشجو نباید از سقف واحد ترم بیشتر بگیرد.
    already = units_taken_this_semester(request.user, course.semester)
    limit = settings.MAX_UNITS_PER_SEMESTER
    if already + course.units > limit:
        messages.error(
            request,
            f"تعداد واحد زیاد است. سقف هر ترم {limit} واحد است "
            f"(شما هم‌اکنون {already} واحد دارید).",
        )
        return redirect("course_selection")

    # get_or_create از ثبت تکراری جلوگیری می‌کند
    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user, course=course
    )
    if created:
        messages.success(request, f"درس {course.title} اخذ شد.")
    else:
        messages.info(request, "این درس را قبلاً اخذ کرده‌اید.")
    return redirect("course_selection")


@login_required
def drop(request, course_id):
    if not request.user.is_student():
        return redirect("dashboard")

    Enrollment.objects.filter(student=request.user, course_id=course_id).delete()
    messages.success(request, "درس حذف شد.")
    return redirect("course_selection")


@login_required
def transcript(request):
    enrollments = request.user.enrollments.select_related("course").order_by(
        "course__semester"
    )
    semesters = {}
    for e in enrollments:
        semesters.setdefault(e.course.semester, []).append(e)

    semester_reports = []
    for sem, items in semesters.items():
        semester_reports.append(
            {"semester": sem, "items": items, "gpa": calculate_gpa(items)}
        )

    context = {
        "semester_reports": semester_reports,
        "total_gpa": calculate_gpa(enrollments),
    }
    return render(request, "student/transcript.html", context)


# ---------------------------------------------------------------------------
# PROFESSOR pages
# ---------------------------------------------------------------------------
def professor_dashboard(request):
    courses = request.user.courses_taught.all()
    return render(request, "professor/dashboard.html", {"courses": courses})


@login_required
def enter_grades(request, course_id):
    if not request.user.is_professor():
        messages.error(request, "فقط اساتید می‌توانند نمره ثبت کنند.")
        return redirect("dashboard")

    course = get_object_or_404(Course, id=course_id)

    if course.professor_id != request.user.id:
        messages.error(request, "این درس متعلق به شما نیست.")
        return redirect("dashboard")

    enrollments = course.enrollments.select_related("student")

    if request.method == "POST":
        for e in enrollments:
            value = request.POST.get(f"grade_{e.id}", "").strip()
            if value == "":
                e.grade = None
                e.save()
                continue
            try:
                grade = float(value)
            except ValueError:
                messages.error(request, f"«{value}» یک عدد معتبر نیست.")
                continue
            if 0 <= grade <= 20:
                e.grade = grade
                e.save()
            else:
                messages.error(request, "نمره باید بین ۰ تا ۲۰ باشد.")
        messages.success(request, "نمرات ذخیره شد.")
        return redirect("enter_grades", course_id=course.id)

    return render(
        request,
        "professor/enter_grades.html",
        {"course": course, "enrollments": enrollments},
    )


# ---------------------------------------------------------------------------
# MANAGER pages
# ---------------------------------------------------------------------------
def manager_dashboard(request):
    context = {
        "course_count": Course.objects.count(),
        "student_count": User.objects.filter(role=User.STUDENT).count(),
        "professor_count": User.objects.filter(role=User.PROFESSOR).count(),
        "enrollment_count": Enrollment.objects.count(),
        "workflows": Workflow.objects.all(),
    }
    return render(request, "manager/dashboard.html", context)


@login_required
def add_course(request):
    """Manager adds a new course."""
    if not request.user.is_manager():
        messages.error(request, "فقط مدیر گروه می‌تواند درس اضافه کند.")
        return redirect("dashboard")

    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "درس اضافه شد.")
            return redirect("course_list")
    else:
        form = CourseForm()
    return render(request, "manager/add_course.html", {"form": form})


@login_required
def course_list(request):
    """Manager sees all courses (with a search box)."""
    if not request.user.is_manager():
        return redirect("dashboard")

    query = request.GET.get("q", "")
    courses = Course.objects.all().select_related("professor")
    if query:
        courses = courses.filter(
            Q(code__icontains=query) | Q(title__icontains=query)
        )
    return render(
        request, "manager/course_list.html", {"courses": courses, "query": query}
    )


@login_required
def reports(request):
    """
    Reports and search for the manager (گزارش‌گیری و جستجو).
    - search students by name or student number
    - see the average grade of every course
    """
    if not request.user.is_manager():
        return redirect("dashboard")

    query = request.GET.get("q", "")
    students = User.objects.filter(role=User.STUDENT)
    if query:
        students = students.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(username__icontains=query)
            | Q(student_number__icontains=query)
        )

    student_rows = []
    for s in students:
        gpa = calculate_gpa(s.enrollments.select_related("course"))
        student_rows.append({"student": s, "gpa": gpa})

    course_stats = (
        Course.objects.annotate(
            avg_grade=Avg("enrollments__grade"),
            num_students=Count("enrollments"),
        )
    )

    context = {
        "student_rows": student_rows,
        "course_stats": course_stats,
        "query": query,
    }
    return render(request, "manager/reports.html", context)


@login_required
def workflows(request):
    if not request.user.is_manager():
        return redirect("dashboard")

    if request.method == "POST":
        form = WorkflowForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "گردش کار ذخیره شد.")
            return redirect("workflows")
    else:
        form = WorkflowForm()

    return render(
        request,
        "manager/workflows.html",
        {"form": form, "workflows": Workflow.objects.all()},
    )


@login_required
def toggle_workflow(request, workflow_id):
    if not request.user.is_manager():
        return redirect("dashboard")
    wf = get_object_or_404(Workflow, id=workflow_id)
    wf.is_active = not wf.is_active
    wf.save()
    return redirect("workflows")


@login_required
def export_students_csv(request):
    if not request.user.is_manager():
        return redirect("dashboard")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["شماره دانشجویی", "نام", "نام کاربری", "تعداد دروس", "معدل"])

    for s in User.objects.filter(role=User.STUDENT):
        gpa = calculate_gpa(s.enrollments.select_related("course"))
        writer.writerow([
            s.student_number,
            s.get_full_name(),
            s.username,
            s.enrollments.count(),
            gpa if gpa is not None else "-",
        ])

    content = output.getvalue().encode("utf-8-sig")
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="students.csv"'
    return response


@login_required
def activity_logs(request):
    if not request.user.is_manager():
        return redirect("dashboard")
    logs = ActivityLog.objects.select_related("user").order_by("-created_at")[:100]
    return render(request, "manager/logs.html", {"logs": logs})


# ---------------------------------------------------------------------------
# JSON API (طراحی API)
# These return data as JSON instead of HTML. They can be used by other
# programs or by JavaScript. They are simple on purpose.
# ---------------------------------------------------------------------------
@login_required
def api_courses(request):
    data = []
    for c in Course.objects.select_related("professor"):
        data.append(
            {
                "id": c.id,
                "code": c.code,
                "title": c.title,
                "units": c.units,
                "capacity": c.capacity,
                "free_seats": c.free_seats(),
                "semester": c.semester,
                "professor": c.professor.get_full_name() if c.professor else None,
            }
        )
    return JsonResponse({"courses": data})


@login_required
def api_my_transcript(request):
    if not request.user.is_student():
        return JsonResponse({"error": "only students have a transcript"}, status=403)

    enrollments = request.user.enrollments.select_related("course")
    data = []
    for e in enrollments:
        data.append(
            {
                "course": e.course.title,
                "code": e.course.code,
                "units": e.course.units,
                "semester": e.course.semester,
                "grade": e.grade,
                "passed": e.is_passed(),
            }
        )
    return JsonResponse(
        {"student": request.user.username, "gpa": calculate_gpa(enrollments), "courses": data}
    )


@login_required
def api_stats(request):
    return JsonResponse(
        {
            "courses": Course.objects.count(),
            "students": User.objects.filter(role=User.STUDENT).count(),
            "professors": User.objects.filter(role=User.PROFESSOR).count(),
            "enrollments": Enrollment.objects.count(),
        }
    )


# ---------------------------------------------------------------------------
# پروفایل و تغییر رمز عبور (همه نقش‌ها)
# ---------------------------------------------------------------------------
@login_required
def profile(request):
    user = request.user
    error = None 

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "update_name":
            first = request.POST.get("first_name", "").strip()
            last = request.POST.get("last_name", "").strip()
            if first or last:
                user.first_name = first
                user.last_name = last
                user.save()
                messages.success(request, "نام شما بروز شد.")
                return redirect("profile")
            else:
                error = "نام نمی‌تواند خالی باشد."

        elif action == "change_password":
            old = request.POST.get("old_password", "")
            new1 = request.POST.get("new_password1", "")
            new2 = request.POST.get("new_password2", "")

            if not user.check_password(old):
                error = "رمز عبور فعلی اشتباه است."
            elif len(new1) < 4:
                error = "رمز عبور جدید باید حداقل ۴ کاراکتر باشد."
            elif new1 != new2:
                error = "رمز عبور جدید و تکرار آن یکسان نیستند."
            else:
                user.set_password(new1)
                user.save()
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                messages.success(request, "رمز عبور تغییر کرد.")
                return redirect("profile")

    return render(request, "profile.html", {"user": user, "error": error})
