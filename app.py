
from flask import (Flask, render_template, session, redirect, url_for, abort,
                   request, flash)

import connection # Tu archivo de lógica de negocio

app = Flask(__name__)
app.secret_key = "clave_secreta_biblioteca_uninorte"

@app.route('/')
def catalogo():
    if not session.get('codigo') or not session.get('rol'):
        session.clear()
        return redirect(url_for('login'))
        

    try:
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

    codigo = session.get('codigo')

    if not codigo:
        return redirect(url_for('login'))

    try:
        prestamos = connection.consultar_historial_prestamos_por_usuario(codigo)
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


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', error=None)

    codigo = request.form.get('codigo', '').strip()
    identificacion = request.form.get('identificacion', '').strip()

    try:
        usuario = connection.autenticar_usuario(codigo, identificacion)
    except Exception:
        app.logger.exception('Error consultando usuario')
        return render_template(
            'login.html',
            error='No fue posible iniciar sesión.'
        ), 503

    # Verificar credenciales
    if not usuario:
        return render_template(
            'login.html',
            error='Credenciales incorrectas.'
        ), 401

    # Verificar estado del usuario
    if (usuario.get('estado') or '').strip().lower() != 'activo':
        return render_template(
            'login.html',
            error='Tu cuenta no está activa.'
        ), 403

    # Verificar rol
    roles = {
        'estudiante',
        'docente',
        'bibliotecario',
        'administrador'
    }

    rol = (usuario.get('rol') or '').strip().lower()

    if rol not in roles:
        return render_template(
            'login.html',
            error='El usuario no tiene un rol válido.'
        ), 403

    # Crear sesión
    session.clear()
    session['codigo'] = usuario['codigo']
    session['nombre'] = usuario['nombres']
    session['rol'] = rol

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
