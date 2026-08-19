from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum

from .models import (
    User, CustomerProfile, MechanicProfile, Vehicle,
    ServiceType, Appointment, Notification, Invoice, DiagnosisLog
)
from .forms import (
    CustomerSignUpForm, VehicleForm, AppointmentForm,
    AssignMechanicForm, DiagnosisLogForm, ServiceTypeForm
)


def is_admin(user):
    return user.is_authenticated and user.role == User.Role.ADMIN


def is_mechanic(user):
    return user.is_authenticated and user.role == User.Role.MECHANIC


def home(request):
    services = ServiceType.objects.all()
    return render(request, "scheduler/home.html", {"services": services})


def signup(request):
    if request.method == "POST":
        form = CustomerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            CustomerProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, "Welcome to AutoFix Repair Shop!")
            return redirect("dashboard")
    else:
        form = CustomerSignUpForm()
    return render(request, "scheduler/signup.html", {"form": form})


@login_required
def dashboard(request):
    user = request.user
    if user.role == User.Role.CUSTOMER:
        profile = get_object_or_404(CustomerProfile, user=user)
        appointments = profile.get_appointment_history()
        vehicles = profile.get_vehicles()
        invoices = Invoice.objects.filter(appointment__customer=profile).order_by("-issued_at")
        notifications = Notification.objects.filter(user=user).order_by("-sent_at")[:5]
        return render(request, "scheduler/customer_dashboard.html", {
            "appointments": appointments,
            "vehicles": vehicles,
            "invoices": invoices,
            "notifications": notifications,
        })

    if user.role == User.Role.MECHANIC:
        profile = get_object_or_404(MechanicProfile, user=user)
        appointments = profile.get_assigned_appointments()
        completed_jobs = profile.appointments.filter(status=Appointment.Status.COMPLETED).count()
        return render(request, "scheduler/mechanic_dashboard.html", {
            "appointments": appointments,
            "completed_jobs_count": completed_jobs,
            "profile": profile,
        })

    if user.role == User.Role.ADMIN:
        pending = Appointment.objects.filter(status=Appointment.Status.PENDING)
        upcoming = Appointment.objects.exclude(status__in=[Appointment.Status.CANCELLED, Appointment.Status.COMPLETED])
        completed = Appointment.objects.filter(status=Appointment.Status.COMPLETED)
        services = ServiceType.objects.all()
        mechanics = MechanicProfile.objects.all()
        total_revenue = Invoice.objects.filter(is_paid=True).aggregate(Sum("total_amount"))["total_amount__sum"] or 0
        pending_revenue = Invoice.objects.filter(is_paid=False).aggregate(Sum("total_amount"))["total_amount__sum"] or 0

        return render(request, "scheduler/admin_dashboard.html", {
            "pending": pending,
            "upcoming": upcoming,
            "completed_count": completed.count(),
            "services": services,
            "mechanics": mechanics,
            "total_revenue": total_revenue,
            "pending_revenue": pending_revenue,
        })

    return redirect("home")


@login_required
def add_vehicle(request):
    profile = get_object_or_404(CustomerProfile, user=request.user)
    if request.method == "POST":
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.owner = profile
            vehicle.save()
            messages.success(request, f"Vehicle '{vehicle.make} {vehicle.model}' added successfully.")
            return redirect("dashboard")
    else:
        form = VehicleForm()
    return render(request, "scheduler/add_vehicle.html", {"form": form})


@login_required
def delete_vehicle(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, owner__user=request.user)
    if request.method == "POST":
        vehicle.delete()
        messages.info(request, "Vehicle removed.")
    return redirect("dashboard")


@login_required
def book_appointment(request):
    profile = get_object_or_404(CustomerProfile, user=request.user)
    if request.method == "POST":
        form = AppointmentForm(request.POST, customer=profile)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.customer = profile
            appointment.status = Appointment.Status.PENDING
            appointment.save()
            Notification.objects.create(
                user=request.user,
                appointment=appointment,
                message=f"Booking confirmed for {appointment.service.name} on {appointment.scheduled_date} at {appointment.scheduled_time}.",
            ).send()
            messages.success(request, "Appointment booked! You will receive confirmation when assigned to a technician.")
            return redirect("dashboard")
    else:
        form = AppointmentForm(customer=profile)
    return render(request, "scheduler/book_appointment.html", {"form": form})


@login_required
def cancel_appointment(request, pk):
    if request.user.role == User.Role.CUSTOMER:
        appointment = get_object_or_404(Appointment, pk=pk, customer__user=request.user)
    else:
        appointment = get_object_or_404(Appointment, pk=pk)
    
    appointment.cancel()
    Notification.objects.create(
        user=appointment.customer.user,
        appointment=appointment,
        message=f"Appointment for {appointment.service.name} on {appointment.scheduled_date} was cancelled.",
    ).send()
    messages.info(request, "Appointment cancelled.")
    return redirect("dashboard")


