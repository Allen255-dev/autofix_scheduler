from django.core.management.base import BaseCommand
from datetime import date, time
from decimal import Decimal
from scheduler.models import (
    User, CustomerProfile, MechanicProfile, Vehicle,
    ServiceType, Appointment, DiagnosisLog, Invoice, Notification
)


class Command(BaseCommand):
    help = "Seed the database with rich demo data for AutoFix Mechanic Repair Shop."

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding AutoFix Repair Shop database...")

        # 1. Services
        services_data = [
            ("Oil & Filter Service", "Full synthetic engine oil change, filter replacement, and multi-point safety check.", 30, Decimal("49.99")),
            ("Brake Inspection & Replacement", "Brake pad replacement, rotor resurfacing/inspection, and brake fluid top-up.", 90, Decimal("149.99")),
            ("Full Engine Diagnostics", "Computerized OBD-II diagnostic scan, sensor test, and technician report.", 45, Decimal("89.99")),
            ("Transmission Flush & Service", "Complete transmission fluid flush, filter replacement, and system leak check.", 120, Decimal("219.99")),
            ("A/C System Recharge & Repair", "Refrigerant leak detection, system evac & recharge, and compressor test.", 60, Decimal("129.99")),
            ("Wheel Alignment & Tire Balance", "4-wheel precision laser alignment and dynamic tire balancing.", 45, Decimal("79.99")),
        ]
        
        services = {}
        for name, desc, dur, price in services_data:
            s, _ = ServiceType.objects.get_or_create(
                name=name,
                defaults={"description": desc, "estimated_duration": dur, "base_price": price}
            )
            services[name] = s
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(services_data)} repair services."))

        # 2. Admin User
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@autofixshop.com",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
            }
        )
        if created:
            admin_user.set_password("admin123")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created Admin: admin / admin123"))

        # 3. Mechanics
        mechanics_info = [
            ("mike_mech", "Mike Miller", "mike@autofixshop.com", "Transmission & Engine Specialist", "555-0101"),
            ("sarah_tech", "Sarah Jenkins", "sarah@autofixshop.com", "Brake & Electrical Master Tech", "555-0102"),
        ]

        mech_profiles = {}
        for uname, fullname, email, spec, phone in mechanics_info:
            first, last = fullname.split(" ", 1)
            u, c = User.objects.get_or_create(
                username=uname,
                defaults={
                    "email": email,
                    "first_name": first,
                    "last_name": last,
                    "role": User.Role.MECHANIC,
                    "phone_number": phone,
                }
            )
            if c:
                u.set_password("pass1234")
                u.save()
            mp, _ = MechanicProfile.objects.get_or_create(
                user=u,
                defaults={"specialty": spec, "is_available": True}
            )
            mech_profiles[uname] = mp
        self.stdout.write(self.style.SUCCESS("Created Mechanic profiles."))

        # 4. Customers & Vehicles
        # Customer 1: John Doe
        john_user, c = User.objects.get_or_create(
            username="john_doe",
            defaults={
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "role": User.Role.CUSTOMER,
                "phone_number": "555-0199",
            }
        )
        if c:
            john_user.set_password("pass1234")
            john_user.save()
        john_profile, _ = CustomerProfile.objects.get_or_create(user=john_user, defaults={"address": "742 Evergreen Terrace"})

        camry, _ = Vehicle.objects.get_or_create(
            owner=john_profile,
            plate_number="ABC-1234",
            defaults={"make": "Toyota", "model": "Camry SE", "year": 2021, "vin": "4T1B11HK5MU123456"}
        )

        f150, _ = Vehicle.objects.get_or_create(
            owner=john_profile,
            plate_number="XYZ-9876",
            defaults={"make": "Ford", "model": "F-150 XLT", "year": 2018, "vin": "1FTFW1E84JFB98765"}
        )

        # Customer 2: Alice Smith
        alice_user, c = User.objects.get_or_create(
            username="alice_smith",
            defaults={
                "email": "alice.smith@example.com",
                "first_name": "Alice",
                "last_name": "Smith",
                "role": User.Role.CUSTOMER,
                "phone_number": "555-0188",
            }
        )
        if c:
            alice_user.set_password("pass1234")
            alice_user.save()
        alice_profile, _ = CustomerProfile.objects.get_or_create(user=alice_user, defaults={"address": "1204 Pine Street"})

        civic, _ = Vehicle.objects.get_or_create(
            owner=alice_profile,
            plate_number="HND-4567",
            defaults={"make": "Honda", "model": "Civic Touring", "year": 2022, "vin": "1HGCR2F83HA456789"}
        )
        self.stdout.write(self.style.SUCCESS("Created Customer profiles and vehicles."))

        # 5. Appointments & Invoices
        today = date.today()

        # Job 1: Completed Brake Service for John's Camry
        app1, created = Appointment.objects.get_or_create(
            customer=john_profile,
            vehicle=camry,
            service=services["Brake Inspection & Replacement"],
            scheduled_date=today,
            scheduled_time=time(9, 0),
            defaults={
                "mechanic": mech_profiles["sarah_tech"],
                "status": Appointment.Status.COMPLETED,
                "notes": "Customer noticed squeaking noise when stopping."
            }
        )
        if created:
            diag1 = DiagnosisLog.objects.create(
                appointment=app1,
                diagnosis_notes="Inspected front & rear brakes. Front ceramic pads worn to 2mm. Rotors resurfaced.",
                parts_used="Front Ceramic Brake Pads Set ($65.00), Brake Fluid Flush ($25.00)",
                labor_hours=Decimal("1.50")
            )
            inv1 = Invoice.objects.create(appointment=app1)
            inv1.calculate_total()
            inv1.mark_paid()

        # Job 2: In Progress Diagnostics for John's F-150
        app2, created = Appointment.objects.get_or_create(
            customer=john_profile,
            vehicle=f150,
            service=services["Full Engine Diagnostics"],
            scheduled_date=today,
            scheduled_time=time(11, 30),
            defaults={
                "mechanic": mech_profiles["mike_mech"],
                "status": Appointment.Status.IN_PROGRESS,
                "notes": "Check engine light illuminated. Rough idle at cold start."
            }
        )
        if created:
            DiagnosisLog.objects.create(
                appointment=app2,
                diagnosis_notes="OBD-II code misfire Cylinder 3. Testing ignition coil voltage.",
                parts_used="Pending diagnostic resolution",
                labor_hours=Decimal("1.00")
            )
            inv2 = Invoice.objects.create(appointment=app2)
            inv2.calculate_total()

        # Job 3: Pending Appointment for Alice's Civic
        app3, created = Appointment.objects.get_or_create(
            customer=alice_profile,
            vehicle=civic,
            service=services["Oil & Filter Service"],
            scheduled_date=today,
            scheduled_time=time(14, 0),
            defaults={
                "status": Appointment.Status.PENDING,
                "notes": "Regular 10k mile maintenance check."
            }
        )

        # 6. Notifications
        Notification.objects.get_or_create(
            user=john_user,
            appointment=app1,
            message="Your Brake Inspection & Replacement on 2021 Toyota Camry is COMPLETED! Invoice paid."
        )
        Notification.objects.get_or_create(
            user=alice_user,
            appointment=app3,
            message="Booking received for Oil & Filter Service. Technician assignment pending."
        )

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
