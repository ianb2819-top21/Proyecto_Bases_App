import os
from abc import ABC, abstractmethod
from contextlib import contextmanager
from urllib.parse import urlparse

from dotenv import load_dotenv


# 1. INTERFAZ COMÚN
class BaseDatos(ABC):
    _en_transaccion = False

    @abstractmethod
    def consultar(self, sql, params=()):
        """SELECT: devuelve una lista de diccionarios."""

    @abstractmethod
    def ejecutar(self, sql, params=()):
        """INSERT/UPDATE/DELETE: devuelve filas afectadas."""

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
        """Hace commit solo si NO estamos dentro de una transacción."""
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
        
      
class MySQLDB(BaseDatos):
    def __init__(self, url):
        import pymysql
        from pymysql.cursors import DictCursor
        
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
            host=u.hostname,
            port=u.port or 3306,
            user=u.username,
            password=u.password,
            database=nombre_bd,      # Seleccionamos la base de datos
            charset="utf8mb4",
            cursorclass=DictCursor   # Obliga a MySQL a devolver diccionarios
        )

    def consultar(self, sql, params=()):
        with self.conn.cursor() as cur:
            # Aquí funciona el traductor mágico de tu compañero
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
    load_dotenv()
    url = url or os.getenv("DATABASE_URL")
    return MySQLDB(url)