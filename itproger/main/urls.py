from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('about/', views.about, name='about'),
    
    # Маршрути для авторизації
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='main/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('point/<int:point_id>/', views.point_detail, name='point_detail'),
    path('profile/', views.profile, name='profile'),
    path('rewards/', views.rewards, name='rewards'),
    path('partner-panel/', views.partner_panel, name='partner_panel'),
    path('settings/', views.settings_view, name='settings'),
]