from django.urls import path

from scheduler import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/mosque/", views.mosque_register, name="mosque_request"),
    path("register/imam/", views.imam_register, name="imam_application"),
    path("success/<str:kind>/<int:pk>/", views.success, name="success"),
    # Admin (combined)
    path("panel/", views.admin_panel, name="admin_panel"),
    # Login / logout
    path("login/mosque/", views.mosque_login, name="mosque_login"),
    path("login/imam/", views.imam_login, name="imam_login"),
    path("logout/", views.portal_logout, name="portal_logout"),
    # Mosque portal
    path("portal/mosque/", views.mosque_portal, name="mosque_portal"),
    path("portal/mosque/request/", views.request_friday, name="request_friday"),
    path("portal/mosque/cancel/<int:pk>/", views.cancel_week_request, name="cancel_week_request"),
    path("portal/mosque/preferred/", views.set_preferred_imam, name="set_preferred_imam"),
    path("portal/mosque/review/<int:pk>/", views.submit_review, name="submit_review"),
    # Imam portal
    path("portal/imam/", views.imam_portal, name="imam_portal"),
    path("portal/imam/availability/", views.toggle_unavailability, name="toggle_unavailability"),
    path("portal/imam/training/", views.imam_training, name="imam_training"),
    path("portal/imam/training/quiz/", views.submit_quiz, name="submit_quiz"),
]
