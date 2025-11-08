# Generated manually: factura/migrations/0003_drop_fk_home_cuota.py
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('factura', '0003_previous_migration'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE factura_notarelacionada DROP CONSTRAINT IF EXISTS "factura_notarelacion_idCuota_id_dd647612_fk_home_cuot";',
            reverse_sql='-- reverse not implemented: recreate FK if needed (manual)',
        ),
    ]