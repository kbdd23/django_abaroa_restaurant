# Restaurante Abaroa - Backend 
Tercera etapa del proyecto académico iniciado en la Unidad 1.

Esta etapa cierra el sistema: operaciones CRUD completas (crear, consultar, modificar y eliminar) desde las interfaces propias del sitio, validaciones en los formularios, autenticación con manejo de sesiones y medidas básicas de seguridad, todo sobre la persistencia en base de datos incorporada en la etapa anterior.

# Base de datos
El proyecto usa MongoDB Atlas en la nube mediante `django-mongodb-backend` en lugar de MySQL por defecto de Django.

La conexión se configura en un archivo `db.env` ubicado en la raiz, mismo nivel que `manage.py`. El archivo .env no se sube al repositorio git, está incluido en el .gitignore para no exponer las credenciales.

Con el env cargado la estructura se levanta con:
```
python manage.py migrate
```

# Roles y control de acceso

El usuario hereda de `AbstractUser` y agrega el campo `rol` con tres valores: `cliente`, `mesero` y `admin`.

Cada rol tiene su propio decorador en `panel/decorators.py` (`cliente_required`, `mesero_required`, `admin_required`) de manera que si un usuario autenticado con el rol equivocado intenta entrar a una ruta que no debería este recibirá un `403`, prohibiendole accesos indebidos de forma explicita.

# Panel de administración
Además del admin nativo, el proyecto tiene un panel propio en `/admin/`, construido con sus propias vistas y plantillas que incluyen el decorador `admin_required` para poder acceder.

Desde allí un administrador puede:

-Gestionar la carta: crear, editar, retirar y reactivar platos.
-Gestionar alérgenos, que son el origen de los tags del menú publico.
-Gestionar mesas: crear, mover redimensionar el salón y retirar/activar mesas.
-Dar de alta a meseros y administradores. 
-Revisar y cancelar reservas
-Desactivar y reactivar clientes.

Todas las bajas son con *soft-delete*: retirar un plato, mesa, cliente, mesero no lo elimina solamente lo saca de servicio. Sin borrar trazabilidad.


# Usuarios de prueba

El proyecto se entrega con cuentas que existen solo para la revisión: no hay contraseñas personales ni credenciales de servicios reales.

| Usuario | Clave | Rol | Para qué sirve |
|---|---|---|---|
| `admin@abaroa.cl` | `12345678` | `admin` | Entrar al panel propio (`/admin/`) y al django-admin con todos los permisos |
| `ana@abaroa.cl` | `12345678` | `mesero` | Atender mesas y abrir cuentas desde `/mesero/` |
| `matias@abaroa.cl` | `12345678` | `mesero` | Lo mismo, para probar dos sesiones en paralelo |
| `francisco@abaroa.cl` | `12345678` | `mesero` | Lo mismo |
| `usuario@gmail.com` | `12345678` | `cliente` | Reservar mesas desde el sitio público |
| `mreveryday` | `12345678` | `cliente` | Ocupa la mesa 1 en todos los bloques horarios |
| `mrcopycat` | `12345678` | `cliente` | Lo mismo en la mesa 2, para comparar mesas tomadas |

El login del sitio autentica por correo, así que el nombre de usuario es el correo completo. `admin@abaroa.cl` se crea con `rol='admin'`, `is_staff` e `is_superuser`, así que sirve para las dos administraciones sin pasos extra.

# Datos de prueba para la demostración de reserva

Las cuentas de prueba no viajan en el repositorio: se reconstruyen contra la base de datos que estés usando. Con las migraciones ya aplicadas:

```
python manage.py poblar_usuarios_prueba
```

El comando crea todas las cuentas de la tabla y llena la mesa 1 y la mesa 2 con un bloque por hora (00:00 a 23:00, incluidos los bloques fuera del horario de atención) desde el día de hoy hasta 30 días adelante. Como las fechas se calculan al ejecutarlo, las reservas siempre quedan vigentes.

Opciones:

- `--dias N` cambia el alcance (por defecto 30).
- `--limpiar` borra las reservas anteriores de esas cuentas antes de repoblarlas.
- `--clave` cambia la clave de todos los usuarios de prueba.

```
python manage.py poblar_usuarios_prueba --dias 30 --limpiar
```

# Django-admin
Igualmente, creamos un superusuario y añadimos los modelos al django-admin.

Cabe nombrar que crear un superusuario hace que este nazca con el `rol='cliente'` y nuestros decoradores de `'admin_required'` exige `rol=ADMIN` asi que el superusuario servirá solo para `/django-admin/` pero no para nuestro panel propio de administración.

Para lograr que el superusuario sea compatible con nuestro panel de adminstración personalizado se debe cambiar su rol desde panel.User en django-admin o en su defecto cambiarlo con el comando:

```
python manage.py shell -c "from panel.models import User;u=User.objects.get(username='TU_USERNAME'); u.rol=User.Rol.ADMIN; u.save(update_fields=['rol'])"
```

