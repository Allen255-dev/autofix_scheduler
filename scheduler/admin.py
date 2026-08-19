from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, CustomerProfile, MechanicProfile, Vehicle,
    ServiceType, Appointment, DiagnosisLog, Invoice, Notification,
)


class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Role info", {"fields": ("role", "phone_number")}),
    )
    list_display = ("username", "email", "role", "is_staff")


admin.site.register(User, CustomUserAdmin)
admin.site.register(CustomerProfile)
admin.site.register(MechanicProfile)
admin.site.register(Vehicle)
admin.site.register(ServiceType)
admin.site.register(Appointment)
admin.site.register(DiagnosisLog)
admin.site.register(Invoice)
admin.site.register(Notification)
