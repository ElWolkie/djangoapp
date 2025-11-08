# apps/factura/migrations/0003_drop_fk_home_cuota.py
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('factura', '0002_initial'),
    ]

    operations = [
        # DROP CONSTRAINT IF EXISTS para evitar fallos si ya la quitaste manualmente
        migrations.RunSQL(
            sql=(
                "ALTER TABLE factura_notarelacionada "
                "DROP CONSTRAINT IF EXISTS factura_notarelacion_idCuota_id_dd647612_fk_home_cuot;"
            ),
            reverse_sql=(
                # No intentamos recrear la constraint automáticamente porque la definición exacta puede variar.
                # Si necesitas recrearla en forward->reverse, pon aquí la sentencia CREATE CONSTRAINT correspondiente.
                "SELECT 1;"
            )
        ),
    ]
