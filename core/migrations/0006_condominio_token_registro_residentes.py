import uuid

from django.db import migrations, models


def asignar_tokens_unicos(apps, schema_editor):
    modelo_condominio = apps.get_model("core", "Condominio")
    for condominio in modelo_condominio.objects.all():
        condominio.token_registro_residentes = uuid.uuid4()
        condominio.save(update_fields=["token_registro_residentes"])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_solicitudacceso'),
    ]

    operations = [
        migrations.AddField(
            model_name='condominio',
            name='token_registro_residentes',
            field=models.UUIDField(null=True, editable=False, help_text='Identifica el link/QR público de autoregistro de residentes de este condominio.'),
        ),
        migrations.RunPython(asignar_tokens_unicos, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='condominio',
            name='token_registro_residentes',
            field=models.UUIDField(default=uuid.uuid4, editable=False, help_text='Identifica el link/QR público de autoregistro de residentes de este condominio.', unique=True),
        ),
    ]
