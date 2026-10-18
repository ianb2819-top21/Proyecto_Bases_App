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

def registrar_usuario(codigo, identificacion, nombres, correo, rol, carrera=None, estado="activo"):
    with crear_db() as db:
        db.ejecutar(
            "INSERT INTO usuarios (identificacion, nombres, correo, rol, carrera, estado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (identificacion, nombres, correo, rol, carrera, estado)
        )

def consultar_historial_prestamos_por_usuario(codigo):
    with crear_db() as db:
        return db.consultar(
            "SELECT * FROM prestamos WHERE codigo_usuario = ? ORDER BY fecha_prestamo DESC",
            (codigo,)
        )
    
''' 4.	Gestión de Devolución
La aplicación debe permitir:
•	Registrar la devolución de un ejemplar y actualizar su estado a disponible.
•	Si existe retraso, calcular automáticamente sanción/multa.
•	Registrar observaciones del ejemplar al devolver: “dañado”, “páginas faltantes”.
'''

def registrar_devolucion(codigo_ejemplar, codigo_usuario, observaciones=None):
    with crear_db() as db:
        # Actualizar estado del ejemplar a disponible
        db.ejecutar(
            "UPDATE ejemplares SET estado = 'disponible' WHERE codigo = ?",
            (codigo_ejemplar,)
        )
        
        # Registrar la devolución en la tabla de devoluciones
        db.ejecutar(
            "INSERT INTO devoluciones (codigo_ejemplar, codigo_usuario, fecha_devolucion, observaciones) "
            "VALUES (?, ?, CURRENT_TIMESTAMP, ?)",
            (codigo_ejemplar, codigo_usuario, observaciones)
        )
        
        # Calcular sanción/multa si hay retraso
        prestamo = db.consultar(
            "SELECT fecha_prestamo FROM prestamos WHERE codigo_ejemplar = ? AND codigo_usuario = ?",
            (codigo_ejemplar, codigo_usuario)
        )
        
        if prestamo:
            fecha_prestamo = prestamo[0]['fecha_prestamo']
            # Aquí se puede implementar la lógica para calcular la sanción/multa según la política de la biblioteca
            tarifa = 2000  # Ejemplo: $2000 pesos por día de retraso
            dias_retraso = (datetime.now() - fecha_prestamo).days - 7  # Suponiendo un período de préstamo de 7 días
            if dias_retraso > 0:    
                multa = dias_retraso * tarifa
                db.ejecutar(
                    "UPDATE usuarios SET saldo_multa = saldo_multa + ? WHERE codigo = ?",
                    (multa, codigo_usuario)
                )
                        
        # Actualizar prestamo para reflejar que el ejemplar ha sido devuelto
        db.ejecutar(
            "UPDATE prestamos SET fecha_devolucion = CURRENT_TIMESTAMP WHERE codigo_ejemplar = ? AND codigo_usuario = ?",
            (codigo_ejemplar, codigo_usuario)
        )
        
        
''' 5.	Reportes y consultas
El personal bibliotecario debe poder ver:
•	Préstamos activos y vencidos.
•	Libros más prestados por periodo.
•	Usuarios con más préstamos.
•	Inventario por estado (disponibles, prestados, perdidos).
'''

def obtener_prestamos_activos_y_vencidos():
    with crear_db() as db:
        prestamos = db.consultar(
            "SELECT * FROM prestamos WHERE fecha_devolucion IS NULL"
        )
        vencidos = []
        for prestamo in prestamos:
            fecha_prestamo = prestamo['fecha_prestamo']
            dias_transcurridos = (datetime.now() - fecha_prestamo).days
            if dias_transcurridos > 7:  # Suponiendo un período de préstamo de 7 días
                vencidos.append(prestamo)
        return {'activos': prestamos, 'vencidos': vencidos}
    
def obtener_libros_mas_prestados_por_periodo(fecha_inicio, fecha_fin):
    with crear_db() as db:
        return db.consultar(
            "SELECT codigo_libro, COUNT(*) AS cantidad_prestamos "
            "FROM prestamos "
            "WHERE fecha_prestamo BETWEEN ? AND ? "
            "GROUP BY codigo_libro "
            "ORDER BY cantidad_prestamos DESC",
            (fecha_inicio, fecha_fin)
        )
        
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
    with crear_db() as db:
        prestamos = db.consultar(
            "SELECT * FROM prestamos WHERE fecha_devolucion IS NULL"
        )
        proximos_a_vencer = []
        for prestamo in prestamos:
            fecha_prestamo = prestamo['fecha_prestamo']
            dias_transcurridos = (datetime.now() - fecha_prestamo).days
            if 5 <= dias_transcurridos <= 7:  # Suponiendo un período de préstamo de 7 días
                proximos_a_vencer.append(prestamo)
        return proximos_a_vencer

