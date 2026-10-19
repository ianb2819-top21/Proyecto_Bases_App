from datetime import datetime

from db import crear_db

'''
if __name__ == "__main__":
    iniciar_tablas()
    app.run(port=5000, debug=True)
'''



    
    
''' 2.	Gestión de usuarios
La aplicación debe permitir:
•	Registrar usuarios con datos mínimos: código, identificación, nombres, correo, rol (estudiante/docente), carrera (opcional), estado (activo/bloqueado).
•	Consultar historial de préstamos por usuario. '''

def registrar_usuario(codigo, identificacion, nombres, correo, rol, carrera=None, estado="Activo"):
    with crear_db() as db:
        with db.transaccion():
            db.ejecutar("""
                INSERT INTO usuarios (codigo, identificacion, nombres, correo, rol, carrera, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (codigo, identificacion, nombres, correo, rol, carrera, estado))
            if rol.lower() == 'administrador':
                db.ejecutar('INSERT INTO usuario_admin (codigo) VALUES (?)', (codigo,))


def consultar_historial_prestamos_por_usuario(codigo):
    """Préstamos del usuario con título y estado derivado de las fechas reales.

    El SQL define fec_prestamo, fec_vencimiento, fec_devolucion y sancion.
    No inventamos una tarifa de multas: se expone solo la sanción guardada.
    """
    from datetime import date, datetime
    from decimal import Decimal

    with crear_db() as db:
        filas = db.consultar("""
            SELECT p.id_ejemplar, p.codigo_usuario, p.fec_prestamo,
                   p.fec_vencimiento, p.fec_devolucion, p.observaciones,
                   p.estado, p.sancion, l.isbn, l.titulo, l.editorial
            FROM prestamos AS p
            JOIN ejemplares AS e ON e.id_ejemplar = p.id_ejemplar
            JOIN libros AS l ON l.isbn = e.isbn
            WHERE p.codigo_usuario = ?
            ORDER BY p.fec_prestamo DESC, p.id_ejemplar DESC
        """, (codigo,))

    hoy = date.today()
    TARIFA_MULTA_DIARIA = 2000  
    for prestamo in filas:
        vence = prestamo['fec_vencimiento']
        if isinstance(vence, datetime):
            vence = vence.date()
        elif isinstance(vence, str):
            vence = date.fromisoformat(vence)
        devuelto = prestamo['fec_devolucion'] is not None
        dias_restantes = (vence - hoy).days if vence else None
        if devuelto:
            estado_visual = 'Devuelto'
        elif dias_restantes is not None and dias_restantes < 0:
            estado_visual = 'Vencido'
        elif dias_restantes is not None and dias_restantes <= 3:
            estado_visual = 'Próximo a vencer'
        else:
            estado_visual = 'Activo'

        prestamo['estado_visual'] = estado_visual
        
        # Calculamos el retraso usando la fecha de devolución
        # o la fecha actual si todavía no ha sido devuelto.
        fecha_devolucion = prestamo['fec_devolucion']

        if isinstance(fecha_devolucion, datetime):
            fecha_devolucion = fecha_devolucion.date()
        elif isinstance(fecha_devolucion, str):
            fecha_devolucion = date.fromisoformat(fecha_devolucion)

        fecha_referencia = fecha_devolucion or hoy

        dias_retraso = (
            max((fecha_referencia - vence).days, 0)
            if vence else 0
        )

        prestamo['dias_retraso'] = dias_retraso
        prestamo['dias_restantes'] = dias_restantes if not devuelto else None
        prestamo['multa_calculada'] = dias_retraso * 2000

        # Calculamos la multa según la política de la biblioteca.
        prestamo['multa_calculada'] = (
            Decimal(dias_retraso) * Decimal(TARIFA_MULTA_DIARIA)
        )

        # Conservamos la sanción registrada originalmente en MySQL.
        prestamo['sancion'] = Decimal(str(prestamo['sancion'] or 0))

    return filas


''' 4.	Gestión de Devolución
La aplicación debe permitir:
•	Registrar la devolución de un ejemplar y actualizar su estado a disponible.
•	Si existe retraso, calcular automáticamente sanción/multa.
•	Registrar observaciones del ejemplar al devolver: “dañado”, “páginas faltantes”.
'''

TARIFA_MULTA_DIARIA = 2000  # COP por día de retraso


def _a_fecha(valor):
    """Normaliza date/datetime/str a date (o None)."""
    from datetime import date, datetime as _dt
    if valor is None:
        return None
    if isinstance(valor, _dt):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor)[:10])


def registrar_devolucion(id_ejemplar, observaciones=None):
    from datetime import date
    hoy = date.today()
    with crear_db() as db:
        with db.transaccion():
            ejemplares = db.consultar(
                "SELECT estado FROM ejemplares WHERE id_ejemplar = ? FOR UPDATE",
                (id_ejemplar,))
            if not ejemplares or str(ejemplares[0]['estado']).lower() != 'prestado':
                raise ValueError('El ejemplar no está marcado como prestado.')
            prestamos = db.consultar("""
                SELECT codigo_usuario, fec_prestamo, fec_vencimiento
                FROM prestamos WHERE id_ejemplar = ? AND fec_devolucion IS NULL
                AND LOWER(estado) IN ('activo', 'aprobado') FOR UPDATE
            """, (id_ejemplar,))
            if len(prestamos) != 1:
                raise ValueError('Debe existir exactamente un préstamo activo del ejemplar.')
            prestamo = prestamos[0]
            vence = _a_fecha(prestamo['fec_vencimiento'])
            retraso = max((hoy - vence).days, 0) if vence else 0
            multa = retraso * TARIFA_MULTA_DIARIA
            filas = db.ejecutar("""
                UPDATE prestamos SET fec_devolucion = ?, observaciones = ?,
                       estado = 'devuelto', sancion = ?
                WHERE id_ejemplar = ? AND codigo_usuario = ? AND fec_prestamo = ?
                  AND fec_devolucion IS NULL
            """, (hoy, observaciones or None, multa, id_ejemplar,
                  prestamo['codigo_usuario'], prestamo['fec_prestamo']))
            if filas != 1:
                raise ValueError('No se pudo actualizar el préstamo.')
            if db.ejecutar("UPDATE ejemplares SET estado = 'Disponible' WHERE id_ejemplar = ?",
                          (id_ejemplar,)) != 1:
                raise ValueError('No se pudo actualizar el ejemplar.')
    return {'codigo_usuario': prestamo['codigo_usuario'], 'dias_retraso': retraso, 'multa': multa}

def obtener_prestamos_activos_y_vencidos():
    with crear_db() as db:
        activos = db.consultar("""
            SELECT p.*, l.titulo, u.nombres
            FROM prestamos p JOIN ejemplares e ON e.id_ejemplar = p.id_ejemplar
            JOIN libros l ON l.isbn = e.isbn
            JOIN usuarios u ON u.codigo = p.codigo_usuario
            WHERE p.fec_devolucion IS NULL AND LOWER(p.estado) IN ('activo', 'aprobado')
            ORDER BY p.fec_vencimiento
        """)
    from datetime import date
    return {'activos': activos,
            'vencidos': [p for p in activos if _a_fecha(p['fec_vencimiento'])
                         and _a_fecha(p['fec_vencimiento']) < date.today()]}


def obtener_libros_mas_prestados_por_periodo(fecha_inicio, fecha_fin):
    with crear_db() as db:
        return db.consultar("""
            SELECT l.isbn, l.titulo, COUNT(*) AS cantidad_prestamos
            FROM prestamos p JOIN ejemplares e ON e.id_ejemplar = p.id_ejemplar
            JOIN libros l ON l.isbn = e.isbn
            WHERE p.fec_prestamo BETWEEN ? AND ?
              AND LOWER(p.estado) <> 'rechazado'
            GROUP BY l.isbn, l.titulo ORDER BY cantidad_prestamos DESC
        """, (fecha_inicio, fecha_fin))


def obtener_usuarios_con_mas_prestamos():
    with crear_db() as db:
        return db.consultar(
            "SELECT codigo_usuario, COUNT(*) AS cantidad_prestamos "
            "FROM prestamos "
            "GROUP BY codigo_usuario "
            "ORDER BY cantidad_prestamos DESC"
        )
        
def obtener_inventario_por_estado(estado):
    with crear_db() as db:
        return db.consultar(
            "SELECT * FROM ejemplares WHERE estado = ?",
            (estado,)
        )
        
def obtener_inventario_completo():
    with crear_db() as db:
        return db.consultar(
            "SELECT * FROM ejemplares"
        )

''' Notificaciones y alertas
La aplicación debe enviar notificaciones a los usuarios sobre: 
•	Préstamos próximos a vencer.
•	Préstamos vencidos.
'''

def obtener_prestamos_proximos_a_vencer():
    from datetime import date, timedelta
    with crear_db() as db:
        return db.consultar("""
            SELECT * FROM prestamos WHERE fec_devolucion IS NULL
              AND LOWER(estado) IN ('activo', 'aprobado')
              AND fec_vencimiento BETWEEN ? AND ?
        """, (date.today(), date.today() + timedelta(days=3)))


def obtener_prestamos_vencidos():
    from datetime import date
    with crear_db() as db:
        return db.consultar("""
            SELECT * FROM prestamos WHERE fec_devolucion IS NULL
              AND LOWER(estado) IN ('activo', 'aprobado')
              AND fec_vencimiento < ?
        """, (date.today(),))


def obtener_usuarios_administradores():
    with crear_db() as db:
        return db.consultar(
            "SELECT * FROM usuarios WHERE rol = 'administrador' OR rol = 'bibliotecario'"
        )
        
'''El usuario busca el libro y solicita el préstamo el cual debe ser aprobado por el administrador.'''

def solicitar_prestamo(id_ejemplar, codigo_usuario):
    from datetime import date
    with crear_db() as db:
        with db.transaccion():
            ej = db.consultar(
                'SELECT estado FROM ejemplares WHERE id_ejemplar = ? FOR UPDATE',
                (id_ejemplar,))
            if not ej or str(ej[0]['estado']).lower() != 'disponible':
                raise ValueError('El ejemplar no está disponible.')
            existe = db.consultar("""
                SELECT id_ejemplar FROM prestamos
                WHERE id_ejemplar = ? AND fec_devolucion IS NULL
                  AND LOWER(estado) IN ('pendiente', 'aprobado', 'activo')
            """, (id_ejemplar,))
            if existe:
                raise ValueError('El ejemplar ya tiene un préstamo o solicitud activa.')
            db.ejecutar("""
                INSERT INTO prestamos
                (id_ejemplar, codigo_usuario, fec_prestamo, estado, sancion)
                VALUES (?, ?, ?, 'pendiente', 0)
            """, (id_ejemplar, codigo_usuario, date.today()))
    return True


def aprobar_prestamo(id_ejemplar, codigo_usuario):
    from datetime import date, timedelta
    with crear_db() as db:
        with db.transaccion():
            ej = db.consultar(
                'SELECT estado FROM ejemplares WHERE id_ejemplar = ? FOR UPDATE',
                (id_ejemplar,))
            if not ej or str(ej[0]['estado']).lower() != 'disponible':
                raise ValueError('El ejemplar no está disponible.')
            pendientes = db.consultar("""
                SELECT fec_prestamo FROM prestamos
                WHERE id_ejemplar = ? AND codigo_usuario = ?
                  AND LOWER(estado) = 'pendiente' AND fec_devolucion IS NULL
                FOR UPDATE
            """, (id_ejemplar, codigo_usuario))
            if len(pendientes) != 1:
                raise ValueError('No se encontró una única solicitud pendiente.')
            filas = db.ejecutar("""
                UPDATE prestamos SET estado = 'aprobado',
                    fec_vencimiento = COALESCE(fec_vencimiento, ?)
                WHERE id_ejemplar = ? AND codigo_usuario = ? AND fec_prestamo = ?
                  AND LOWER(estado) = 'pendiente'
            """, (date.today() + timedelta(days=7), id_ejemplar,
                  codigo_usuario, pendientes[0]['fec_prestamo']))
            if filas != 1:
                raise ValueError('No se pudo aprobar el préstamo.')
            if db.ejecutar(
                "UPDATE ejemplares SET estado = 'Prestado' WHERE id_ejemplar = ?",
                (id_ejemplar,)) != 1:
                raise ValueError('No se pudo actualizar el ejemplar.')
    return True

def rechazar_prestamo(id_ejemplar, codigo_usuario):
        
    with crear_db() as db:
      
        db.ejecutar(
            "UPDATE prestamos SET estado = 'rechazado' "
            "WHERE id_ejemplar = ? AND codigo_usuario = ? AND estado = 'pendiente'",
            (id_ejemplar, codigo_usuario)
        )
        
def obtener_prestamos_pendientes():
    with crear_db() as db:
        return db.consultar("""
            SELECT p.id_ejemplar, p.codigo_usuario, p.fec_prestamo,
                   l.titulo, u.nombres AS usuario
            FROM prestamos AS p
            JOIN ejemplares AS e ON e.id_ejemplar = p.id_ejemplar
            JOIN libros AS l ON l.isbn = e.isbn
            LEFT JOIN usuarios AS u ON u.codigo = p.codigo_usuario
            WHERE p.estado = 'pendiente'
            ORDER BY p.fec_prestamo
        """)


def obtener_inventario_admin():
    """Todos los ejemplares con su título (para el panel de administración)."""
    with crear_db() as db:
        return db.consultar("""
            SELECT e.id_ejemplar, e.estado, l.isbn, l.titulo
            FROM ejemplares AS e
            JOIN libros AS l ON l.isbn = e.isbn
            ORDER BY l.titulo, e.id_ejemplar
        """)

        
def obtener_prestamos_aprobados():
    with crear_db() as db:
        return db.consultar(
            "SELECT * FROM prestamos WHERE estado = 'aprobado'"
        )
        
def obtener_prestamos_rechazados():
    with crear_db() as db:
        return db.consultar(
            "SELECT * FROM prestamos WHERE estado = 'rechazado'"
        )
        
'''Seguridad y autenticación
La aplicación debe implementar un sistema de autenticación para los usuarios, asegurando que solo los usuarios registrados puedan acceder a las funcionalidades de la aplicación. Se debe utilizar un mecanismo de inicio de sesión con credenciales (usuario y contraseña) y, opcionalmente, se puede implementar autenticación basada en tokens para mayor seguridad.'''

def autenticar_usuario(codigo, identificacion):
    with crear_db() as db:
        usuarios = db.consultar(
            """
            SELECT codigo, identificacion, nombres,
                   correo, estado, rol
            FROM usuarios
            WHERE codigo = ? AND identificacion = ?
            """,
            (codigo, identificacion)
        )

        return usuarios[0] if usuarios else None
            
def bloquear_usuario(codigo):
    with crear_db() as db:
        db.ejecutar(
            "UPDATE usuarios SET estado = 'bloqueado' WHERE codigo = ?",
            (codigo,)
        )
        
def desbloquear_usuario(codigo):
    with crear_db() as db:
        db.ejecutar(
            "UPDATE usuarios SET estado = 'activo' WHERE codigo = ?",
            (codigo,)
        )
        
def obtener_estado_usuario(codigo):
    with crear_db() as db:
        usuario = db.consultar(
            "SELECT estado FROM usuarios WHERE codigo = ?",
            (codigo,)
        )
        if usuario:
            return usuario[0]['estado']
        else:
            return None  # Usuario no encontrado
        
def obtener_rol_usuario(codigo):
    with crear_db() as db:
        usuario = db.consultar(
            "SELECT rol FROM usuarios WHERE codigo = ?",
            (codigo,)
        )
        if usuario:
            return usuario[0]['rol']
        else:
            return None  # Usuario no encontrado
    
def obtener_informacion_usuario(codigo):
    with crear_db() as db:
        usuario = db.consultar(
            "SELECT * FROM usuarios WHERE codigo = ?",
            (codigo,)
        )
        if usuario:
            return usuario[0]
        else:
            return None  # Usuario no encontrado
        
def crear_usuario_administrador(codigo, identificacion, nombres, correo, ):
    with crear_db() as db:
        db.ejecutar(
            "INSERT INTO usuarios (codigo, identificacion, nombres, correo, rol, estado) "
            "VALUES (?, ?, ?, ?, 'administrador', 'activo')",
            (codigo, identificacion, nombres, correo)
        )
        
def crear_usuario_bibliotecario(codigo, identificacion, nombres, correo):
    with crear_db() as db:
        db.ejecutar(
            "INSERT INTO usuarios (codigo, identificacion, nombres, correo, rol, estado) "
            "VALUES (?, ?, ?, ?, 'bibliotecario', 'activo')",
            (codigo, identificacion, nombres, correo)
        )
        
def crear_usuario_estudiante(codigo, identificacion, nombres, correo, carrera):
    with crear_db() as db:
        db.ejecutar(
            "INSERT INTO usuarios (codigo, identificacion, nombres, correo, rol, carrera, estado) "
            "VALUES (?, ?, ?, ?, 'estudiante', ?, 'activo')",
            (codigo, identificacion, nombres, correo, carrera)
        )
        
def crear_usuario_docente(codigo, identificacion, nombres, correo):
    with crear_db() as db:
        db.ejecutar(
            "INSERT INTO usuarios (codigo, identificacion, nombres, correo, rol, estado) "
            "VALUES (?, ?, ?, ?, 'docente', 'activo')",
            (codigo, identificacion, nombres, correo)
        )
        
def eliminar_usuario(codigo):
    with crear_db() as db:
        db.ejecutar(
            "DELETE FROM usuarios WHERE codigo = ?",
            (codigo,)
        )
        
def actualizar_informacion_usuario(codigo, identificacion=None, nombres=None, correo=None, carrera=None, contrasena=None):
    with crear_db() as db:
        usuario = db.consultar(
            "SELECT * FROM usuarios WHERE codigo = ?",
            (codigo,)
        )
        if not usuario:
            raise ValueError("Usuario no encontrado.")
        
        # Construir la consulta de actualización dinámicamente
        campos_actualizar = []
        valores = []
        
        if identificacion is not None:
            campos_actualizar.append("identificacion = ?")
            valores.append(identificacion)
        if nombres is not None:
            campos_actualizar.append("nombres = ?")
            valores.append(nombres)
        if correo is not None:
            campos_actualizar.append("correo = ?")
            valores.append(correo)
        if carrera is not None:
            campos_actualizar.append("carrera = ?")
            valores.append(carrera)
        if campos_actualizar:
            consulta_actualizacion = "UPDATE usuarios SET " + ", ".join(campos_actualizar) + " WHERE codigo = ?"
            valores.append(codigo)
            db.ejecutar(consulta_actualizacion, tuple(valores))
            
        if not campos_actualizar:
            raise ValueError("No se proporcionaron campos para actualizar.")
        
def obtener_usuarios_por_rol(rol):
    with crear_db() as db:
        return db.consultar(
            "SELECT * FROM usuarios WHERE rol = ?",
            (rol,)
        )
        
def obtener_usuarios_por_estado(estado):
    with crear_db() as db:
        return db.consultar(
            "SELECT * FROM usuarios WHERE estado = ?",
            (estado,)
        )

def obtener_usuarios_por_carrera(carrera):
    with crear_db() as db:
        return db.consultar(
            "SELECT * FROM usuarios WHERE carrera = ?",
            (carrera,)
        )
        
def obtener_usuarios_por_nombre(nombre):
    with crear_db() as db:
        return db.consultar(
            "SELECT * FROM usuarios WHERE nombres LIKE ?",
            (f"%{nombre}%",)
        )
        
def obtener_usuarios_por_identificacion(identificacion):
    with crear_db() as db:
        return db.consultar(
            "SELECT * FROM usuarios WHERE identificacion = ?",
            (identificacion,)
        )
        
def obtener_usuarios_por_correo(correo):
    with crear_db() as db:
        return db.consultar(
            "SELECT * FROM usuarios WHERE correo = ?",
            (correo,)
        )

def obtener_usuarios_por_codigo(codigo):
    with crear_db() as db:
        return db.consultar(
            "SELECT * FROM usuarios WHERE codigo = ?",
            (codigo,)
        )


def obtener_catalogo_web():
    """Muestra todos los títulos aunque no haya copias disponibles."""
    with crear_db() as db:
        return db.consultar("""
            SELECT l.isbn, l.titulo,
                COALESCE((SELECT GROUP_CONCAT(categoria SEPARATOR ', ')
                  FROM libro_categoria WHERE isbn = l.isbn), 'Sin categoría') AS categoria,
                COALESCE((SELECT GROUP_CONCAT(autor SEPARATOR ', ')
                  FROM libro_autor WHERE isbn = l.isbn), 'Sin autor') AS autor,
                (SELECT COUNT(*) FROM ejemplares e WHERE e.isbn = l.isbn) AS total_ejemplares,
                (SELECT COUNT(*) FROM ejemplares e WHERE e.isbn = l.isbn
                 AND LOWER(e.estado) = 'disponible') AS disponibles,
                CASE WHEN EXISTS (SELECT 1 FROM ejemplares e WHERE e.isbn = l.isbn
                      AND LOWER(e.estado) = 'disponible')
                     THEN 'Disponible' ELSE 'No disponible' END AS estado,
                CONCAT('https://covers.openlibrary.org/b/isbn/', l.isbn, '-L.jpg') AS imagen,
                (SELECT MIN(e.id_ejemplar) FROM ejemplares e
                 WHERE e.isbn = l.isbn AND LOWER(e.estado) = 'disponible') AS id_disponible
            FROM libros l ORDER BY l.titulo
        """)


def buscar_usuario_por_codigo(codigo):
    """Busca un usuario por su código institucional."""
    from db import crear_db

    with crear_db() as db:
        usuarios = db.consultar("""
            SELECT codigo, identificacion, nombres,
                   correo, carrera, estado, rol
            FROM usuarios
            WHERE codigo = ?
            LIMIT 1
        """, (codigo,))

    return usuarios[0] if usuarios else None

        
        