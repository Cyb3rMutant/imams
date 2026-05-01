from datetime import date, timedelta
from functools import wraps

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import ImamForm, MosqueForm, MosqueSettingsForm, TrainingVideoForm
from .models import (
    Assignment, Imam, ImamReview, ImamUnavailability, Mosque,
    QuizAttempt, QuizChoice, QuizQuestion,
    TrainingProgress, TrainingVideo, WeekRequest,
)


def _get_friday(d: date) -> date:
    return d + timedelta(days=(4 - d.weekday()) % 7)


def _upcoming_fridays() -> list[date]:
    today = date.today()
    first = _get_friday(today) if today.weekday() != 4 else today
    cutoff = today + timedelta(days=60)
    fridays, d = [], first
    while d <= cutoff:
        fridays.append(d)
        d += timedelta(days=7)
    return fridays


def _trained_imam_ids() -> set[int] | None:
    if not QuizQuestion.objects.exists():
        return None  # no quiz configured → no training gate
    return set(QuizAttempt.objects.filter(passed=True).values_list("imam_id", flat=True))



# ── Portal auth decorators ────────────────────────────────────────────────────

def mosque_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("mosque_id"):
            return redirect("mosque_login")
        return view_func(request, *args, **kwargs)
    return wrapper


def imam_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("imam_id"):
            return redirect("imam_login")
        return view_func(request, *args, **kwargs)
    return wrapper


# ── Public registration ───────────────────────────────────────────────────────

def home(request):
    return render(request, "scheduler/home.html")


def mosque_register(request):
    if request.method == "POST":
        form = MosqueForm(request.POST)
        if form.is_valid():
            mosque = form.save()
            return redirect("success", kind="mosque", pk=mosque.pk)
    else:
        form = MosqueForm()
    return render(request, "scheduler/mosque_request.html", {"form": form})


def imam_register(request):
    if request.method == "POST":
        form = ImamForm(request.POST)
        if form.is_valid():
            imam = form.save()
            return redirect("success", kind="imam", pk=imam.pk)
    else:
        form = ImamForm()
    return render(request, "scheduler/imam_application.html", {"form": form})


def success(request, kind, pk):
    copy = {
        "mosque": (
            "Your mosque has been registered.",
            "Use your ID to log in to your mosque portal and request Jumuah dates.",
            reverse("mosque_login"), "Go to Mosque Portal",
        ),
        "imam": (
            "Your application has been submitted.",
            "Use your ID to log in to your imam portal and complete your training.",
            reverse("imam_login"), "Go to Imam Portal",
        ),
    }
    heading, body, login_url, login_label = copy.get(kind, ("Done", "", "/", "Home"))
    return render(request, "scheduler/success.html", {
        "heading": heading, "body": body,
        "pk": pk, "login_url": login_url, "login_label": login_label,
    })


# ── Login / logout ────────────────────────────────────────────────────────────

def mosque_login(request):
    error = None
    if request.method == "POST":
        raw = request.POST.get("portal_id", "").strip()
        try:
            mosque = Mosque.objects.get(pk=int(raw))
            request.session["mosque_id"] = mosque.pk
            request.session.pop("imam_id", None)
            return redirect("mosque_portal")
        except (Mosque.DoesNotExist, ValueError):
            error = "No mosque found with that ID."
    return render(request, "scheduler/login.html", {
        "error": error, "portal_type": "Mosque",
        "action_url": reverse("mosque_login"),
        "other_label": "Imam Portal", "other_url": reverse("imam_login"),
    })


def imam_login(request):
    error = None
    if request.method == "POST":
        raw = request.POST.get("portal_id", "").strip()
        try:
            imam = Imam.objects.get(pk=int(raw))
            request.session["imam_id"] = imam.pk
            request.session.pop("mosque_id", None)
            return redirect("imam_portal")
        except (Imam.DoesNotExist, ValueError):
            error = "No imam found with that ID."
    return render(request, "scheduler/login.html", {
        "error": error, "portal_type": "Imam",
        "action_url": reverse("imam_login"),
        "other_label": "Mosque Portal", "other_url": reverse("mosque_login"),
    })


def portal_logout(request):
    request.session.pop("mosque_id", None)
    request.session.pop("imam_id", None)
    return redirect("home")


