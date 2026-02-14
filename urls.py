from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.dashboard, name="dashboard"),

    path("inventory/receive/", views.receive_inventory),
    path("inventory/summary/<int:item_id>/", views.stock_summary),
    path("get_stock_summary/", views.get_stock_summary),
    path("reserve_inventory/", views.reserve_inventory),
    path("issue_inventory/", views.issue_inventory),
]
