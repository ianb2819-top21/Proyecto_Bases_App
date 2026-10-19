aplicación de gestión de información y consultoria
# Proyecto BiblioUninorte 📚

## Instrucciones de Instalación para Calificación

1. **Base de Datos:** Abra MySQL Workbench y ejecute el script `Biblioteca_Final.sql` incluido en esta carpeta para generar la estructura y los datos de prueba.
2. **Variables de Entorno:** Copie el archivo `.env.example`, renómbrelo a `.env` (en la raíz del proyecto) y coloque su contraseña local de MySQL en las variables `DB_PASS` y `DATABASE_URL`.
3. **Dependencias:** Ejecute `pip install flask pymysql python-dotenv` en su terminal.
4. **Ejecución:** Inicie el servidor con `py app.py`.

## Registro desde el inicio de sesión

En la pantalla de login, pulse **Crear cuenta** y seleccione **Estudiante** o
**Docente**. Complete el código institucional, nombre, correo e identificación;
la carrera es opcional. La cuenta se crea activa. Después, inicie sesión con el
código institucional y la identificación como clave de acceso, siguiendo el
mismo mecanismo de autenticación de las cuentas existentes.

No se requieren cambios en el esquema de la base de datos. El registro valida
los campos obligatorios, las longitudes y el correo, y avisa si el código ya existe.

Para ejecutar las pruebas de registro sin modificar MySQL:
`py -m unittest discover -s tests -v`.

## Usuarios de Prueba Disponibles:
* **Estudiante:** Código: `U001` | Correo: `maria@correo.com`
* **Administrador:** Código: `A001` | Correo: `admin@biblioteca.com`
