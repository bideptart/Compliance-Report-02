from django.contrib import admin

from .models import Fcc499Filing


@admin.register(Fcc499Filing)
class Fcc499FilingAdmin(admin.ModelAdmin):
    list_display = (
        "legal_name",
        "filer_id",
        "doing_business_as",
        "usf_contributor",
        "registration_current_as_of",
        "fetched_at",
    )
    search_fields = ("legal_name", "filer_id", "doing_business_as", "cores_id", "search_company_name")
    readonly_fields = ("fetched_at", "updated_at")
    ordering = ("legal_name",)