# ── Mosque portal ─────────────────────────────────────────────────────────────

@mosque_login_required
def mosque_portal(request):
    mosque = get_object_or_404(Mosque, pk=request.session["mosque_id"])

    if request.method == "POST":
        settings_form = MosqueSettingsForm(request.POST, instance=mosque)
        if settings_form.is_valid():
            settings_form.save()
            return redirect("mosque_portal")
    else:
        settings_form = MosqueSettingsForm(instance=mosque)

    existing = {
        wr.jumuah_date: wr
        for wr in mosque.week_requests.select_related("assignment__imam").all()
    }
    friday_rows = [{"date": f, "week_request": existing.get(f)} for f in _upcoming_fridays()]

    # Past assignments with review info
    past_assignments = (
        Assignment.objects
        .filter(week_request__mosque=mosque, week_request__jumuah_date__lt=date.today())
        .select_related("week_request", "imam")
        .order_by("-week_request__jumuah_date")
    )
    past_rows = []
    past_imam_ids = set()
    for a in past_assignments:
        past_imam_ids.add(a.imam_id)
        try:
            review = a.review
        except ImamReview.DoesNotExist:
            review = None
        past_rows.append({"assignment": a, "review": review})

    past_imams = Imam.objects.filter(pk__in=past_imam_ids).order_by("name")

    return render(request, "scheduler/mosque_portal.html", {
        "mosque": mosque,
        "settings_form": settings_form,
        "friday_rows": friday_rows,
        "past_rows": past_rows,
        "past_imams": past_imams,
    })


@mosque_login_required
def set_preferred_imam(request):
    if request.method == "POST":
        mosque = get_object_or_404(Mosque, pk=request.session["mosque_id"])
        imam_id = request.POST.get("preferred_imam_id") or None
        if imam_id:
            # Only allow imams this mosque has worked with
            valid = Assignment.objects.filter(
                week_request__mosque=mosque, imam_id=imam_id
            ).exists()
            if valid:
                mosque.preferred_imam_id = imam_id
                mosque.save(update_fields=["preferred_imam"])
        else:
            mosque.preferred_imam = None
            mosque.save(update_fields=["preferred_imam"])
    return redirect("mosque_portal")


@mosque_login_required
def request_friday(request):
    if request.method == "POST":
        mosque = get_object_or_404(Mosque, pk=request.session["mosque_id"])
        date_str = request.POST.get("jumuah_date", "")
        try:
            jumuah_date = date.fromisoformat(date_str)
            today = date.today()
            if jumuah_date.weekday() == 4 and jumuah_date >= today and jumuah_date <= today + timedelta(days=60):
                WeekRequest.objects.get_or_create(mosque=mosque, jumuah_date=jumuah_date)
        except ValueError:
            pass
    return redirect("mosque_portal")


@mosque_login_required
def cancel_week_request(request, pk):
    mosque = get_object_or_404(Mosque, pk=request.session["mosque_id"])
    wr = get_object_or_404(WeekRequest, pk=pk, mosque=mosque)
    if not wr.is_assigned:
        wr.delete()
    return redirect("mosque_portal")


@mosque_login_required
def submit_review(request, pk):
    if request.method != "POST":
        return redirect("mosque_portal")
    mosque = get_object_or_404(Mosque, pk=request.session["mosque_id"])
    assignment = get_object_or_404(Assignment, pk=pk, week_request__mosque=mosque)
    if assignment.week_request.jumuah_date >= date.today():
        return redirect("mosque_portal")
    rating_str = request.POST.get("rating", "")
    comment = request.POST.get("comment", "").strip()
    try:
        rating = int(rating_str)
        if 1 <= rating <= 5:
            ImamReview.objects.update_or_create(
                assignment=assignment,
                defaults={"rating": rating, "comment": comment},
            )
    except ValueError:
        pass
    return redirect("mosque_portal")


# ── Imam portal ───────────────────────────────────────────────────────────────

