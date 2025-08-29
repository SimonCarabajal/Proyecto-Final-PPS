import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import date, timedelta

from db import crear_base_datos, conexion


crear_base_datos()


CARRERAS = [
    "Ingeniería Civil",
    "Ingeniería Electromecánica",
    "Ingeniería Industrial",
    "Ingeniería en Sistemas de Información",
    "Tecnicatura en Programación",
    "Maestría en Inteligencia de Negocios",
    "Maestría en Desarrollo Territorial",
]

UBICACIONES = [
    "Pasillo A", "Pasillo B", "Pasillo C",
    "Sección Historia", "Sección Tecnología", "Sección Literatura",
    "Depósito"
]
root = tk.Tk()
root.title("📚 Inventario de Biblioteca")
root.geometry("1200x650")
root.configure(bg="#f5f5f5")


def _hoy_iso() -> str:
    return date.today().isoformat()


def _parse_iso(s: str) -> date:
    return date.fromisoformat(s)


def _estado_desde_prestamo(f_lim: str | None, devuelto: int | None) -> tuple[str, str]:
    """
    Devuelve (etiqueta_estado, tag_treeview) a partir de fecha_limite y devuelto.
    tag_treeview puede ser '' o 'atrasado' para colorear la fila.
    """
    if f_lim is None or devuelto is None:
        return ("", "")
    if devuelto == 1:
        return ("Sí", "")
    # No devuelto
    try:
        lim = _parse_iso(f_lim)
    except Exception:
        return ("No", "")
    if lim < date.today():
        return ("Atrasado", "atrasado")
    return ("No", "")

def mostrar_libros():
    """Rellena la grilla de Libros con la columna 'Devuelto' calculada del último préstamo."""
    # limpiar
    for item in tree_libros.get_children():
        tree_libros.delete(item)

    conn = conexion()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            l.id, l.titulo, l.autor, l.anio, l.carrera, l.ubicacion,
            (SELECT p.fecha_limite FROM prestamos p
             WHERE p.libro_id = l.id ORDER BY p.id DESC LIMIT 1) AS ultima_fecha_limite,
            (SELECT p.devuelto FROM prestamos p
             WHERE p.libro_id = l.id ORDER BY p.id DESC LIMIT 1) AS ultimo_devuelto
        FROM libros l
        ORDER BY l.id ASC;
    """)
    rows = cur.fetchall()
    conn.close()

    for row in rows:
        (id_libro, titulo, autor, anio, carrera, ubicacion, f_lim, dev) = row
        estado, tag = _estado_desde_prestamo(f_lim, dev)

        valores = (id_libro, titulo, autor, anio if anio is not None else "", carrera or "", ubicacion or "", estado or "")
        tree_libros.insert("", "end", values=valores, tags=(tag,))


    tree_libros.tag_configure("atrasado", background="#ffb3b3")


def mostrar_prestamos():
    """Rellena la grilla de Préstamos con el estado (Devuelto / No devuelto / Atrasado)."""
    for item in tree_prestamos.get_children():
        tree_prestamos.delete(item)

    conn = conexion()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            p.libro_id, l.titulo, p.nombre_usuario, p.fecha_prestamo, p.fecha_limite, p.devuelto
        FROM prestamos p
        JOIN libros l ON l.id = p.libro_id
        ORDER BY p.fecha_prestamo DESC, p.id DESC;
    """)
    rows = cur.fetchall()
    conn.close()

    for libro_id, titulo, usuario, f_prest, f_lim, dev in rows:
        estado, tag = _estado_desde_prestamo(f_lim, dev)
        valores = (libro_id, titulo, usuario, f_prest, f_lim, "Devuelto" if estado == "Sí" else ("Atrasado" if estado == "Atrasado" else "No devuelto"))
        tree_prestamos.insert("", "end", values=valores, tags=(tag,))
    tree_prestamos.tag_configure("atrasado", background="#ffb3b3")


def limpiar_campos():
    entry_titulo.delete(0, tk.END)
    entry_autor.delete(0, tk.END)
    entry_anio.delete(0, tk.END)
    combo_carrera.set("")
    combo_ubicacion.set("")


def agregar_libro():
    titulo = entry_titulo.get().strip()
    autor = entry_autor.get().strip()
    anio_txt = entry_anio.get().strip()
    carrera = combo_carrera.get().strip()
    ubicacion = combo_ubicacion.get().strip()

    if not titulo or not autor or not anio_txt or not carrera or not ubicacion:
        messagebox.showwarning("Campos incompletos", "Por favor completa todos los campos.")
        return

    try:
        anio = int(anio_txt)
    except ValueError:
        messagebox.showwarning("Año inválido", "Ingresa un año numérico (e.g., 2022).")
        return

    conn = conexion()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO libros (titulo, autor, anio, carrera, ubicacion)
        VALUES (?, ?, ?, ?, ?);
    """, (titulo, autor, anio, carrera, ubicacion))
    conn.commit()
    conn.close()

    limpiar_campos()
    mostrar_libros()
    mostrar_prestamos()


def eliminar_libro():
    sel = tree_libros.selection()
    if not sel:
        messagebox.showwarning("Seleccione un libro", "Selecciona un libro para eliminar.")
        return

    id_libro = tree_libros.item(sel[0])["values"][0]
    if not messagebox.askyesno("Confirmar", f"¿Eliminar el libro ID {id_libro} y sus préstamos asociados?"):
        return

    conn = conexion()
    cur = conn.cursor()
    cur.execute("DELETE FROM prestamos WHERE libro_id = ?", (id_libro,))
    cur.execute("DELETE FROM libros WHERE id = ?", (id_libro,))
    conn.commit()
    conn.close()

    mostrar_libros()
    mostrar_prestamos()


def registrar_prestamo():
    sel = tree_libros.selection()
    if not sel:
        messagebox.showwarning("Seleccione un libro", "Selecciona un libro para prestar.")
        return

    id_libro = tree_libros.item(sel[0])["values"][0]
    usuario = simpledialog.askstring("Préstamo", "¿A quién se le presta el libro?")
    if not usuario:
        return

    dias = simpledialog.askinteger("Duración", "¿Por cuántos días se presta el libro?", initialvalue=7, minvalue=1)
    if not dias or dias <= 0:
        messagebox.showwarning("Valor inválido", "Ingresa un número de días válido (>=1).")
        return

    f_prest = date.today()
    f_lim = f_prest + timedelta(days=dias)

    conn = conexion()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO prestamos (libro_id, nombre_usuario, fecha_prestamo, fecha_limite, devuelto)
        VALUES (?, ?, ?, ?, 0);
    """, (id_libro, usuario.strip(), f_prest.isoformat(), f_lim.isoformat()))
    conn.commit()
    conn.close()

    mostrar_libros()
    mostrar_prestamos()


