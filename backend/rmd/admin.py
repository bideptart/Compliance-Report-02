from django.contrib import admin

from .models import RmdFiling


@admin.register(RmdFiling)
class RmdFilingAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "business_name",
        "frn",
        "country",
        "implementation",
        "last_updated",
        "last_recertified",
    )
    search_fields = ("number", "business_name", "frn", "sys_id", "other_frns", "other_dba_names")
    list_filter = ("implementation", "foreign_voice_provider", "country")
    readonly_fields = ("imported_at", "updated_in_db_at")
    ordering = ("business_name",)
