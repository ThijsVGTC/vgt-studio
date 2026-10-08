from django.urls import path

from . import views


app_name = "gebarometer"


urlpatterns = [
    path(
        "",
        views.gebarometer_overview,name="overview",
    ),
    path(
        "<int:pk>/",
        views.gebarometer_detail,
        name="detail",
    ),
]