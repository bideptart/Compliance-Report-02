from django.db import migrations, models


def clear_existing_customers(apps, schema_editor):
    # The Customers table is fully derived from the CSV import (never
    # user-edited), so clearing it before reshaping the schema is safe --
    # running `import_customers` afterwards repopulates it cleanly under the
    # new one-row-per-unique-carrier model. This never touches RMD data.
    Customer = apps.get_model("customers", "Customer")
    Customer.objects.all().delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(clear_existing_customers, noop_reverse),
        migrations.RemoveConstraint(
            model_name="customer",
            name="unique_carrier_country",
        ),
        migrations.RemoveIndex(
            model_name="customer",
            name="customers_c_country_fc020b_idx",
        ),
        migrations.RemoveField(
            model_name="customer",
            name="country",
        ),
        migrations.AddField(
            model_name="customer",
            name="carrier_key",
            field=models.CharField(default="", max_length=255, unique=True, db_index=True),
            preserve_default=False,
        ),
    ]
