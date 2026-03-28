from django.contrib import admin
from .models import WasteType, RecyclingPoint, UserProfile, Transaction, Review # Додали Review сюди

admin.site.register(WasteType)
admin.site.register(RecyclingPoint)
admin.site.register(UserProfile)
admin.site.register(Transaction)
admin.site.register(Review)