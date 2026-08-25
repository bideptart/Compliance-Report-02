from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("carrier", "imported_at")
    search_fields = ("carrier",)
    readonly_fields = ("carrier_key", "imported_at", "updated_in_db_at")
    ordering = ("carrier",)
