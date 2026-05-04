from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Avg, F
from django.db.models.functions import TruncDate

from scheduler.models import (Assignment, Imam, ImamUnavailability,
                              QuizAttempt, QuizQuestion, WeekRequest)
from scheduler.utils import within_miles


class Command(BaseCommand):
    help = "Auto-assign trained, nearby imams to unassigned requests for the upcoming Friday."

    def handle(self, *args, **options):
        today = date.today()
        friday = today + timedelta(days=(4 - today.weekday()) % 7)
        self.stdout.write(f"Auto-assigning for {friday}")

        assigned_request_ids = set(
            Assignment.objects.filter(week_request__jumuah_date=friday).values_list(
                "week_request_id", flat=True
            )
        )
        # Mosques: requires_imam first, then by request date (date only, not time),
        # then largest congregation first within the same day.
        requests = list(
            WeekRequest.objects.filter(jumuah_date=friday)
            .exclude(pk__in=assigned_request_ids)
            .select_related("mosque")
            .order_by(
                "-mosque__requires_imam",
                TruncDate("submitted_at"),
                "-mosque__attendees",
            )
        )

        if not requests:
            self.stdout.write("No unassigned requests.")
            return

        unavailable_ids = set(
            ImamUnavailability.objects.filter(jumuah_date=friday).values_list(
                "imam_id", flat=True
            )
        )
        already_assigned_ids = set(
            Assignment.objects.filter(week_request__jumuah_date=friday).values_list(
                "imam_id", flat=True
            )
        )
        has_quiz = QuizQuestion.objects.exists()
        trained_ids = (
            set(
                QuizAttempt.objects.filter(passed=True).values_list(
                    "imam_id", flat=True
                )
            )
            if has_quiz
            else None
        )

        # Imams: best average review rating first; unreviewed imams go last.
        all_imams = list(
            Imam.objects.annotate(avg_rating=Avg("assignments__review__rating"))
            .exclude(pk__in=unavailable_ids)
            .exclude(pk__in=already_assigned_ids)
            .order_by(F("avg_rating").desc(nulls_last=True), "name")
        )
        if trained_ids is not None:
            all_imams = [i for i in all_imams if i.pk in trained_ids]

        coord_cache: dict = {}
        assigned_count = 0

        with transaction.atomic():
            for wr in requests:
                mosque_postcode = wr.mosque.address
                max_miles = 20 if wr.mosque.provides_transport else 7
                pool = [
                    i
                    for i in all_imams
                    if within_miles(
                        i.address,
                        mosque_postcode,
                        max_miles=max_miles,
                        cache=coord_cache,
                    )
                ]
                if not pool:
                    self.stdout.write(
                        f"  {wr.mosque.name}: no imam available within 7 miles"
                    )
                    continue

                preferred_id = wr.mosque.preferred_imam_id
                imam = next((i for i in pool if i.pk == preferred_id), pool[0])
                Assignment.objects.create(week_request=wr, imam=imam)
                all_imams = [i for i in all_imams if i.pk != imam.pk]
                assigned_count += 1
                self.stdout.write(f"  {wr.mosque.name} -> {imam.name}")

        self.stdout.write(f"Done: {assigned_count}/{len(requests)} assigned.")
