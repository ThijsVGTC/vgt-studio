from django.contrib import admin
from .models import RecordingItem, AllowedGoogleEmail
# Register your models here.
admin.site.register(RecordingItem)

@admin.register(AllowedGoogleEmail)
class AllowedGoogleEmailAdmin(admin.ModelAdmin):
    list_display = ("email", "active", "note")
    list_filter = ("active",)
    search_fields = ("email", "note")