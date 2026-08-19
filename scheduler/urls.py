from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="scheduler/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("vehicle/add/", views.add_vehicle, name="add_vehicle"),
    path("vehicle/<int:pk>/delete/", views.delete_vehicle, name="delete_vehicle"),
    path("appointment/book/", views.book_appointment, name="book_appointment"),
    path("appointment/<int:pk>/cancel/", views.cancel_appointment, name="cancel_appointment"),
    path("appointment/<int:pk>/status/", views.update_job_status, name="update_job_status"),
    path("appointment/<int:pk>/diagnosis/", views.log_diagnosis, name="log_diagnosis"),
    path("appointment/<int:pk>/assign/", views.assign_mechanic, name="assign_mechanic"),
    path("appointment/<int:pk>/invoice/", views.invoice_detail, name="invoice_detail"),
    path("invoice/<int:pk>/pay/", views.pay_invoice, name="pay_invoice"),
    path("notifications/", views.notifications_list, name="notifications"),
    path("services/add/", views.add_service, name="add_service"),
    path("services/<int:pk>/edit/", views.edit_service, name="edit_service"),
]
