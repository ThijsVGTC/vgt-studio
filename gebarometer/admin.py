from django.contrib import admin

from .models import GebarometerItem


@admin.register(GebarometerItem)
class GebarometerItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "display_gloss",
        "planned_date",
        "mailchimp_status",
        "total_votes",
        "mailchimp_report_id",
    )

    list_filter = (
        "mailchimp_status",
        "planned_date",
    )

    search_fields = (
        "historical_gloss",
        "signbank_entry__gloss",
        "mailchimp_report_id",
    )

    ordering = (
        "-planned_date",
        "-id",
    )

    @admin.display(description="Gloss")
    def display_gloss(self, obj):
        if obj.signbank_entry:
            return obj.signbank_entry.gloss

        return obj.historical_gloss or "—"