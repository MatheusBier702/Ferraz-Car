from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
urlpatterns = [path('api/clients/<int:pk>/', views.client_detail, name='client-detail'), path('api/vehicles/<int:pk>/', views.vehicle_detail, name='vehicle-detail'), path('login/', auth_views.LoginView.as_view(template_name='oficina/login.html', redirect_authenticated_user=True), name='login'), path('logout/', auth_views.LogoutView.as_view(), name='logout'), path('', views.dashboard, name='dashboard'), path('api/services/', views.services, name='services'), path('api/services/<int:pk>/', views.service_detail, name='service-detail')]
