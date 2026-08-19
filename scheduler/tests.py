from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, time
from decimal import Decimal
from scheduler.models import (
    User, CustomerProfile, MechanicProfile, Vehicle,
    ServiceType, Appointment, DiagnosisLog, Invoice, Notification
)


class AutoFixSchedulerTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # 1. Admin
        self.admin = User.objects.create_superuser("admin", "admin@test.com", "adminpass")
        self.admin.role = User.Role.ADMIN
        self.admin.save()

        # 2. Mechanic
        self.mech_user = User.objects.create_user("mechanic1", "mech@test.com", "mechpass")
        self.mech_user.role = User.Role.MECHANIC
        self.mech_user.save()
        self.mechanic = MechanicProfile.objects.create(user=self.mech_user, specialty="Brakes & Transmission")

        # 3. Customer
        self.cust_user = User.objects.create_user("customer1", "cust@test.com", "custpass")
        self.cust_user.role = User.Role.CUSTOMER
        self.cust_user.save()
        self.customer = CustomerProfile.objects.create(user=self.cust_user, address="123 Main St")

        # 4. Vehicle
        self.vehicle = Vehicle.objects.create(
            owner=self.customer,
            make="Toyota",
            model="Corolla",
            year=2020,
            plate_number="TEST-123"
        )

        # 5. Service
        self.service = ServiceType.objects.create(
            name="Oil & Filter Change",
            description="Synthetic oil change",
            estimated_duration=30,
            base_price=Decimal("49.99")
        )

    def test_home_page_loads(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Oil &amp; Filter Change")

    def test_customer_booking_workflow(self):
        self.client.login(username="customer1", password="custpass")
        response = self.client.post(reverse("book_appointment"), {
            "vehicle": self.vehicle.pk,
            "service": self.service.pk,
            "scheduled_date": str(date.today()),
            "scheduled_time": "10:00",
            "notes": "Engine noise",
        })
        self.assertEqual(response.status_code, 302)
        
        appointment = Appointment.objects.get(vehicle=self.vehicle)
        self.assertEqual(appointment.status, Appointment.Status.PENDING)
        self.assertEqual(Notification.objects.filter(user=self.cust_user).count(), 1)

    def test_admin_assignment_workflow(self):
        appointment = Appointment.objects.create(
            customer=self.customer,
            vehicle=self.vehicle,
            service=self.service,
            scheduled_date=date.today(),
            scheduled_time=time(10, 0),
            status=Appointment.Status.PENDING
        )
        
        self.client.login(username="admin", password="adminpass")
        response = self.client.post(reverse("assign_mechanic", kwargs={"pk": appointment.pk}), {
            "mechanic": self.mechanic.pk,
            "status": Appointment.Status.CONFIRMED,
        })
        self.assertEqual(response.status_code, 302)
        
        appointment.refresh_from_db()
        self.assertEqual(appointment.mechanic, self.mechanic)
        self.assertEqual(appointment.status, Appointment.Status.CONFIRMED)

    def test_mechanic_diagnosis_and_completion_workflow(self):
        appointment = Appointment.objects.create(
            customer=self.customer,
            vehicle=self.vehicle,
            mechanic=self.mechanic,
            service=self.service,
            scheduled_date=date.today(),
            scheduled_time=time(10, 0),
            status=Appointment.Status.CONFIRMED
        )

        self.client.login(username="mechanic1", password="mechpass")
        
        # Log diagnosis
        response = self.client.post(reverse("log_diagnosis", kwargs={"pk": appointment.pk}), {
            "diagnosis_notes": "Worn oil filter replaced.",
            "parts_used": "Filter #405 ($15.00)",
            "labor_hours": "1.00",
        })
        self.assertEqual(response.status_code, 302)

        # Mark completed
        response = self.client.post(reverse("update_job_status", kwargs={"pk": appointment.pk}), {
            "status": Appointment.Status.COMPLETED,
        })
        self.assertEqual(response.status_code, 302)

        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.COMPLETED)
        
        # Check invoice
        invoice = Invoice.objects.get(appointment=appointment)
        # Expected total: 49.99 + 1.0 * 45.00 = 94.99
        self.assertEqual(invoice.total_amount, Decimal("94.99"))
        self.assertFalse(invoice.is_paid)

    def test_customer_invoice_payment(self):
        appointment = Appointment.objects.create(
            customer=self.customer,
            vehicle=self.vehicle,
            mechanic=self.mechanic,
            service=self.service,
            scheduled_date=date.today(),
            scheduled_time=time(10, 0),
            status=Appointment.Status.COMPLETED
        )
        invoice = Invoice.objects.create(appointment=appointment, total_amount=Decimal("49.99"))

        self.client.login(username="customer1", password="custpass")
        response = self.client.post(reverse("pay_invoice", kwargs={"pk": invoice.pk}))
        self.assertEqual(response.status_code, 302)

        invoice.refresh_from_db()
        self.assertTrue(invoice.is_paid)
