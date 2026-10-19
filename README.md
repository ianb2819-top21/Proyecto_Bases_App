aplicación de gestión de información y consultoria
# Proyecto BiblioUninorte 📚

## Instrucciones de Instalación para Calificación

1. **Base de Datos:** Abra MySQL Workbench y ejecute el script `Biblioteca_Final.sql` incluido en esta carpeta para generar la estructura y los datos de prueba.
2. **Variables de Entorno:** Copie el archivo `.env.example`, renómbrelo a `.env` (en la raíz del proyecto) y coloque su contraseña local de MySQL en las variables `DB_PASS` y `DATABASE_URL`.
3. **Dependencias:** Ejecute `pip install flask pymysql python-dotenv` en su terminal.
4. **Ejecución:** Inicie el servidor con `py app.py`.

## Usuarios de Prueba Disponibles:
* **Estudiante:** Código: `U001` | Correo: `maria@correo.com`
* **Administrador:** Código: `A001` | Correo: `admin@biblioteca.com`
