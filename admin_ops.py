'Operaciones administrativas ajustadas al esquema Biblioteca_LAB.'
from db import crear_db


def listar_usuarios():
    with crear_db() as db:
        return db.consultar('SELECT codigo, nombres, correo, rol, carrera, estado FROM usuarios ORDER BY codigo')


def cambiar_estado_usuario(codigo, estado, actor):
    if codigo == actor and estado.lower() != 'activo':
        raise ValueError('No puedes bloquear tu propia cuenta.')
    if estado.lower() not in ('activo', 'bloqueado'):
        raise ValueError('Estado inválido.')
    with crear_db() as db:
        if db.ejecutar('UPDATE usuarios SET estado = ? WHERE codigo = ?', (estado, codigo)) != 1:
            raise ValueError('No existe ese usuario.')


def listar_libros():
    with crear_db() as db:
        return db.consultar('''
            SELECT l.*, (SELECT GROUP_CONCAT(autor SEPARATOR ', ') FROM libro_autor
                        WHERE isbn = l.isbn) AS autores,
                   (SELECT GROUP_CONCAT(categoria SEPARATOR ', ') FROM libro_categoria
                        WHERE isbn = l.isbn) AS categorias
            FROM libros l ORDER BY l.titulo
        ''')


def obtener_libro(isbn):
    with crear_db() as db:
        rows = db.consultar('SELECT * FROM libros WHERE isbn = ?', (isbn,))
        if not rows:
            raise ValueError('Libro no encontrado.')
        item = rows[0]
        item['autores'] = ', '.join(r['autor'] for r in db.consultar(
            'SELECT autor FROM libro_autor WHERE isbn = ?', (isbn,)))
        item['categorias'] = ', '.join(r['categoria'] for r in db.consultar(
            'SELECT categoria FROM libro_categoria WHERE isbn = ?', (isbn,)))
        return item


def guardar_libro(isbn, titulo, editorial, anio, descripcion, autores, categorias, nuevo):
    isbn, titulo = isbn.strip(), titulo.strip()
    if not isbn or not titulo:
        raise ValueError('ISBN y título son obligatorios.')
    try:
        anio = int(anio) if anio else None
    except ValueError:
        raise ValueError('El año debe ser numérico.')
    if anio is not None and not 0 < anio <= 9999:
        raise ValueError('Año inválido.')
    autores = list(dict.fromkeys(x.strip() for x in autores.split(',') if x.strip()))
    categorias = list(dict.fromkeys(x.strip() for x in categorias.split(',') if x.strip()))
    with crear_db() as db:
        with db.transaccion():
            if nuevo:
                db.ejecutar('''INSERT INTO libros (isbn, titulo, editorial, año, descripcion)
                    VALUES (?, ?, ?, ?, ?)''', (isbn, titulo, editorial, anio, descripcion))
            else:
                if db.ejecutar('''UPDATE libros SET titulo = ?, editorial = ?, año = ?, descripcion = ?
                                 WHERE isbn = ?''', (titulo, editorial, anio, descripcion, isbn)) == 0:
                    # MySQL devuelve 0 si los valores no cambian; verificamos existencia.
                    if not db.consultar('SELECT isbn FROM libros WHERE isbn = ?', (isbn,)):
                        raise ValueError('Libro no encontrado.')
                db.ejecutar('DELETE FROM libro_autor WHERE isbn = ?', (isbn,))
                db.ejecutar('DELETE FROM libro_categoria WHERE isbn = ?', (isbn,))
            for autor in autores:
                db.ejecutar('INSERT INTO libro_autor (isbn, autor) VALUES (?, ?)', (isbn, autor))
            for categoria in categorias:
                db.ejecutar('INSERT INTO libro_categoria (isbn, categoria) VALUES (?, ?)', (isbn, categoria))


def eliminar_libro(isbn):
    with crear_db() as db:
        with db.transaccion():
            if db.consultar('SELECT id_ejemplar FROM ejemplares WHERE isbn = ? LIMIT 1', (isbn,)):
                raise ValueError('No se puede borrar un libro con ejemplares. Conserva su historial.')
            db.ejecutar('DELETE FROM libro_autor WHERE isbn = ?', (isbn,))
            db.ejecutar('DELETE FROM libro_categoria WHERE isbn = ?', (isbn,))
            if db.ejecutar('DELETE FROM libros WHERE isbn = ?', (isbn,)) != 1:
                raise ValueError('Libro no encontrado.')


