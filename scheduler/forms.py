from django import forms

from .models import Imam, Mosque, TrainingVideo


class MosqueForm(forms.ModelForm):
    class Meta:
        model = Mosque
        fields = ["name", "address", "phone"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}
        labels = {"name": "Mosque Name", "phone": "Contact Number"}


class MosqueSettingsForm(forms.ModelForm):
    class Meta:
        model = Mosque
        fields = ["attendees", "requires_imam", "provides_transport"]
        labels = {
            "attendees": "Expected Attendees",
            "requires_imam": "Jumuah cannot run without an imam",
            "provides_transport": "We can provide transport for the imam",
        }


class ImamForm(forms.ModelForm):
    class Meta:
        model = Imam
        fields = ["name", "address", "phone"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}
        labels = {"name": "Full Name", "phone": "Contact Number"}


class TrainingVideoForm(forms.ModelForm):
    class Meta:
        model = TrainingVideo
        fields = ["title", "url", "order"]
        labels = {
            "url": "YouTube URL",
            "order": "Order (lower = first)",
        }