def marcar_devuelto():
    sel = tree_libros.selection()
    if not sel:
        messagebox.showwarning("Seleccione un libro", "Selecciona un libro para marcar como devuelto.")
        return

    id_libro = tree_libros.item(sel[0])["values"][0]

    conn = conexion()
    cur = conn.cursor()
    # Solo marcamos el último préstamo NO devuelto de ese libro
    cur.execute("""
        UPDATE prestamos
        SET devuelto = 1
        WHERE id = (
            SELECT id FROM prestamos
            WHERE libro_id = ? AND devuelto = 0
            ORDER BY id DESC
            LIMIT 1
        );
    """, (id_libro,))
    conn.commit()
    conn.close()

    mostrar_libros()
    mostrar_prestamos()

notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill="both", padx=10, pady=10)

# Pestaña Libros
frame_libros = ttk.Frame(notebook)
notebook.add(frame_libros, text="Libros")

# Línea de formulario
frame_form = tk.Frame(frame_libros, bg="#f5f5f5")
frame_form.pack(pady=10, fill="x")

tk.Label(frame_form, text="Título:", bg="#f5f5f5").grid(row=0, column=0, padx=5, sticky="e")
entry_titulo = tk.Entry(frame_form)
entry_titulo.grid(row=0, column=1, padx=5)

tk.Label(frame_form, text="Autor:", bg="#f5f5f5").grid(row=0, column=2, padx=5, sticky="e")
entry_autor = tk.Entry(frame_form)
entry_autor.grid(row=0, column=3, padx=5)

tk.Label(frame_form, text="Año:", bg="#f5f5f5").grid(row=0, column=4, padx=5, sticky="e")
entry_anio = tk.Entry(frame_form)
entry_anio.grid(row=0, column=5, padx=5)

tk.Label(frame_form, text="Carrera:", bg="#f5f5f5").grid(row=1, column=0, padx=5, sticky="e")
combo_carrera = ttk.Combobox(frame_form, values=CARRERAS, state="readonly")
combo_carrera.grid(row=1, column=1, padx=5)

tk.Label(frame_form, text="Ubicación:", bg="#f5f5f5").grid(row=1, column=2, padx=5, sticky="e")
combo_ubicacion = ttk.Combobox(frame_form, values=UBICACIONES, state="readonly")
combo_ubicacion.grid(row=1, column=3, padx=5)

btn_agregar = tk.Button(frame_form, text="Agregar Libro", command=agregar_libro, bg="#4caf50", fg="white")
btn_agregar.grid(row=1, column=5, padx=5)


frame_botones = tk.Frame(frame_libros, bg="#f5f5f5")
frame_botones.pack(pady=10)

btn_eliminar = tk.Button(frame_botones, text="Eliminar Libro", command=eliminar_libro, bg="#f44336", fg="white")
btn_eliminar.pack(side="left", padx=10)

btn_prestar = tk.Button(frame_botones, text="Registrar Préstamo", command=registrar_prestamo, bg="#2196f3", fg="white")
btn_prestar.pack(side="left", padx=10)

btn_devolver = tk.Button(frame_botones, text="Marcar Devuelto", command=marcar_devuelto, bg="#ff9800", fg="white")
btn_devolver.pack(side="left", padx=10)


cols_libros = ("ID", "Título", "Autor", "Año", "Carrera", "Ubicación", "Devuelto")
tree_libros = ttk.Treeview(frame_libros, columns=cols_libros, show="headings", height=18)
for col in cols_libros:
    tree_libros.heading(col, text=col)
    tree_libros.column(col, width=130, anchor="center")
tree_libros.pack(expand=True, fill="both", padx=15, pady=15)


frame_prestamos = ttk.Frame(notebook)
notebook.add(frame_prestamos, text="Préstamos")

cols_prestamos = ("ID Libro", "Título", "Usuario", "Fecha Préstamo", "Fecha Límite", "Estado")
tree_prestamos = ttk.Treeview(frame_prestamos, columns=cols_prestamos, show="headings", height=18)
for col in cols_prestamos:
    tree_prestamos.heading(col, text=col)
    tree_prestamos.column(col, width=150, anchor="center")
tree_prestamos.pack(expand=True, fill="both", padx=10, pady=10)


mostrar_libros()
mostrar_prestamos()


root.mainloop()