def resumen_reportes():
    with crear_db() as db:
        por_estado = db.consultar('''SELECT estado, COUNT(*) AS total FROM ejemplares
                                    GROUP BY estado ORDER BY estado''')
        top = db.consultar('''SELECT l.titulo, l.isbn, COUNT(*) AS total
            FROM prestamos p JOIN ejemplares e ON e.id_ejemplar = p.id_ejemplar
            JOIN libros l ON l.isbn = e.isbn
            WHERE LOWER(p.estado) <> 'rechazado'
            GROUP BY l.titulo, l.isbn ORDER BY total DESC LIMIT 10''')
        activos = db.consultar('''SELECT p.*, l.titulo, u.nombres FROM prestamos p
            JOIN ejemplares e ON e.id_ejemplar = p.id_ejemplar
            JOIN libros l ON l.isbn = e.isbn
            JOIN usuarios u ON u.codigo = p.codigo_usuario
            WHERE p.fec_devolucion IS NULL AND LOWER(p.estado) IN ('aprobado','activo')
            ORDER BY p.fec_vencimiento''')
    from datetime import date, datetime
    hoy = date.today()
    for p in activos:
        vence = p['fec_vencimiento']
        if isinstance(vence, datetime): vence = vence.date()
        if isinstance(vence, str): vence = date.fromisoformat(vence)
        p['vencido'] = bool(vence and vence < hoy)
    return por_estado, top, activos


# Los estados pertenecen a ejemplares, no a la tabla libros.
ESTADOS_EDITABLES = ('Disponible', 'Mantenimiento', 'Dañado', 'Perdido')


def detalle_ejemplares(isbn):
    with crear_db() as db:
        libros = db.consultar('SELECT isbn, titulo FROM libros WHERE isbn = ?', (isbn,))
        if not libros:
            raise ValueError('El libro no existe.')
        ejemplares = db.consultar('''
            SELECT e.id_ejemplar, e.sala, e.estante, e.estado,
              EXISTS(SELECT 1 FROM prestamos p
                WHERE p.id_ejemplar = e.id_ejemplar
                  AND p.fec_devolucion IS NULL
                  AND LOWER(p.estado) IN ('pendiente', 'aprobado', 'activo')) AS comprometido,
              EXISTS(SELECT 1 FROM prestamos p
                WHERE p.id_ejemplar = e.id_ejemplar) AS tiene_historial
            FROM ejemplares e WHERE e.isbn = ? ORDER BY e.id_ejemplar
        ''', (isbn,))
    return libros[0], ejemplares


def ajustar_cantidad_ejemplares(isbn, cantidad):
    if isinstance(cantidad, str) and not cantidad.isdecimal():
        raise ValueError('La cantidad debe ser un número entero no negativo.')
    cantidad = int(cantidad)
    if cantidad < 0 or cantidad > 10000:
        raise ValueError('La cantidad debe estar entre 0 y 10000.')
    with crear_db() as db:
        with db.transaccion():
            libros = db.consultar('SELECT isbn FROM libros WHERE isbn = ? FOR UPDATE', (isbn,))
            if not libros:
                raise ValueError('Libro no encontrado.')
            ejemplares = db.consultar('SELECT id_ejemplar, estado FROM ejemplares WHERE isbn = ? ORDER BY id_ejemplar FOR UPDATE', (isbn,))
            actuales = len(ejemplares)
            if cantidad > actuales:
                for _ in range(cantidad - actuales):
                    db.ejecutar("INSERT INTO ejemplares (isbn, estado) VALUES (?, 'Disponible')", (isbn,))
            elif cantidad < actuales:
                quitar = actuales - cantidad
                # Nunca se borran ejemplares con historial de préstamos, ni siquiera devueltos.
                eliminables = db.consultar('''
                    SELECT e.id_ejemplar FROM ejemplares e
                    WHERE e.isbn = ? AND LOWER(e.estado) = 'disponible'
                    AND NOT EXISTS (SELECT 1 FROM prestamos p WHERE p.id_ejemplar = e.id_ejemplar)
                    ORDER BY e.id_ejemplar DESC LIMIT ?
                ''', (isbn, quitar))
                if len(eliminables) != quitar:
                    raise ValueError('No es posible reducir esa cantidad: solo pueden eliminarse ejemplares disponibles sin historial de préstamos.')
                for item in eliminables:
                    db.ejecutar('DELETE FROM ejemplares WHERE id_ejemplar = ?', (item['id_ejemplar'],))
    return cantidad


def modificar_estado_ejemplar(isbn, id_ejemplar, estado):
    if estado not in ESTADOS_EDITABLES:
        raise ValueError('Estado inválido. El estado Prestado se establece al aprobar un préstamo.')
    with crear_db() as db:
        with db.transaccion():
            filas = db.consultar('''SELECT id_ejemplar, estado FROM ejemplares
                WHERE isbn = ? AND id_ejemplar = ? FOR UPDATE''', (isbn, id_ejemplar))
            if not filas:
                raise ValueError('Ejemplar no encontrado.')
            activo = db.consultar('''SELECT 1 FROM prestamos
                WHERE id_ejemplar = ? AND fec_devolucion IS NULL
                AND LOWER(estado) IN ('pendiente', 'aprobado', 'activo') LIMIT 1''', (id_ejemplar,))
            if activo or str(filas[0]['estado']).strip().lower() == 'prestado':
                raise ValueError('Este ejemplar tiene un préstamo/solicitud vigente o figura como Prestado. Gestiona primero su devolución.')
            db.ejecutar('UPDATE ejemplares SET estado = ? WHERE id_ejemplar = ?', (estado, id_ejemplar))
