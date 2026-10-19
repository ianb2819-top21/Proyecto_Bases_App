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
    def __init__(self):
        # Conexión directa y segura usando variables separadas del .env
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

# 3. PUENTE DE CONEXIÓN
def crear_db():
    load_dotenv()
    return MySQLDB()