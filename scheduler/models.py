import re

from django.db import models


class Mosque(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    attendees = models.PositiveIntegerField(default=0)
    requires_imam = models.BooleanField(default=True)
    preferred_imam = models.ForeignKey(
        "Imam",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_by_mosques",
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Imam(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)

    @property
    def is_trained(self):
        if not QuizQuestion.objects.exists():
            return True
        try:
            return self.quiz_attempt.passed
        except QuizAttempt.DoesNotExist:
            return False

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class TrainingVideo(models.Model):
    title = models.CharField(max_length=200)
    url = models.URLField()
    order = models.PositiveSmallIntegerField(default=0)

    def youtube_id(self):
        match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", self.url)
        return match.group(1) if match else None

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["order", "pk"]


class TrainingProgress(models.Model):
    imam = models.ForeignKey(Imam, on_delete=models.CASCADE, related_name="training_progress")
    video = models.ForeignKey(TrainingVideo, on_delete=models.CASCADE, related_name="completions")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["imam", "video"]]


class ImamUnavailability(models.Model):
    imam = models.ForeignKey(Imam, on_delete=models.CASCADE, related_name="unavailabilities")
    jumuah_date = models.DateField()

    class Meta:
        unique_together = [["imam", "jumuah_date"]]
        ordering = ["jumuah_date"]


class WeekRequest(models.Model):
    mosque = models.ForeignKey(Mosque, on_delete=models.CASCADE, related_name="week_requests")
    jumuah_date = models.DateField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_assigned(self):
        return hasattr(self, "assignment")

    def __str__(self):
        return f"{self.mosque} — {self.jumuah_date}"

    class Meta:
        unique_together = [["mosque", "jumuah_date"]]
        ordering = ["jumuah_date"]


class Assignment(models.Model):
    week_request = models.OneToOneField(
        WeekRequest, on_delete=models.CASCADE, related_name="assignment"
    )
    imam = models.ForeignKey(Imam, on_delete=models.CASCADE, related_name="assignments")

    def __str__(self):
        return f"{self.week_request.jumuah_date} — {self.week_request.mosque} → {self.imam}"

    class Meta:
        ordering = ["week_request__jumuah_date"]


class QuizQuestion(models.Model):
    text = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return self.text[:80]

    class Meta:
        ordering = ["order", "pk"]


class QuizChoice(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text[:60]

    class Meta:
        ordering = ["pk"]


class QuizAttempt(models.Model):
    imam = models.OneToOneField(Imam, on_delete=models.CASCADE, related_name="quiz_attempt")
    passed = models.BooleanField(default=False)
    score = models.PositiveSmallIntegerField(default=0)
    total = models.PositiveSmallIntegerField(default=0)
    taken_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.imam} — {'passed' if self.passed else 'failed'} ({self.score}/{self.total})"