def obtener_prestamos_vencidos():
    with crear_db() as db:
        prestamos = db.consultar(
            "SELECT * FROM prestamos WHERE fecha_devolucion IS NULL"
        )
        vencidos = []
        for prestamo in prestamos:
            fecha_prestamo = prestamo['fecha_prestamo']
            dias_transcurridos = (datetime.now() - fecha_prestamo).days
            if dias_transcurridos > 7:  # Suponiendo un período de préstamo de 7 días
                vencidos.append(prestamo)
        return vencidos
    
'''Debe existir un usuario administrador o bibliotecario que se encargara de realizar la aprobación del préstamo y la devolución del libro.'''

def obtener_usuarios_administradores():
    with crear_db() as db:
        return db.consultar(
            "SELECT * FROM usuarios WHERE rol = 'administrador' OR rol = 'bibliotecario'"
        )
        
'''El usuario busca el libro y solicita el préstamo el cual debe ser aprobado por el administrador.'''

def solicitar_prestamo(codigo_ejemplar, codigo_usuario):
    with crear_db() as db:
        # Verificar si el ejemplar está disponible
        ejemplar = db.consultar(
            "SELECT estado FROM ejemplares WHERE codigo = ?",
            (codigo_ejemplar,)
        )
        if not ejemplar or ejemplar[0]['estado'] != 'disponible':
            raise ValueError("El ejemplar no está disponible para préstamo.")
        
        # Registrar la solicitud de préstamo (pendiente de aprobación)
        db.ejecutar(
            "INSERT INTO prestamos (codigo_ejemplar, codigo_usuario, fecha_prestamo, estado) "
            "VALUES (?, ?, CURRENT_TIMESTAMP, 'pendiente')",
            (codigo_ejemplar, codigo_usuario)
        )
        
def aprobar_prestamo(codigo_prestamo):
    with crear_db() as db:
        # Actualizar el estado del préstamo a aprobado
        db.ejecutar(
            "UPDATE prestamos SET estado = 'aprobado' WHERE codigo = ?",
            (codigo_prestamo,)
        )
        
        # Actualizar el estado del ejemplar a prestado
        prestamo = db.consultar(
            "SELECT codigo_ejemplar FROM prestamos WHERE codigo = ?",
            (codigo_prestamo,)
        )
        if prestamo:
            codigo_ejemplar = prestamo[0]['codigo_ejemplar']
            db.ejecutar(
                "UPDATE ejemplares SET estado = 'prestado' WHERE codigo = ?",
                (codigo_ejemplar,)
            )
            
def rechazar_prestamo(codigo_prestamo):
    with crear_db() as db:
        # Actualizar el estado del préstamo a rechazado
        db.ejecutar(
            "UPDATE prestamos SET estado = 'rechazado' WHERE codigo = ?",
            (codigo_prestamo,)
        )
        
def obtener_prestamos_pendientes():
    with crear_db() as db:
        return db.consultar(
            "SELECT * FROM prestamos WHERE estado = 'pendiente'"
        )
        
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

def autenticar_usuario(codigo, correo):
    with crear_db() as db:
        usuario = db.consultar(
            # ¡Cambio vital: Ahora SQL busca la columna 'correo' real!
            "SELECT * FROM usuarios WHERE codigo = ? AND correo = ?",
            (codigo, correo)
        )
        if usuario:
            return usuario[0]  # Retornamos el diccionario con los datos del usuario
        else:
            return None  # Autenticación fallida
            
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
    from db import crear_db # Aseguramos la importación
    with crear_db() as db:
        # Usamos JOIN para unir la información del libro con la disponibilidad de su ejemplar
        return db.consultar("""
            SELECT 
                l.isbn, 
                l.titulo, 
                'Ingeniería / Tecnología' AS categoria, 
                e.estado,
                CONCAT('https://covers.openlibrary.org/b/isbn/', l.isbn, '-L.jpg') AS imagen
            FROM libros l
            JOIN ejemplares e ON l.isbn = e.isbn
            GROUP BY l.isbn, e.estado
        """)
        
        