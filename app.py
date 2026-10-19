import os
import secrets
from functools import wraps
from flask import Flask, render_template, session, redirect, url_for, abort, request, flash
import connection
import admin_ops

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or os.urandom(32)
ROLES_STAFF = {'administrador', 'bibliotecario'}

@app.context_processor
def csrf_helpers():
    def token():
        if '_csrf' not in session:
            session['_csrf'] = secrets.token_urlsafe(32)
        return session['_csrf']
    return {'csrf_token': token}

@app.before_request
def verificar_csrf():
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        esperado = session.get('_csrf')
        recibido = request.form.get('_csrf')
        if not esperado or not recibido or not secrets.compare_digest(esperado, recibido):
            abort(400, description='Formulario vencido o token de seguridad ausente. Recarga la página.')


def requiere_login(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('codigo') or not session.get('rol'):
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper


def requiere_roles(*roles):
    def decorar(func):
        @wraps(func)
        @requiere_login
        def wrapper(*args, **kwargs):
            if session['rol'] not in roles:
                abort(403)
            return func(*args, **kwargs)
        return wrapper
    return decorar


@app.route('/')
@requiere_login
def catalogo():
    try:
        libros = connection.obtener_catalogo_web()
    except Exception:
        app.logger.exception('No se pudo cargar catálogo')
        return render_template('catalogo.html', libros=[], error='No se pudo cargar el catálogo.'), 503
    return render_template('catalogo.html', libros=libros, error=None)


@app.route('/mis-prestamos')
@requiere_roles('estudiante', 'docente')
def mis_prestamos():
    try:
        prestamos = connection.consultar_historial_prestamos_por_usuario(session['codigo'])
    except Exception:
        app.logger.exception('Error consultando préstamos')
        return render_template('mis_prestamos.html', prestamos=[], resumen=None,
                               error='No se pudo cargar el historial.'), 503
    resumen = {'activos': sum(p['fec_devolucion'] is None and
                              str(p['estado']).lower() in ('activo','aprobado') for p in prestamos),
               'vencidos': sum(p['estado_visual'] == 'Vencido' for p in prestamos),
               'multa_registrada': sum(p['sancion'] for p in prestamos),
               'multa_total': sum(p['multa_calculada'] for p in prestamos)}
    return render_template('mis_prestamos.html', prestamos=prestamos, resumen=resumen, error=None)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', error=None)
    codigo = request.form.get('codigo','').strip()
    identificacion = request.form.get('identificacion','').strip()
    try:
        usuario = connection.autenticar_usuario(codigo, identificacion)
    except Exception:
        app.logger.exception('Error autenticando')
        return render_template('login.html', error='No fue posible iniciar sesión.'), 503
    if not usuario:
        return render_template('login.html', error='Credenciales incorrectas.'), 401
    if str(usuario.get('estado') or '').strip().lower() != 'activo':
        return render_template('login.html', error='Cuenta no activa.'), 403
    rol = str(usuario.get('rol') or '').strip().lower()
    if rol not in {'estudiante', 'docente', 'bibliotecario', 'administrador'}:
        return render_template('login.html', error='Rol inválido.'), 403
    session.clear()
    session.update(codigo=usuario['codigo'], nombre=usuario['nombres'], rol=rol)
    return redirect(url_for('catalogo'))


@app.route('/logout', methods=['POST'])
@requiere_login
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/panel-admin')
@requiere_roles(*ROLES_STAFF)
def panel_admin():
    try:
        pendientes = connection.obtener_prestamos_pendientes()
        inventario = connection.obtener_inventario_admin()
    except Exception:
        app.logger.exception('Error panel admin')
        return render_template('admin_panel.html', pendientes=[], inventario=[],
                               error='No fue posible cargar el panel.'), 503
    return render_template('admin_panel.html', pendientes=pendientes, inventario=inventario, error=None)


@app.route('/panel-admin/aprobar', methods=['POST'])
@requiere_roles(*ROLES_STAFF)
def aprobar():
    try:
        connection.aprobar_prestamo(int(request.form['id_ejemplar']),
                                    request.form['codigo_usuario'].strip())
        flash('Préstamo aprobado correctamente.', 'ok')
    except (ValueError, KeyError) as e:
        flash(str(e), 'error')
    except Exception:
        app.logger.exception('Error aprobando')
        flash('No se pudo aprobar el préstamo.', 'error')
    return redirect(url_for('panel_admin'))


@app.route('/panel-admin/devolver', methods=['POST'])
@requiere_roles(*ROLES_STAFF)
def devolver():
    try:
        r = connection.registrar_devolucion(int(request.form['id_ejemplar']),
                                           request.form.get('observaciones','').strip())
        flash(f"Devolución registrada. Retraso: {r['dias_retraso']} día(s). "
              f"Multa: ${r['multa']:,.0f}.", 'warn' if r['multa'] else 'ok')
    except (ValueError, KeyError) as e:
        flash(str(e), 'error')
    except Exception:
        app.logger.exception('Error devolviendo')
        flash('No se pudo registrar la devolución.', 'error')
    return redirect(url_for('panel_admin'))


@app.route('/solicitar/<int:id_ejemplar>', methods=['POST'])
@requiere_roles('estudiante','docente')
def solicitar(id_ejemplar):
    try:
        connection.solicitar_prestamo(id_ejemplar, session['codigo'])
        flash('Solicitud enviada. Espera la aprobación del personal.', 'ok')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception:
        app.logger.exception('Error solicitando préstamo')
        flash('No se pudo registrar la solicitud.', 'error')
    return redirect(url_for('catalogo'))


@app.route('/reportes')
@requiere_roles(*ROLES_STAFF)
def reportes():
    try:
        estados, populares, activos = admin_ops.resumen_reportes()
    except Exception:
        app.logger.exception('Error reportes')
        abort(503)
    return render_template('reportes.html', estados=estados, populares=populares, activos=activos)


@app.route('/gestion')
@requiere_roles('administrador')
def gestion():
    try:
        return render_template('gestion.html', libros=admin_ops.listar_libros(),
                               usuarios=admin_ops.listar_usuarios())
    except Exception:
        app.logger.exception('Error en gestión')
        abort(503)


@app.route('/libros/nuevo', methods=['GET','POST'])
@app.route('/libros/<isbn>/editar', methods=['GET','POST'])
@requiere_roles('administrador')
def libro_form(isbn=None):
    nuevo = isbn is None
    if request.method == 'GET':
        libro = {} if nuevo else admin_ops.obtener_libro(isbn)
        return render_template('libro_form.html', libro=libro, nuevo=nuevo)
    datos = request.form
    try:
        admin_ops.guardar_libro(isbn if not nuevo else datos.get('isbn',''),
            datos.get('titulo',''), datos.get('editorial',''), datos.get('anio',''),
            datos.get('descripcion',''), datos.get('autores',''),
            datos.get('categorias',''), nuevo)
        flash('Libro guardado correctamente.', 'ok')
        return redirect(url_for('gestion'))
    except ValueError as e:
        flash(str(e), 'error')
    except Exception:
        app.logger.exception('Error guardando libro')
        flash('No se pudo guardar el libro. Verifica ISBN duplicado y los datos.', 'error')
    libro = dict(datos)
    if not nuevo: libro['isbn'] = isbn
    return render_template('libro_form.html', libro=libro, nuevo=nuevo), 400


@app.route('/libros/<isbn>/ejemplares')
@requiere_roles('administrador')
def gestionar_ejemplares(isbn):
    try:
        libro, ejemplares = admin_ops.detalle_ejemplares(isbn)
    except ValueError:
        abort(404)
    except Exception:
        app.logger.exception('Error consultando ejemplares')
        abort(503)
    return render_template('ejemplares_form.html', libro=libro, ejemplares=ejemplares,
                           estados=admin_ops.ESTADOS_EDITABLES)


@app.route('/libros/<isbn>/ejemplares/cantidad', methods=['POST'])
@requiere_roles('administrador')
def editar_cantidad_ejemplares(isbn):
    try:
        admin_ops.ajustar_cantidad_ejemplares(isbn, request.form.get('cantidad', ''))
        flash('Cantidad de ejemplares actualizada.', 'ok')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception:
        app.logger.exception('Error ajustando cantidad')
        flash('No fue posible actualizar la cantidad.', 'error')
    return redirect(url_for('gestionar_ejemplares', isbn=isbn))


@app.route('/libros/<isbn>/ejemplares/<int:id_ejemplar>/estado', methods=['POST'])
@requiere_roles('administrador')
def editar_estado_ejemplar(isbn, id_ejemplar):
    try:
        admin_ops.modificar_estado_ejemplar(isbn, id_ejemplar, request.form.get('estado', ''))
        flash('Estado actualizado.', 'ok')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception:
        app.logger.exception('Error actualizando estado')
        flash('No fue posible actualizar el estado.', 'error')
    return redirect(url_for('gestionar_ejemplares', isbn=isbn))


@app.route('/libros/<isbn>/borrar', methods=['POST'])
@requiere_roles('administrador')
def borrar_libro(isbn):
    try:
        admin_ops.eliminar_libro(isbn)
        flash('Libro eliminado.', 'ok')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception:
        app.logger.exception('Error borrando libro')
        flash('No se pudo eliminar el libro.', 'error')
    return redirect(url_for('gestion'))


@app.route('/usuarios/nuevo', methods=['POST'])
@requiere_roles('administrador')
def crear_usuario():
    datos = request.form
    rol = datos.get('rol','').lower()
    if rol not in {'estudiante','docente','bibliotecario','administrador'}:
        flash('Rol inválido.', 'error')
    else:
        try:
            connection.registrar_usuario(datos.get('codigo','').strip(),
                datos.get('identificacion','').strip(), datos.get('nombres','').strip(),
                datos.get('correo','').strip(), rol, datos.get('carrera') or None)
            flash('Usuario creado.', 'ok')
        except Exception:
            app.logger.exception('Error creando usuario')
            flash('No se pudo crear. Comprueba campos obligatorios y código único.', 'error')
    return redirect(url_for('gestion'))


@app.route('/usuarios/<codigo>/estado', methods=['POST'])
@requiere_roles('administrador')
def estado_usuario(codigo):
    try:
        admin_ops.cambiar_estado_usuario(codigo, request.form['estado'], session['codigo'])
        flash('Estado del usuario actualizado.', 'ok')
    except (KeyError, ValueError) as e:
        flash(str(e), 'error')
    except Exception:
        app.logger.exception('Error cambiando estado')
        flash('No se pudo actualizar el usuario.', 'error')
    return redirect(url_for('gestion'))


if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG') == '1', port=5000)
