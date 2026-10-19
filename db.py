import os
import traceback
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dotenv import load_dotenv
import pymysql
from pymysql.cursors import DictCursor
from urllib.parse import urlparse

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

# 2. MOTOR MYSQL LOCAL (LIMPIO)
class MySQLDB(BaseDatos):
    def __init__(self, url):
        # Desarmamos tu DATABASE_URL para extraer el root y la contraseña
        if isinstance(url, bytes):
            url = url.decode("utf-8")

        u = urlparse(url)
        nombre_bd = u.path.lstrip("/")

        # Conexión directa a tu MySQL Workbench local
        self.conn = pymysql.connect(
            host=u.hostname or "localhost",
            port=u.port or 3306,
            user=u.username or "root",
            password=u.password or "",
            database=nombre_bd,
            charset="utf8mb4",
            cursorclass=DictCursor
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

# 3. PUENTE DE CONEXIÓN
def crear_db(url=None):
    try:
        load_dotenv()
        url = url or os.getenv("DATABASE_URL")
        
        if not url:
            raise ValueError("No se encontró DATABASE_URL en el archivo .env")

        print("Intentando conectar con MySQL Local...")
        db = MySQLDB(url)
        print("Conexión con MySQL Local exitosa")
        return db

    except Exception as e:
        print(f"ERROR AL CONECTAR CON MYSQL: {e}")
        traceback.print_exc()
        raise