@imam_login_required
def imam_portal(request):
    imam = get_object_or_404(Imam, pk=request.session["imam_id"])
    today = date.today()

    all_assignments = (
        imam.assignments
        .select_related("week_request__mosque")
        .order_by("week_request__jumuah_date")
    )
    upcoming = [a for a in all_assignments if a.week_request.jumuah_date >= today]
    past     = [a for a in all_assignments if a.week_request.jumuah_date < today]

    unavailable_dates = set(
        imam.unavailabilities
        .filter(jumuah_date__gte=today)
        .values_list("jumuah_date", flat=True)
    )
    assigned_dates = {a.week_request.jumuah_date for a in upcoming}
    cutoff = today + timedelta(days=7)
    availability_rows = [
        {
            "date": f,
            "unavailable": f in unavailable_dates,
            "assigned": f in assigned_dates,
            "too_soon": f <= cutoff,
        }
        for f in _upcoming_fridays()
    ]

    return render(request, "scheduler/imam_portal.html", {
        "imam": imam,
        "upcoming": upcoming,
        "past": past,
        "availability_rows": availability_rows,
        "is_trained": imam.is_trained,
    })


@imam_login_required
def toggle_unavailability(request):
    if request.method == "POST":
        imam = get_object_or_404(Imam, pk=request.session["imam_id"])
        date_str = request.POST.get("jumuah_date", "")
        try:
            jumuah_date = date.fromisoformat(date_str)
            if jumuah_date.weekday() == 4 and jumuah_date > date.today() + timedelta(days=7):
                obj, created = ImamUnavailability.objects.get_or_create(imam=imam, jumuah_date=jumuah_date)
                if not created:
                    obj.delete()
                else:
                    Assignment.objects.filter(imam=imam, week_request__jumuah_date=jumuah_date).delete()
        except ValueError:
            pass
    return redirect("imam_portal")


@imam_login_required
def imam_training(request):
    imam = get_object_or_404(Imam, pk=request.session["imam_id"])
    videos = list(TrainingVideo.objects.all())
    questions = list(QuizQuestion.objects.prefetch_related("choices").all())
    try:
        attempt = imam.quiz_attempt
    except QuizAttempt.DoesNotExist:
        attempt = None
    return render(request, "scheduler/imam_training.html", {
        "imam": imam,
        "videos": videos,
        "questions": questions,
        "attempt": attempt,
        "is_trained": imam.is_trained,
    })


@imam_login_required
def submit_quiz(request):
    if request.method != "POST":
        return redirect("imam_training")
    imam = get_object_or_404(Imam, pk=request.session["imam_id"])
    questions = list(QuizQuestion.objects.prefetch_related("choices").all())
    if not questions:
        return redirect("imam_training")
    score = 0
    for q in questions:
        selected_id = request.POST.get(f"q{q.pk}")
        if selected_id:
            try:
                choice = q.choices.get(pk=int(selected_id))
                if choice.is_correct:
                    score += 1
            except (QuizChoice.DoesNotExist, ValueError):
                pass
    total = len(questions)
    QuizAttempt.objects.update_or_create(
        imam=imam,
        defaults={"passed": score == total, "score": score, "total": total},
    )
    return redirect("imam_training")


# ── Combined admin panel ──────────────────────────────────────────────────────

