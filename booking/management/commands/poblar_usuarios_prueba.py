"""Puebla las cuentas de prueba del sistema y las mesas de demostracion.

Crea el equipo que se usa en la presentacion: un administrador, tres meseros y
un cliente, todos con el correo como nombre de usuario porque el login del
sitio autentica contra el campo de correo.

Ademas crea MrEveryday y MrCopycat, que no tienen logica de negocio ni
consumos: existen solo para llenar el salon y que el flujo de reservas y el
panel del mesero se vean con mesas tomadas de punta a punta. Cada uno toma,
hora por hora, todos los bloques del dia (00:00-23:00, incluidos los que caen
fuera del horario de atencion) en su propia mesa, desde hoy hasta `--dias` dias
adelante. Esas reservas se crean con `objects.create` y no con la vista de
reserva a proposito: el formulario rechazaria los bloques fuera de horario, y
aqui lo que se busca es justamente ocupar todo.
"""

from datetime import time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from booking.models import Mesa, Reserva
from panel.models import User

ADMINISTRADORES = (
    {"username": "admin@abaroa.cl", "first_name": "Admin"},
)

MESEROS = (
    {"username": "ana@abaroa.cl", "first_name": "Ana"},
    {"username": "matias@abaroa.cl", "first_name": "Matias"},
    {"username": "francisco@abaroa.cl", "first_name": "Francisco"},
)

CLIENTES = (
    {"username": "usuario@gmail.com", "first_name": "Usuario"},
)

# Estas dos, ademas de existir, llenan su mesa con reservas.
CUENTAS_DE_PRUEBA = (
    {"username": "mreveryday", "first_name": "Mr Everyday", "numero_mesa": 1},
    {"username": "mrcopycat", "first_name": "Mr Copycat", "numero_mesa": 2},
)

CLAVE_POR_DEFECTO = "12345678"

PRIMERA_HORA = 0
ULTIMA_HORA = 23  # el ultimo bloque del dia termina a las 23:00
DIAS_POR_DEFECTO = 30


class Command(BaseCommand):
    help = "Crea las cuentas de prueba y llena las mesas 1 y 2 hora por hora."

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
            help="Clave con la que quedan todas las cuentas.",
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

        for datos in ADMINISTRADORES:
            self.crear_persona(datos, User.Rol.ADMIN, clave)

        for datos in MESEROS:
            self.crear_persona(datos, User.Rol.MESERO, clave)

        for datos in CLIENTES:
            self.crear_persona(datos, User.Rol.CLIENTE, clave)

        for cuenta in CUENTAS_DE_PRUEBA:
            mesa = Mesa.objects.filter(numero=cuenta["numero_mesa"]).first()
            if mesa is None:
                raise CommandError(
                    f"No existe la mesa {cuenta['numero_mesa']}: revisa que las migraciones de booking corrieron."
                )

            usuario = self.crear_persona(cuenta, User.Rol.CLIENTE, clave)

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

    def crear_persona(self, datos, rol, clave):
        """Crea o actualiza la cuenta con ese rol.

        El rol se asigna despues del create porque create_user() lo rechaza a
        proposito (evita escalar privilegios desde el frontend). Solo el
        administrador lleva is_staff e is_superuser: son las banderas del
        django-admin nativo.
        """
        usuario, creado = User.objects.get_or_create(
            username=datos["username"],
            defaults={"email": datos["username"], "first_name": datos["first_name"]},
        )
        usuario.email = datos["username"]
        usuario.first_name = datos["first_name"]
        usuario.rol = rol
        usuario.is_staff = rol == User.Rol.ADMIN
        usuario.is_superuser = rol == User.Rol.ADMIN
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
