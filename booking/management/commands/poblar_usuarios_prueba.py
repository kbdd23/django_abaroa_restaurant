"""Puebla las cuentas de prueba que ocupan mesas enteras.

MrEveryday y MrCopycat no tienen logica de negocio ni consumos: existen solo
para llenar el salon y que el flujo de reservas y el panel del mesero se vean
con mesas tomadas de punta a punta.

Cada cuenta toma, hora por hora, todos los bloques del dia (00:00-23:00,
incluidos los que caen fuera del horario de atencion) en su propia mesa,
desde hoy hasta `--dias` dias adelante. Se crean con `objects.create` y no con
la vista de reserva a proposito: el formulario rechazaria los bloques fuera
de horario, y aqui lo que se busca es justamente ocupar todo.
"""

from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from booking.models import Mesa, Reserva
from panel.models import User

CUENTAS_DE_PRUEBA = (
    {"username": "MrEveryday", "first_name": "Mr Everyday", "numero_mesa": 1},
    {"username": "MrCopycat", "first_name": "Mr Copycat", "numero_mesa": 2},
)

# Cuenta con la que el docente revisa el panel propio y el django-admin.
CUENTA_ADMIN = "ADMIN"
CLAVE_ADMIN_POR_DEFECTO = "1234"

CLAVE_POR_DEFECTO = "prueba1234"

PRIMERA_HORA = 0
ULTIMA_HORA = 23  # el ultimo bloque del dia termina a las 23:00
DIAS_POR_DEFECTO = 30


class Command(BaseCommand):
    help = "Crea MrEveryday y MrCopycat y los llena de reservas hora por hora."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dias",
            type=int,
            default=DIAS_POR_DEFECTO,
            help="Cuantos dias hacia adelante se llenan (por defecto 30).",
        )
        parser.add_argument(
            "--clave",
            default=CLAVE_POR_DEFECTO,
            help="Clave con la que quedan las dos cuentas de prueba.",
        )
        parser.add_argument(
            "--clave-admin",
            default=CLAVE_ADMIN_POR_DEFECTO,
            help="Clave con la que queda la cuenta ADMIN.",
        )
        parser.add_argument(
            "--limpiar",
            action="store_true",
            help="Borra las reservas existentes de estas cuentas antes de poblarlas.",
        )

    def handle(self, *args, **opciones):
        dias = opciones["dias"]
        clave = opciones["clave"]

        if dias < 1:
            raise CommandError("--dias debe ser al menos 1.")

        hoy = timezone.localdate()

        self.crear_admin(opciones["clave_admin"])

        for cuenta in CUENTAS_DE_PRUEBA:
            mesa = Mesa.objects.filter(numero=cuenta["numero_mesa"]).first()
            if mesa is None:
                raise CommandError(
                    f"No existe la mesa {cuenta['numero_mesa']}: revisa que las migraciones de booking corrieron."
                )

            usuario = self.crear_cuenta(cuenta, clave)

            if opciones["limpiar"]:
                borradas = Reserva.objects.filter(cliente=usuario).delete()
                self.stdout.write(f"  reservas borradas: {borradas[0]}")

            creadas = self.poblar_mesas(usuario, mesa, hoy, dias)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{usuario.username}: mesa {mesa.numero}, {creadas} reservas nuevas."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f"Listo: {dias} dias desde {hoy}.")
        )

    def crear_admin(self, clave):
        """Crea o actualiza ADMIN: rol admin, staff y superusuario.

        El rol se asigna despues del create porque create_user() rechaza
        'rol' a proposito: es la misma via controlada que usa User.crear_admin,
        pero pasando por save() para poder fijar tambien is_staff.
        """
        usuario, creado = User.objects.get_or_create(
            username=CUENTA_ADMIN,
            defaults={"first_name": "ADMIN"},
        )
        usuario.rol = User.Rol.ADMIN
        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.set_password(clave)
        usuario.save()

        estado = "creada" if creado else "actualizada"
        self.stdout.write(f"{usuario.username} {estado} (rol {usuario.rol}).")
        return usuario

    def crear_cuenta(self, cuenta, clave):
        """Crea o actualiza la cuenta, siempre como cliente."""
        usuario, creado = User.objects.get_or_create(
            username=cuenta["username"],
            defaults={"first_name": cuenta["first_name"]},
        )
        usuario.first_name = cuenta["first_name"]
        usuario.rol = User.Rol.CLIENTE
        usuario.set_password(clave)
        usuario.save()

        estado = "creada" if creado else "actualizada"
        self.stdout.write(f"{usuario.username} {estado} (rol {usuario.rol}).")
        return usuario

    def poblar_mesas(self, usuario, mesa, hoy, dias):
        """Llena los bloques de cada dia, saltando los que ya existan."""
        bloques_por_dia = [
            (time(hora, 0), time(hora + 1, 0))
            for hora in range(PRIMERA_HORA, ULTIMA_HORA)
        ]

        fechas = [hoy + timedelta(days=desplazamiento) for desplazamiento in range(dias)]

        # Una sola consulta por mesa: el conjunto (fecha, hora_inicio) ya tomado.
        ya_reservados = {
            (reserva.fecha, reserva.hora_inicio)
            for reserva in Reserva.objects.filter(
                mesa=mesa,
                fecha__gte=fechas[0],
                fecha__lte=fechas[-1],
                estado=Reserva.ESTADO_CONFIRMADO,
            )
        }

        nuevas = []
        for fecha in fechas:
            for hora_inicio, hora_fin in bloques_por_dia:
                if (fecha, hora_inicio) in ya_reservados:
                    continue
                nuevas.append(
                    Reserva(
                        cliente=usuario,
                        mesa=mesa,
                        fecha=fecha,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                    )
                )

        Reserva.objects.bulk_create(nuevas)
        return len(nuevas)
