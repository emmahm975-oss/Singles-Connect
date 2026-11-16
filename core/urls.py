from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('discover/', views.discover, name='discover'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('block/<int:user_id>/', views.block_user, name='block_user'),
        path('password-reset/', views.password_reset_request, name='password_reset'),
    
    # New Checkout Flow (No more payment_page)
    path('connect/<int:user_id>/', views.send_connection, name='send_connection'),
    path('checkout/<int:checkout_id>/', views.checkout_page, name='checkout_page'),
    path('checkout/<int:checkout_id>/submit/', views.submit_evidence, name='submit_evidence'),
    path('accept/<int:connection_id>/', views.accept_connection, name='accept_connection'),
    path('chat/<int:connection_id>/', views.chat_view, name='chat_view'),
    path('checkout/<int:checkout_id>/retry/', views.retry_checkout, name='retry_checkout'),
    path('checkout/<int:checkout_id>/delete/', views.delete_checkout, name='delete_checkout'),
    path('success_stories/', views.success_stories, name='success_stories'),
]