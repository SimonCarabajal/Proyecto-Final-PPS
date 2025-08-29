# db.py
import os
import sys
import sqlite3

DB_FILENAME = "biblioteca.db"

def get_db_dir() -> str:

    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)

    return os.path.dirname(os.path.abspath(__file__))

def get_db_path() -> str:
    return os.path.join(get_db_dir(), DB_FILENAME)

def conexion():
    return sqlite3.connect(get_db_path())

def crear_base_datos():
    conn = conexion()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS libros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            autor TEXT NOT NULL,
            anio INTEGER,
            carrera TEXT,
            ubicacion TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prestamos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            libro_id INTEGER NOT NULL,
            nombre_usuario TEXT NOT NULL,
            fecha_prestamo TEXT NOT NULL,  -- YYYY-MM-DD
            fecha_limite   TEXT NOT NULL,  -- YYYY-MM-DD
            devuelto       INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (libro_id) REFERENCES libros(id)
        )
    """)
    conn.commit()
    conn.close()
