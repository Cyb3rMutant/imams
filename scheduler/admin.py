from django.contrib import admin

from .models import (Assignment, Imam, ImamReview, ImamUnavailability, Mosque,
                     QuizAttempt, QuizChoice, QuizQuestion,
                     TrainingProgress, TrainingVideo, WeekRequest)


@admin.register(Mosque)
class MosqueAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "attendees", "requires_imam", "preferred_imam", "phone"]
    search_fields = ["name", "address", "phone"]


@admin.register(Imam)
class ImamAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "is_trained", "phone"]
    search_fields = ["name", "address", "phone"]


@admin.register(TrainingVideo)
class TrainingVideoAdmin(admin.ModelAdmin):
    list_display = ["__str__", "order", "title", "url"]
    list_editable = ["order", "title"]


@admin.register(TrainingProgress)
class TrainingProgressAdmin(admin.ModelAdmin):
    list_display = ["imam", "video", "completed_at"]
    list_filter = ["video"]


@admin.register(ImamUnavailability)
class ImamUnavailabilityAdmin(admin.ModelAdmin):
    list_display = ["imam", "jumuah_date"]
    list_filter = ["jumuah_date"]


@admin.register(WeekRequest)
class WeekRequestAdmin(admin.ModelAdmin):
    list_display = ["jumuah_date", "mosque", "is_assigned"]
    list_filter = ["jumuah_date"]
    ordering = ["-jumuah_date"]


@admin.register(ImamReview)
class ImamReviewAdmin(admin.ModelAdmin):
    list_display = ["get_date", "get_mosque", "get_imam", "rating", "comment", "created_at"]
    list_filter = ["rating"]
    ordering = ["-created_at"]

    @admin.display(description="Date")
    def get_date(self, obj):
        return obj.assignment.week_request.jumuah_date

    @admin.display(description="Mosque")
    def get_mosque(self, obj):
        return obj.assignment.week_request.mosque

    @admin.display(description="Imam")
    def get_imam(self, obj):
        return obj.assignment.imam


class QuizChoiceInline(admin.TabularInline):
    model = QuizChoice
    extra = 4


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ["__str__", "order"]
    list_editable = ["order"]
    inlines = [QuizChoiceInline]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ["imam", "passed", "score", "total", "taken_at"]
    list_filter = ["passed"]


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ["get_date", "get_mosque", "imam"]
    ordering = ["-week_request__jumuah_date"]

    @admin.display(description="Date")
    def get_date(self, obj):
        return obj.week_request.jumuah_date

    @admin.display(description="Mosque")
    def get_mosque(self, obj):
        return obj.week_request.mosque
