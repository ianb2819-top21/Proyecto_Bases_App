from flask import Flask, render_template, session, redirect, url_for
import connection # Tu archivo de lógica de negocio

app = Flask(__name__)
app.secret_key = "clave_secreta_biblioteca_uninorte"

@app.route('/')
def catalogo():
    # Simulador de rol
    if 'rol' not in session:
        session['rol'] = 'estudiante'
        session['nombre'] = 'Usuario de Prueba'

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

@app.route('/cambiar-rol/<nuevo_rol>')
def cambiar_rol(nuevo_rol):
    Roles_validos = ['estudiante', 'docente', 'bibliotecario', 'administrador']
    if nuevo_rol in Roles_validos:
        session['rol'] = nuevo_rol
        session['nombre'] = f"Modo: {nuevo_rol.capitalize()}"
    return redirect(url_for('catalogo'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)