@staff_member_required
def admin_panel(request):
    # Resolve current Friday for schedule section
    week_str = request.GET.get("week", "")
    try:
        friday = date.fromisoformat(week_str)
    except (ValueError, TypeError):
        friday = _get_friday(date.today())

    video_form = TrainingVideoForm()

    if request.method == "POST":
        action = request.POST.get("action", "")
        # Re-parse friday from POST so redirects preserve week
        try:
            friday = date.fromisoformat(request.POST.get("week", ""))
        except (ValueError, TypeError):
            pass

        if action == "assign":
            wr_pk   = request.POST.get("request_id")
            imam_id = request.POST.get("imam_id") or None
            try:
                wr = WeekRequest.objects.get(pk=wr_pk)
                if imam_id:
                    imam = Imam.objects.get(pk=imam_id)
                    already = Assignment.objects.filter(
                        imam=imam, week_request__jumuah_date=wr.jumuah_date,
                    ).exclude(week_request=wr).exists()
                    if not already:
                        Assignment.objects.update_or_create(
                            week_request=wr, defaults={"imam": imam}
                        )
                else:
                    Assignment.objects.filter(week_request=wr).delete()
            except (WeekRequest.DoesNotExist, Imam.DoesNotExist):
                pass
            return redirect(f"{reverse('admin_panel')}?week={friday.isoformat()}#schedule")

        elif action == "add_video":
            video_form = TrainingVideoForm(request.POST)
            if video_form.is_valid():
                video_form.save()
                return redirect(f"{reverse('admin_panel')}?week={friday.isoformat()}#training")

        elif action == "delete_video":
            TrainingVideo.objects.filter(pk=request.POST.get("video_pk")).delete()
            return redirect(f"{reverse('admin_panel')}?week={friday.isoformat()}#training")

        elif action == "add_question":
            q_text = request.POST.get("question_text", "").strip()
            choices = [request.POST.get(f"choice_{c}", "").strip() for c in ("a", "b", "c", "d")]
            correct = request.POST.get("correct_choice", "")
            if q_text and all(choices) and correct in ("a", "b", "c", "d"):
                q = QuizQuestion.objects.create(text=q_text)
                for letter, text in zip(("a", "b", "c", "d"), choices):
                    QuizChoice.objects.create(question=q, text=text, is_correct=(letter == correct))
            return redirect(f"{reverse('admin_panel')}?week={friday.isoformat()}#quiz")

        elif action == "delete_question":
            QuizQuestion.objects.filter(pk=request.POST.get("question_pk")).delete()
            return redirect(f"{reverse('admin_panel')}?week={friday.isoformat()}#quiz")

    # ── Schedule data ──
    week_requests = (
        WeekRequest.objects
        .filter(jumuah_date=friday)
        .select_related("mosque", "mosque__preferred_imam", "assignment__imam")
        .order_by("-mosque__requires_imam", "-mosque__attendees")
    )
    assigned_imam_ids = set(
        Assignment.objects.filter(week_request__jumuah_date=friday).values_list("imam_id", flat=True)
    )
    unavailable_ids = set(
        ImamUnavailability.objects.filter(jumuah_date=friday).values_list("imam_id", flat=True)
    )
    trained_ids = _trained_imam_ids()
    all_imams = list(Imam.objects.all())

    request_rows = []
    for wr in week_requests:
        preferred_id = wr.mosque.preferred_imam_id
        current_imam_id = wr.assignment.imam_id if wr.is_assigned else None
        # Preferred imam always first in list
        sorted_imams = sorted(all_imams, key=lambda i: (0 if i.pk == preferred_id else 1, i.name.lower()))
        imam_options = [
            {
                "imam": imam,
                "preferred": imam.pk == preferred_id,
                "untrained": trained_ids is not None and imam.pk not in trained_ids,
                "busy": imam.pk in assigned_imam_ids and imam.pk != current_imam_id,
                "unavailable": imam.pk in unavailable_ids and imam.pk != current_imam_id,
            }
            for imam in sorted_imams
        ]
        request_rows.append({"wr": wr, "current_imam_id": current_imam_id, "imam_options": imam_options})

    total = len(request_rows)
    total_assigned = sum(1 for r in request_rows if r["current_imam_id"])

    # ── Mosque / imam lists ──
    mosques = Mosque.objects.select_related("preferred_imam").order_by("-requires_imam", "-attendees")
    imams = Imam.objects.annotate(
        quiz_passed=Exists(QuizAttempt.objects.filter(imam=OuterRef("pk"), passed=True))
    ).order_by("name")
    videos = TrainingVideo.objects.all()
    questions = QuizQuestion.objects.prefetch_related("choices").all()
    has_quiz = QuizQuestion.objects.exists()
    reviews = ImamReview.objects.select_related(
        "assignment__week_request__mosque", "assignment__imam"
    ).order_by("-created_at")

    return render(request, "scheduler/admin_panel.html", {
        # schedule
        "friday": friday,
        "prev_friday": friday - timedelta(days=7),
        "next_friday": friday + timedelta(days=7),
        "request_rows": request_rows,
        "total_mosques": total,
        "total_assigned": total_assigned,
        "total_unassigned": total - total_assigned,
        # lists
        "mosques": mosques,
        "imams": imams,
        "has_quiz": has_quiz,
        # training
        "videos": videos,
        "video_form": video_form,
        # quiz
        "questions": questions,
        # reviews
        "reviews": reviews,
    })
