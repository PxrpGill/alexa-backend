from django.db import migrations


class Migration(migrations.Migration):
    """Сводит два листа графа: 0005_alter_promotioncondition_icon (SVG-иконки
    условий) и 0005_slug_max_length (расширение slug'а) — ветки смерджены
    в main независимо друг от друга."""

    dependencies = [
        ("promotions", "0005_alter_promotioncondition_icon"),
        ("promotions", "0005_slug_max_length"),
    ]

    operations = []
