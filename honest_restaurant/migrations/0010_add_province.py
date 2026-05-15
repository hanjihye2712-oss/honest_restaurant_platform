from django.db import migrations, models


def fill_province(apps, schema_editor):
    """기존 레코드의 address_road(또는 address_jibun) 첫 토큰으로 province 채우기."""
    Model = apps.get_model("honest_restaurant", "PublicRestaurantData")
    batch = []
    for obj in Model.objects.all().only("id", "address_road", "address_jibun"):
        addr = obj.address_road or obj.address_jibun
        obj.province = addr.split()[0] if addr else ""
        batch.append(obj)
        if len(batch) >= 1000:
            Model.objects.bulk_update(batch, ["province"])
            batch.clear()
    if batch:
        Model.objects.bulk_update(batch, ["province"])


class Migration(migrations.Migration):

    dependencies = [
        ("honest_restaurant", "0009_add_performance_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="publicrestaurantdata",
            name="province",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="address_road 첫 번째 토큰에서 자동 추출 (예: 서울특별시, 경기도, 부산광역시)",
                max_length=20,
                verbose_name="시/도",
            ),
        ),
        migrations.AddIndex(
            model_name="publicrestaurantdata",
            index=models.Index(
                fields=["province", "status_code", "synced_at"],
                name="idx_province_status_synced",
            ),
        ),
        migrations.RunPython(fill_province, migrations.RunPython.noop),
    ]
