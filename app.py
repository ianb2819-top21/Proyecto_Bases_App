# 1. IMPORTACIONES
from flask import Flask, render_template, session, redirect, url_for

# 2. CREACIÓN DE LA APP
app = Flask(__name__)

# 3. LLAVE SECRETA (Obligatoria para usar sesiones)
# Flask encripta la "manilla" del usuario con esta clave para que nadie pueda 
# falsificar su rol desde el navegador.
app.secret_key = "clave_secreta_biblioteca_uninorte"


# 4. DATOS SIMULADOS (Mock Data mientras nos pasan el script SQL)
LIBROS_PRUEBA = [
    {
        "id": 1,
        "titulo": "Cien Años de Soledad",
        "autor": "Gabriel García Márquez",
        "isbn": "978-0307474728",
        "categoria": "Literatura",
        "estado": "disponible",
        "imagen": "https://covers.openlibrary.org/b/id/8228691-L.jpg"
    },
    {
        "id": 2,
        "titulo": "Clean Code",
        "autor": "Robert C. Martin",
        "isbn": "978-0132350884",
        "categoria": "Ingeniería de Software",
        "estado": "prestado",
        "imagen": "https://covers.openlibrary.org/b/id/10543666-L.jpg"
    },
    {
        "id": 3,
        "titulo": "Database System Concepts",
        "autor": "Abraham Silberschatz",
        "isbn": "978-0078022159",
        "categoria": "Bases de Datos",
        "estado": "disponible",
        "imagen": "https://covers.openlibrary.org/b/id/9255566-L.jpg"
    }
]


# 5. RUTA PRINCIPAL (El Catálogo)
@app.route('/')
def catalogo():
    # Si el usuario entra por primera vez y no tiene un rol asignado en su "manilla",
    # le ponemos 'estudiante' por defecto para probar.
    if 'rol' not in session:
        session['rol'] = 'estudiante'
        session['nombre'] = 'Usuario de Prueba'

    # Renderizamos (dibujamos) el archivo catalogo.html y le enviamos la lista de libros
    return render_template('catalogo.html', libros=LIBROS_PRUEBA)


# 6. RUTA PARA CAMBIAR DE ROL (Nuestro simulador rápido)
# El <nuevo_rol> entre signos mayor/menor es una variable que viaja en la URL
@app.route('/cambiar-rol/<nuevo_rol>')
def cambiar_rol(nuevo_rol):
    Roles_validos = ['estudiante', 'docente', 'bibliotecario', 'administrador']
    
    if nuevo_rol in Roles_validos:
        session['rol'] = nuevo_rol
        # Cambiamos el nombre para que se note en pantalla quién somos
        session['nombre'] = f"Modo: {nuevo_rol.capitalize()}"
        
    # redirect(url_for('catalogo')) nos devuelve automáticamente a la página principal ('/')
    return redirect(url_for('catalogo'))


# 7. ENCENDIDO DEL SERVIDOR
if __name__ == '__main__':
    app.run(debug=True, port=5000)