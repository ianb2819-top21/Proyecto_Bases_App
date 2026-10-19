from flask import (Flask, render_template, session, redirect, url_for, abort,
                   request, flash)
import connection # Tu archivo de lógica de negocio

app = Flask(__name__)
app.secret_key = "clave_secreta_biblioteca_uninorte"

@app.route('/')
def catalogo():
    # Simulador de rol
    if 'rol' not in session:
        session['rol'] = 'estudiante'
        session['nombre'] = 'Usuario de Prueba'
        # Solo para la demostración: el SQL incluye al estudiante U001.
        # Reemplazar por el código asignado durante el login real.
        session['codigo'] = 'U001'

    # 🌟 AHORA SÍ: LLAMAMOS A MYSQL
    try:
        # Traemos los libros reales (Clean Code, Effective Java, etc.)
        libros_reales = connection.obtener_catalogo_web()
    except Exception as e:
        import traceback
        print(f"Error conectando a BD: {e}")
        traceback.print_exc()
        libros_reales = [] # Si hay error, enviamos lista vacía para no romper la web

    return render_template('catalogo.html', libros=libros_reales)

@app.route('/mis-prestamos')
def mis_prestamos():
    # El rol visual no sustituye la autenticación en producción.
    if session.get('rol') not in ('estudiante', 'docente'):
        abort(403)

    codigo = session.get('codigo') or 'U001'
    if not codigo:
        return redirect(url_for('catalogo'))

    try:
        prestamos = connection.consultar_historial_prestamos_por_usuario(codigo)

        print("Archivo utilizado:", connection.__file__)
        print("Campos devueltos:", [list(p.keys()) for p in prestamos])
    except Exception:
        app.logger.exception('No se pudieron consultar los préstamos')
        return render_template('mis_prestamos.html', prestamos=[], resumen=None,
                               error='No fue posible cargar tus préstamos. Intenta más tarde.'), 503

    activos = sum(p['fec_devolucion'] is None for p in prestamos)
    vencidos = sum(p['estado_visual'] == 'Vencido' for p in prestamos)
    # Se muestra la sanción almacenada; no se calcula dinero sin una política confirmada.
    multa_registrada = sum(p['sancion'] for p in prestamos)
    multa_total = sum(p['multa_calculada'] for p in prestamos)
    resumen = {
    'activos': activos,
    'vencidos': vencidos,
    'multa_registrada': multa_registrada,
    'multa_total': multa_total
    }
    return render_template('mis_prestamos.html', prestamos=prestamos, resumen=resumen,
                           error=None)

@app.route('/cambiar-rol/<nuevo_rol>')
def cambiar_rol(nuevo_rol):
    Roles_validos = ['estudiante', 'docente', 'bibliotecario', 'administrador']
    if nuevo_rol in Roles_validos:
        session['rol'] = nuevo_rol
        session['nombre'] = f"Modo: {nuevo_rol.capitalize()}"
    return redirect(url_for('catalogo'))


# ---------------------------------------------------------------------------
# PANEL DE ADMINISTRACIÓN (solo bibliotecario / administrador)
# ---------------------------------------------------------------------------
ROLES_STAFF = ('bibliotecario', 'administrador')


def _exigir_staff():
    """Candado de seguridad: sin rol de staff -> 403."""
    if session.get('rol') not in ROLES_STAFF:
        abort(403)


@app.route('/panel-admin')
def panel_admin():
    _exigir_staff()
    try:
        pendientes = connection.obtener_prestamos_pendientes()
        inventario = connection.obtener_inventario_admin()
    except Exception:
        app.logger.exception('No se pudo cargar el panel de administración')
        flash('No fue posible cargar los datos del panel.', 'error')
        pendientes, inventario = [], []
    return render_template('admin_panel.html', pendientes=pendientes,
                           inventario=inventario)


@app.route('/panel-admin/aprobar', methods=['POST'])
def aprobar():
    _exigir_staff()
    try:
        connection.aprobar_prestamo(request.form['id_ejemplar'],
                                    request.form['codigo_usuario'])
        flash('Préstamo aprobado.', 'ok')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception:
        app.logger.exception('Error aprobando préstamo')
        flash('No fue posible aprobar el préstamo.', 'error')
    return redirect(url_for('panel_admin'))


@app.route('/panel-admin/devolver', methods=['POST'])
def devolver():
    _exigir_staff()
    try:
        r = connection.registrar_devolucion(request.form['id_ejemplar'],
                                            request.form.get('observaciones', '').strip())
        if r['multa'] > 0:
            flash(f"Devolución registrada con {r['dias_retraso']} día(s) de retraso. "
                  f"Multa: ${r['multa']:,.0f} (usuario {r['codigo_usuario']}).", 'warn')
        else:
            flash('Devolución registrada sin multa.', 'ok')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception:
        app.logger.exception('Error registrando devolución')
        flash('No fue posible registrar la devolución.', 'error')
    return redirect(url_for('panel_admin'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
