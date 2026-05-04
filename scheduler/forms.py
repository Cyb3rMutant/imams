from django import forms

from .models import Imam, Mosque, TrainingVideo
from .utils import get_postcode_coords


def _validate_postcode(value: str) -> str:
    if get_postcode_coords(value) is None:
        raise forms.ValidationError("Please enter a valid UK postcode.")
    return value.strip().upper()


class MosqueForm(forms.ModelForm):
    class Meta:
        model = Mosque
        fields = ["name", "address", "phone"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}
        labels = {"name": "Mosque Name", "phone": "Contact Number"}

    def clean_address(self):
        return _validate_postcode(self.cleaned_data["address"])


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

    def clean_address(self):
        return _validate_postcode(self.cleaned_data["address"])


class TrainingVideoForm(forms.ModelForm):
    class Meta:
        model = TrainingVideo
        fields = ["title", "url", "order"]
        labels = {
            "url": "YouTube URL",
            "order": "Order (lower = first)",
        }