@login_required
@user_passes_test(is_mechanic)
def update_job_status(request, pk):
    profile = get_object_or_404(MechanicProfile, user=request.user)
    appointment = get_object_or_404(Appointment, pk=pk, mechanic=profile)
    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status == Appointment.Status.COMPLETED:
            appointment.mark_completed()
            Notification.objects.create(
                user=appointment.customer.user,
                appointment=appointment,
                message=f"Your vehicle repair for {appointment.service.name} is completed! Invoice is ready.",
            ).send()
            messages.success(request, "Job marked as completed. Invoice generated for customer.")
        else:
            appointment.status = new_status
            appointment.save()
            Notification.objects.create(
                user=appointment.customer.user,
                appointment=appointment,
                message=f"Job status updated to '{appointment.get_status_display()}' for {appointment.service.name}.",
            ).send()
            messages.success(request, f"Job status updated to {appointment.get_status_display()}.")
    return redirect("dashboard")


@login_required
@user_passes_test(is_mechanic)
def log_diagnosis(request, pk):
    profile = get_object_or_404(MechanicProfile, user=request.user)
    appointment = get_object_or_404(Appointment, pk=pk, mechanic=profile)
    diagnosis_log = getattr(appointment, "diagnosis_log", None)
    if request.method == "POST":
        form = DiagnosisLogForm(request.POST, instance=diagnosis_log)
        if form.is_valid():
            log = form.save(commit=False)
            log.appointment = appointment
            log.save()
            if hasattr(appointment, "invoice"):
                appointment.invoice.calculate_total()
            messages.success(request, "Diagnostic report saved successfully.")
            return redirect("dashboard")
    else:
        form = DiagnosisLogForm(instance=diagnosis_log)
    return render(request, "scheduler/log_diagnosis.html", {"form": form, "appointment": appointment})


@login_required
@user_passes_test(is_admin)
def assign_mechanic(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.method == "POST":
        form = AssignMechanicForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            if appointment.mechanic:
                Notification.objects.create(
                    user=appointment.mechanic.user,
                    appointment=appointment,
                    message=f"New repair job assigned: {appointment.vehicle} - {appointment.service.name}",
                ).send()
                Notification.objects.create(
                    user=appointment.customer.user,
                    appointment=appointment,
                    message=f"Technician {appointment.mechanic} has been assigned to your repair job.",
                ).send()
            messages.success(request, "Technician assigned successfully.")
            return redirect("dashboard")
    else:
        form = AssignMechanicForm(instance=appointment)
    return render(request, "scheduler/assign_mechanic.html", {"form": form, "appointment": appointment})


@login_required
def invoice_detail(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    # Ensure authorization: Customer owns appointment or user is staff/mechanic
    if request.user.role == User.Role.CUSTOMER and appointment.customer.user != request.user:
        messages.error(request, "Unauthorized access to invoice.")
        return redirect("dashboard")

    invoice, created = Invoice.objects.get_or_create(
        appointment=appointment,
        defaults={"total_amount": appointment.service.base_price}
    )
    invoice.calculate_total()

    return render(request, "scheduler/invoice_detail.html", {
        "appointment": appointment,
        "invoice": invoice,
    })


@login_required
def pay_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.user.role == User.Role.CUSTOMER and invoice.appointment.customer.user != request.user:
        messages.error(request, "Unauthorized action.")
        return redirect("dashboard")

    if request.method == "POST":
        invoice.mark_paid()
        messages.success(request, f"Payment of ${invoice.total_amount} processed successfully! Receipt issued.")
        return redirect("invoice_detail", pk=invoice.appointment.pk)
    return redirect("dashboard")


@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by("-sent_at")
    return render(request, "scheduler/notifications.html", {"notifications": notifications})


@login_required
@user_passes_test(is_admin)
def add_service(request):
    if request.method == "POST":
        form = ServiceTypeForm(request.POST)
        if form.is_valid():
            service = form.save()
            messages.success(request, f"Service '{service.name}' added to service menu.")
            return redirect("dashboard")
    else:
        form = ServiceTypeForm()
    return render(request, "scheduler/add_service.html", {"form": form})


@login_required
@user_passes_test(is_admin)
def edit_service(request, pk):
    service = get_object_or_404(ServiceType, pk=pk)
    if request.method == "POST":
        form = ServiceTypeForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, f"Service '{service.name}' updated.")
            return redirect("dashboard")
    else:
        form = ServiceTypeForm(instance=service)
    return render(request, "scheduler/edit_service.html", {"form": form, "service": service})
