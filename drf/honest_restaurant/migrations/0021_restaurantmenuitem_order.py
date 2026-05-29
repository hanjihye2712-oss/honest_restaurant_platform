from django.db import migrations, models


def set_order_to_id(apps, schema_editor):
    RestaurantMenuItem = apps.get_model('honest_restaurant', 'RestaurantMenuItem')
    for item in RestaurantMenuItem.objects.all().order_by('id'):
        item.order = item.id
        item.save(update_fields=['order'])


class Migration(migrations.Migration):

    dependencies = [
        ('honest_restaurant', '0020_restaurantmenuitem_ordering_by_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='restaurantmenuitem',
            name='order',
            field=models.PositiveIntegerField(db_index=True, default=0, verbose_name='표시 순서'),
        ),
        migrations.AlterModelOptions(
            name='restaurantmenuitem',
            options={
                'ordering': ['order', 'id'],
                'verbose_name': '메뉴 항목',
                'verbose_name_plural': '메뉴 항목',
            },
        ),
        migrations.RunPython(set_order_to_id, migrations.RunPython.noop),
    ]
