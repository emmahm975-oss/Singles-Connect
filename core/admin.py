from django.contrib import admin
from .models import Profile, Connection, CheckoutSession, Message, SuccessStory

admin.site.register(Profile)
admin.site.register(Connection)
admin.site.register(CheckoutSession)
admin.site.register(Message)
admin.site.register(SuccessStory)