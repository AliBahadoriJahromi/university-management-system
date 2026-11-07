# Educational System (LMS) — Technical Document

A simple **Educational Management System** built with **Django**.

---

## 1. What the project does

The system has **three main roles**, and each role sees a different dashboard:

| Role | What they can do |
|------|------------------|
| **Student** | Log in, see their dashboard, select courses, drop courses, view the term report card and the overall report card (transcript). |
| **Professor** | Log in, see the courses they teach, and enter grades for their students. |
| **Group Manager** | Log in, add new courses, search and run reports, see statistics, create/turn on-off workflows, and read user activity logs. |


---

## 2. How to run the project

You need **Python 3.10+**.

```bash
# 1) (optional) create a virtual environment
python -m venv venv
venv\Scripts\activate          # on Windows

# 2) install Django
pip install -r requirements.txt

# 3) create the database tables
python manage.py migrate

# 4) load the sample (fake) data
python manage.py seed_data

# 5) start the server
python manage.py runserver
```

Then open **http://127.0.0.1:8000/** in your browser.

### Demo accounts (password is `1234` for all of them)

| Username | Role |
|----------|------|
| `manager` | Group Manager |
| `prof1`, `prof2`, `prof3` | Professor |
| `student1` … `student8` | Student |

---

## 3. Project structure

```
edusystem/            ← project settings (settings.py, urls.py, wsgi.py)
core/                 ← the main app (all the logic)
    models.py         ← database tables (User, Course, Enrollment, Workflow, ActivityLog)
    views.py          ← the pages (login, dashboards, course selection, grades, reports...)
    urls.py           ← which address opens which page
    forms.py          ← simple forms (add course, add workflow)
    admin.py          ← shows the models in the Django admin panel
    middleware.py     ← writes a log line when a user changes data
    tests.py          ← automated tests
    management/commands/seed_data.py  ← creates the sample data
templates/            ← the HTML pages
static/style.css      ← the responsive design (CSS)
simple_test.py         ← a quick test that opens every page to check it loads
```

---

## 4. The data model (database)

There are 5 tables:

- **User** — a person who logs in. It is Django's normal user plus a `role`
  field (`student`, `professor`, or `manager`).
- **Course** — a class (code, title, units, capacity, semester, professor).
- **Enrollment** — connects one student to one course and stores the `grade`.
  A student cannot take the same course twice (`unique_together`).
- **Workflow** — a rule the manager controls (for example, "Course Selection"
  can be open or closed).
- **ActivityLog** — a record of everything a does.

Relationships:

```
Professor (User) --< Course --< Enrollment >-- Student (User)
```

---

## 5. The APIs

The project has a few simple **JSON APIs** (they return data, not HTML).
You must be logged in to use them.

| Method | URL | What it returns |
|--------|-----|-----------------|
| GET | `/api/courses/` | The list of all courses with free seats. |
| GET | `/api/my-transcript/` | The logged-in student's grades and GPA. |
| GET | `/api/stats/` | General numbers (counts of courses, students…). |

Example response of `/api/stats/`:

```json
{ "courses": 7, "students": 8, "professors": 3, "enrollments": 30 }
```

---

## 6. Access control (security)

- Every page that needs a login uses Django's `@login_required`.
- Each view checks the **role** before doing something. For example, only a
  student can take a course, and a professor can only enter grades for a
  course **they teach**.
- Django gives us security for free: hashed passwords, CSRF protection on
  every form, and protection against SQL injection (because of the ORM).
- The GPA, capacity check, and "course selection open/closed" rules are all
  checked on the **server side**, so a user cannot bypass them from the browser.

---

## 7. The GPA calculation

The GPA is a **weighted average**: each course counts by its number of units.

```
GPA = sum(grade × units) / sum(units)
```

Only courses that already have a grade are counted. The report card page
(`/transcript/`) shows the GPA **per semester** and the **overall** GPA.

---

## 8. Workflows (controlled by the manager)

A **Workflow** is a simple on/off rule. The most important one is
**"Course Selection"**:

- When it is **active**, students can choose their courses.
- When the manager turns it **off**, the system refuses new course selections.

The manager can create new workflows and turn any workflow on or off with one
click on the Workflows page.

---

## 9. Testing

There are two ways the project is tested:

1. **Automated tests** (`core/tests.py`) — run with:
   ```bash
   python manage.py test
   ```
   it check: taking/dropping a course, the manager closing course selection,
   the course capacity limit, grade entry + GPA, and that a professor cannot
   grade another professor's course.

2. **Simple test** (`simple_test.py`) — a quick test that logs in as each role
   and opens every main page to make sure nothing crashes:
   ```bash
   python simple_test.py
   ```

---

## 10. SDLC (software life cycle) — short version

1. **Design** — the data model (section 4) and the role/permission design.
2. **Implementation** — the Django app in the `core/` folder.
3. **Testing** — automated tests and the simple test (section 9).
4. **Deployment** — run with `python manage.py runserver`.
5. **Maintenance** — the code is split into small, commented files so it is
   easy to change.

---

## 11. Responsive design

The CSS in `static/style.css` uses a flexible layout (`grid` with
`auto-fit`, percentage widths, and a `@media` query). Tables scroll
horizontally inside `.table-wrap` on small screens, and the navigation bar
stacks vertically on phones. The `<meta name="viewport">` tag makes the page
scale correctly on mobile devices.

---

## 12. Extra rules and features

- **Prerequisites** — a course can require other courses. A student can only
  take a course after they have **passed** all of its prerequisites (grade ≥ 10).
  The prerequisites are shown on the course-selection page, and the manager can
  set them when adding a course. (See `missing_prerequisites()` in `views.py`.)
- **Maximum units per semester** — a student cannot take more than
  `MAX_UNITS_PER_SEMESTER` units (default **20**, set in `settings.py`) in one
  semester. (See `units_taken_this_semester()` in `views.py`.)
- **CSV export (bulk export)** — on the Reports page the manager can click
  *"Export students to CSV"* to download all students and their GPA as a CSV
  file that opens in Excel. (`/manage/reports/export/`)

---

"# university_web" 
