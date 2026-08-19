from django.contrib.auth.models import AbstractUser
from django.db import models
from decimal import Decimal


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        MECHANIC = "mechanic", "Mechanic"
        ADMIN = "admin", "Shop Admin"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CUSTOMER)
    phone_number = models.CharField(max_length=20, blank=True)

    def has_role(self, role):
        return self.role == role


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer_profile")
    address = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    def get_vehicles(self):
        return self.vehicles.all()

    def get_appointment_history(self):
        return self.appointments.order_by("-scheduled_date", "-scheduled_time")

    def get_unpaid_invoices(self):
        return Invoice.objects.filter(appointment__customer=self, is_paid=False)


class MechanicProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="mechanic_profile")
    specialty = models.CharField(max_length=100, blank=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    def get_assigned_appointments(self):
        return self.appointments.exclude(status=Appointment.Status.CANCELLED)


class Vehicle(models.Model):
    owner = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name="vehicles")
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveIntegerField()
    plate_number = models.CharField(max_length=20)
    vin = models.CharField(max_length=32, blank=True)

    def __str__(self):
        return f"{self.year} {self.make} {self.model} ({self.plate_number})"


class ServiceType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    estimated_duration = models.PositiveIntegerField(help_text="Minutes")
    base_price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return self.name


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name="appointments")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="appointments")
    mechanic = models.ForeignKey(MechanicProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="appointments")
    service = models.ForeignKey(ServiceType, on_delete=models.PROTECT, related_name="appointments")
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_date", "scheduled_time"]

    def __str__(self):
        return f"{self.vehicle} - {self.service} on {self.scheduled_date} {self.scheduled_time}"

    @classmethod
    def is_conflicting(cls, mechanic, scheduled_date, scheduled_time, exclude_id=None):
        qs = cls.objects.filter(
            mechanic=mechanic,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
        ).exclude(status=cls.Status.CANCELLED)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        return qs.exists()

    def mark_completed(self):
        self.status = self.Status.COMPLETED
        self.save()
        invoice, created = Invoice.objects.get_or_create(
            appointment=self,
            defaults={"total_amount": self.service.base_price},
        )
        invoice.calculate_total()

    def cancel(self):
        self.status = self.Status.CANCELLED
        self.save()


class DiagnosisLog(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name="diagnosis_log")
    diagnosis_notes = models.TextField(blank=True)
    parts_used = models.TextField(blank=True)
    labor_hours = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return f"Diagnosis for {self.appointment}"


class Invoice(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name="invoice")
    total_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    is_paid = models.BooleanField(default=False)
    issued_at = models.DateTimeField(auto_now_add=True)

    def calculate_total(self):
        base = self.appointment.service.base_price
        if hasattr(self.appointment, "diagnosis_log"):
            labor_rate = Decimal("45.00")
            base += self.appointment.diagnosis_log.labor_hours * labor_rate
        self.total_amount = base
        self.save()
        return self.total_amount

    def get_labor_cost(self):
        if hasattr(self.appointment, "diagnosis_log"):
            return self.appointment.diagnosis_log.labor_hours * Decimal("45.00")
        return Decimal("0.00")

    def mark_paid(self):
        self.is_paid = True
        self.save()

    def __str__(self):
        return f"Invoice #{self.id} - {self.appointment}"


class Notification(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    message = models.CharField(max_length=255)
    sent_at = models.DateTimeField(auto_now_add=True)
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.EMAIL)

    def send(self):
        # Placeholder for real email/SMS integration (e.g. Django email backend, Twilio)
        print(f"[{self.channel.upper()}] to {self.user}: {self.message}")

    def __str__(self):
        return f"Notification to {self.user} ({self.channel})"
