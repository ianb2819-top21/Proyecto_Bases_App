import os
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dotenv import load_dotenv
import pymysql
from pymysql.cursors import DictCursor

# 1. INTERFAZ COMÚN
class BaseDatos(ABC):
    _en_transaccion = False

    @abstractmethod
    def consultar(self, sql, params=()):
        pass

    @abstractmethod
    def ejecutar(self, sql, params=()):
        pass

    @abstractmethod
    def cerrar(self):
        pass

    @abstractmethod
    def _commit(self):
        pass

    @abstractmethod
    def _rollback(self):
        pass

    def _confirmar(self):
        if not self._en_transaccion:
            self._commit()

    @contextmanager
    def transaccion(self):
        if self._en_transaccion:
            raise RuntimeError("Ya hay una transacción activa")
        self._en_transaccion = True
        try:
            yield self
            self._commit()
        except Exception:
            self._rollback()
            raise
        finally:
            self._en_transaccion = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cerrar()

# 2. MOTOR MYSQL (SIN URLPARSE)
class MySQLDB(BaseDatos):
    def __init__(self, url):
        import pymysql
        from pymysql.cursors import DictCursor
        
        if isinstance(url, bytes):
            url = url.decode("utf-8")

        u = urlparse(url)
        nombre_bd = u.path.lstrip("/")
    
        # 1. CONEXIÓN TEMPORAL: Solo para ver si la BD existe y crearla
        conn_temp = pymysql.connect(
            host=u.hostname,
            port=u.port or 3306,
            user=u.username,
            password=u.password,
            charset="utf8mb4",
            autocommit=True,
        )
        try:
            with conn_temp.cursor() as cur:
                cur.execute("SHOW DATABASES LIKE %s", (nombre_bd,))
                if not cur.fetchone():
                    # Si no existe, ejecuta el archivo SQL
                    try:
                        script = SCHEMA_PATH.read_text(encoding="utf-8")
                        for sentencia in _sentencias(script):
                            cur.execute(sentencia)
                    except Exception:
                        cur.execute(f"DROP DATABASE IF EXISTS `{nombre_bd}`") 
                        raise
        finally:
            conn_temp.close() # Cerramos el instalador
            
        # 2. CONEXIÓN PERMANENTE: Esta es la que usará tu aplicación viva
        # CRÍTICO: Aquí usamos 'self.conn' y agregamos el 'DictCursor'
        self.conn = pymysql.connect(
            host=os.getenv("DB_HOST"),
            port=3306,
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME"),
            charset="utf8mb4",
            cursorclass=DictCursor,
            ssl={} # El escudo que evita el error de los bytes
        )

    def consultar(self, sql, params=()):
        with self.conn.cursor() as cur:
            cur.execute(sql.replace("?", "%s"), params)
            filas = list(cur.fetchall())
        self._confirmar()
        return filas

    def ejecutar(self, sql, params=()):
        with self.conn.cursor() as cur:
            cur.execute(sql.replace("?", "%s"), params)
            filas = cur.rowcount
        self._confirmar()
        return filas

    def _commit(self):
        self.conn.commit()

    def _rollback(self):
        self.conn.rollback()

    def cerrar(self):
        self.conn.close()
        
def crear_db(url=None):
    import traceback

    try:
        load_dotenv()
        url = url or os.getenv("DATABASE_URL")

        if not url:
            raise ValueError("No se encontró DATABASE_URL en el archivo .env")

        print("Intentando conectar con MySQL...")

        db = MySQLDB(url)

        print("Conexión con MySQL exitosa")
        return db

    except Exception as e:
        print(f"ERROR AL CONECTAR CON MYSQL: {e}")
        traceback.print_exc()
        raise
