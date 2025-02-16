# Generated by Django 5.1.6 on 2025-02-16 17:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TipoPersona',
            fields=[
                ('idTP', models.AutoField(primary_key=True, serialize=False)),
                ('nombre', models.CharField(max_length=100)),
            ],
            options={
                'verbose_name': 'Tipo de Persona',
                'verbose_name_plural': 'Tipos de Personas',
            },
        ),
        migrations.CreateModel(
            name='Personas',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cedula', models.CharField(max_length=10)),
                ('nombres', models.CharField(max_length=100)),
                ('apellidos', models.CharField(max_length=100)),
                ('telefono', models.CharField(max_length=15)),
                ('correo', models.EmailField(max_length=254)),
                ('estadoPersona', models.CharField(max_length=10)),
                ('fecha', models.DateField(auto_now_add=True)),
                ('idTP', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='home.tipopersona')),
            ],
            options={
                'verbose_name': 'Persona',
                'verbose_name_plural': 'Personas',
                'ordering': ['nombres'],
            },
        ),
    ]
