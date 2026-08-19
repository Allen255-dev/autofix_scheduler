from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Vehicle, Appointment, ServiceType, DiagnosisLog


class CustomerSignUpForm(UserCreationForm):
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"placeholder": "First name"}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"placeholder": "Last name"}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"placeholder": "your@email.com"}))
    phone_number = forms.CharField(required=False, widget=forms.TextInput(attrs={"placeholder": "+1 (555) 000-0000"}))

    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "email", "phone_number", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs["placeholder"] = "Choose a username"
        self.fields["password1"].widget.attrs["placeholder"] = "Create a password"
        self.fields["password2"].widget.attrs["placeholder"] = "Confirm password"

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.CUSTOMER
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.email = self.cleaned_data["email"]
        user.phone_number = self.cleaned_data.get("phone_number", "")
        if commit:
            user.save()
        return user


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ["make", "model", "year", "plate_number", "vin"]
        widgets = {
            "make": forms.TextInput(attrs={"placeholder": "e.g. Toyota"}),
            "model": forms.TextInput(attrs={"placeholder": "e.g. Camry"}),
            "year": forms.NumberInput(attrs={"placeholder": "e.g. 2020"}),
            "plate_number": forms.TextInput(attrs={"placeholder": "e.g. ABC-1234"}),
            "vin": forms.TextInput(attrs={"placeholder": "17-char VIN (optional)"}),
        }


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["vehicle", "service", "scheduled_date", "scheduled_time", "notes"]
        widgets = {
            "scheduled_date": forms.DateInput(attrs={"type": "date"}),
            "scheduled_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, customer=None, **kwargs):
        super().__init__(*args, **kwargs)
        if customer is not None:
            self.fields["vehicle"].queryset = Vehicle.objects.filter(owner=customer)

    def clean(self):
        cleaned = super().clean()
        date = cleaned.get("scheduled_date")
        time = cleaned.get("scheduled_time")
        # Availability is re-checked against assigned mechanic once admin assigns one;
        # at booking time we only guard against exact duplicate slots shop-wide.
        if date and time:
            clashing = Appointment.objects.filter(
                scheduled_date=date, scheduled_time=time
            ).exclude(status=Appointment.Status.CANCELLED)
            if self.instance.pk:
                clashing = clashing.exclude(pk=self.instance.pk)
            if clashing.count() >= 3:  # e.g. shop has 3 bays
                raise forms.ValidationError("That time slot is fully booked. Please choose another.")
        return cleaned


class DiagnosisLogForm(forms.ModelForm):
    class Meta:
        model = DiagnosisLog
        fields = ["diagnosis_notes", "parts_used", "labor_hours"]


class AssignMechanicForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["mechanic", "status"]


class ServiceTypeForm(forms.ModelForm):
    class Meta:
        model = ServiceType
        fields = ["name", "description", "estimated_duration", "base_price"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Full Engine Tune-Up"}),
            "description": forms.Textarea(attrs={"placeholder": "Describe what this service includes...", "rows": 3}),
            "estimated_duration": forms.NumberInput(attrs={"placeholder": "Minutes"}),
            "base_price": forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01"}),
        }

