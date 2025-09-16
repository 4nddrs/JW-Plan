import os
import zipfile
from flask import Flask, render_template, request, redirect, url_for, send_file
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_utils import (
    get_all,
    add_record,
    get_record_by_id,
    resolve_event_references,
)
from datetime import datetime, timedelta

import io
import math
import calendar
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4


from ics import Calendar, Event
from dotenv import load_dotenv


load_dotenv()
app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

# --- Init Firebase ---
# if not firebase_admin._apps:
#    cred = credentials.Certificate("key.json")
#    firebase_admin.initialize_app(cred)

# db = firestore.client()
firebase_key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_key_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()


# --- Home ---
@app.route("/")
def index():
    return render_template("index.html")


# --- Locations ---
@app.route("/locations")
def locations():
    docs = db.collection("locations").stream()
    data = [{"id": doc.id, **doc.to_dict()} for doc in docs]
    return render_template("locations.html", locations=data)


@app.route("/locations/add", methods=["POST"])
def add_location():
    name = request.form.get("name")
    db.collection("locations").add({"name": name})
    return redirect(url_for("locations"))


@app.route("/locations/delete/<id>")
def delete_location(id):
    db.collection("locations").document(id).delete()
    return redirect(url_for("locations"))


# --- Conductors ---
@app.route("/conductors")
def conductors():
    docs = db.collection("conductors").stream()
    data = [{"id": doc.id, **doc.to_dict()} for doc in docs]
    return render_template("conductors.html", conductors=data)


@app.route("/conductors/add", methods=["POST"])
def add_conductor():
    name = request.form.get("name")
    db.collection("conductors").add({"name": name})
    return redirect(url_for("conductors"))


@app.route("/conductors/delete/<id>")
def delete_conductor(id):
    db.collection("conductors").document(id).delete()
    return redirect(url_for("conductors"))


# --- Territories ---
@app.route("/territories")
def territories():
    docs = db.collection("territories").stream()
    data = [{"id": doc.id, **doc.to_dict()} for doc in docs]
    return render_template("territories.html", territories=data)


@app.route("/territories/add", methods=["POST"])
def add_territory():
    number = request.form.get("number")
    db.collection("territories").add({"number": int(number)})
    return redirect(url_for("territories"))


@app.route("/territories/delete/<id>")
def delete_territory(id):
    db.collection("territories").document(id).delete()
    return redirect(url_for("territories"))


# --- Events ---
@app.route("/events")
def events_view():
    # Use get_all to fetch all documents
    events = get_all("events")

    # Pre-fetch all related data and store it in dictionaries for fast lookups
    locations = {loc["id"]: loc for loc in get_all("locations")}
    conductors = {con["id"]: con for con in get_all("conductors")}
    territories = {ter["id"]: ter for ter in get_all("territories")}

    for event in events:
        try:
            event["start_time_obj"] = datetime.strptime(
                event["start_time"], "%Y-%m-%dT%H:%M"
            )
            event["start_time_formatted"] = event["start_time_obj"].strftime(
                "%b %d, %Y %I:%M %p"
            )
        except (ValueError, KeyError):
            event["start_time_formatted"] = "N/A"

    return render_template(
        "events.html",
        events=events,
        locations=locations.values(),
        conductors=conductors.values(),
        territories=territories.values(),
    )


@app.route("/events/add", methods=["POST"])
def add_event():
    # Obtener los datos del formulario
    title = request.form["title"]
    start_time = request.form["start_time"]
    location_id = request.form["location_id"]
    conductor_id = request.form["conductor_id"]

    # Obtener el string de IDs de territorio desde el campo oculto del formulario
    territory_ids_string = request.form["territories_list"]

    # Separar el string de IDs en una lista
    territory_ids_list = territory_ids_string.split(",")

    # Obtener los datos completos de los documentos relacionados
    location_data = get_record_by_id("locations", location_id)
    conductor_data = get_record_by_id("conductors", conductor_id)

    # 🗺️ Procesar los territorios: buscar los números correspondientes a los IDs
    territory_numbers = []
    for terr_id in territory_ids_list:
        if terr_id:  # Evita procesar IDs vacíos
            territory_data = get_record_by_id("territories", terr_id)
            if territory_data:
                territory_numbers.append(str(territory_data.get("number", "N/A")))

    # 🎯 Unir los números en un solo string
    territory_numbers_string = ", ".join(territory_numbers)

    # Construir el objeto de datos del evento
    data = {
        "title": title,
        "start_time": start_time,
        "location_name": location_data.get("name", "N/A") if location_data else "N/A",
        "url": location_data.get("url", "N/A") if location_data else "N/A",
        "conductor_name": conductor_data.get("name", "N/A")
        if conductor_data
        else "N/A",
        "territory_number": territory_numbers_string,  # Guarda el string de números
    }

    # Agregar el nuevo registro a la colección 'events'
    add_record("events", data)

    return redirect(url_for("events_view"))


@app.route("/events/delete/<id>")
def delete_event(id):
    db.collection("events").document(id).delete()
    return redirect(url_for("events_view"))


def generate_pdf_from_firestore(year, month, events_data):
    """Genera un PDF del calendario a partir de los datos de Firestore."""

    # --- Márgenes ---
    margin_top = 0.7 * inch
    margin_bottom = 0.5 * inch
    margin_side = 0.5 * inch

    # --- Configuración general ---
    cols = 7
    header_height = 25
    interlineado = 15
    espacio_entre_eventos = 8
    cell_height_deseado = 210
    cell_width_deseado = 270

    # --- Mes actual ---
    primer_dia = datetime(year, month, 1).date()
    ultimo_dia = datetime(year, month, calendar.monthrange(year, month)[1]).date()
    dias_mes = [
        primer_dia + timedelta(days=i)
        for i in range((ultimo_dia - primer_dia).days + 1)
    ]
    primer_weekday = primer_dia.weekday()

    # --- Calcular filas necesarias ---
    total_dias = len(dias_mes) + primer_weekday
    rows_mes = math.ceil(total_dias / 7)
    rows = rows_mes + 1

    # --- Calcular tamaño hoja ---
    width = margin_side * 2 + cell_width_deseado * cols
    height = (
        margin_top + margin_bottom + header_height + cell_height_deseado * (rows - 1)
    )

    # --- Crear buffer y canvas ---
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width, height))

    # --- Función para convertir hex a RGB ---
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4))

    # --- Colores suaves ---
    color1 = hex_to_rgb("#B9DBFF")
    color2 = hex_to_rgb("#CCE5FF")

    # --- Color de tag de ejemplo ---
    tag_colors = {
        "Viloma Cala Cala": hex_to_rgb("#FFDFAF"),
    }

    # --- Título centrado ---
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(
        width / 2,
        height - margin_top / 2,
        f"Calendario {primer_dia.strftime('%B %Y').capitalize()}",
    )

    # --- Cabecera de días ---
    dias_semana = [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    ]
    c.setFont("Helvetica-Bold", 18)
    for i, dia in enumerate(dias_semana):
        x = margin_side + i * cell_width_deseado
        y = height - margin_top - header_height
        c.setFillColorRGB(0.85, 0.85, 0.85)
        c.rect(x, y, cell_width_deseado, header_height, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.drawCentredString(x + cell_width_deseado / 2, y + 7, dia)

    # --- Leyenda de tags ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(
        margin_side, height - margin_top - header_height - 20, "Leyenda de Tags:"
    )
    y_leyenda = height - margin_top - header_height - 40
    for tag, color in tag_colors.items():
        c.setFillColorRGB(*color)
        c.rect(margin_side, y_leyenda, 50, 15, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(margin_side + 55, y_leyenda, tag)
        y_leyenda -= 20

    # --- Grilla de días ---
    c.setFont("Helvetica", 11)
    for idx, dia_actual in enumerate(dias_mes):
        weekday = dia_actual.weekday()
        row = ((idx + primer_weekday) // cols) + 1
        col = weekday
        x = margin_side + col * cell_width_deseado
        y = height - margin_top - header_height - row * cell_height_deseado

        eventos_dia = [e for e in events_data if e["start_time"].date() == dia_actual]

        # --- Color de fondo: alternancia y tags ---
        color_fondo = color1 if idx % 2 == 0 else color2
        for evento in eventos_dia:
            titulo = evento.get("title", "")
            for tag, color in tag_colors.items():
                if tag in titulo:
                    color_fondo = color
                    break
            if color_fondo in tag_colors.values():
                break

        # Dibujar celda
        c.setFillColorRGB(*color_fondo)
        c.rect(x, y, cell_width_deseado, cell_height_deseado, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.rect(x, y, cell_width_deseado, cell_height_deseado)

        # Número del día
        c.setFont("Helvetica-Bold", 18)
        c.drawString(x + 2, y + cell_height_deseado - 16, str(dia_actual.day))
        c.setFont("Helvetica", 11)

        # --- Dibujar eventos ---
        for idx_ev, evento in enumerate(eventos_dia):
            hora_dt = evento["start_time"]

            # Posición vertical basada en la hora
            if 6 <= hora_dt.hour < 12:
                y_base = y + cell_height_deseado * 0.75 + 24
            elif 12 <= hora_dt.hour < 18:
                y_base = y + cell_height_deseado * 0.5 + 21
            else:
                y_base = y + cell_height_deseado * 0.25 + 18

            y_text = y_base - idx_ev * espacio_entre_eventos

            # Título y hora en negrita
            titulo = evento.get("title", "")
            if titulo:
                c.setFont("Helvetica-Bold", 16)
                texto = f"{hora_dt.strftime('%H:%M')} - {titulo}"
                x_centrado = (
                    x
                    + (cell_width_deseado - c.stringWidth(texto, "Helvetica-Bold", 13))
                    / 2
                )
                c.drawString(x_centrado, y_text, texto)
                y_text -= interlineado
                c.setFont("Helvetica", 14)

            # Atributos del evento
            atributos = {
                "Conductor": evento.get("conductor_name"),
                "Ubicación": evento.get("location_name"),
                "Territorio": f"{evento.get('territory_number')}"
                if evento.get("territory_number")
                else None,
            }

            for col_name, valor in atributos.items():
                if valor:
                    texto_attr = f"{col_name}: {valor}"
                    x_centrado = (
                        x
                        + (
                            cell_width_deseado
                            - c.stringWidth(texto_attr, "Helvetica", 13)
                        )
                        / 2
                    )
                    c.drawString(x_centrado, y_text, texto_attr)

                    # URL clicable para la ubicación
                    if col_name == "Ubicación" and evento.get("url"):
                        url = evento["url"]
                        c.linkURL(
                            url,
                            (
                                x_centrado,
                                y_text,
                                x_centrado + c.stringWidth(texto_attr, "Helvetica", 12),
                                y_text + 12,
                            ),
                        )

                    y_text -= interlineado

            y_text -= espacio_entre_eventos

    c.save()
    buffer.seek(0)
    return buffer


@app.route("/generate_pdf", methods=["GET"])
def generate_pdf():
    try:
        # Obtener mes y año de la URL
        year = request.args.get("year", default=datetime.now().year, type=int)
        month = request.args.get("month", default=datetime.now().month, type=int)

        events_ref = db.collection("events")
        # La consulta a Firestore no se puede hacer directamente con fechas,
        # porque el campo `start_time` es una cadena.
        # En su lugar, obtendremos todos los documentos y los filtraremos en Python.

        query = events_ref.order_by("start_time").stream()

        events_data = []
        for doc in query:
            event = doc.to_dict()
            # Convertir la cadena 'start_time' a un objeto datetime
            event["start_time"] = datetime.strptime(
                event["start_time"], "%Y-%m-%dT%H:%M"
            )
            events_data.append(event)

        # Filtramos los eventos en Python para que coincidan con el mes y año seleccionados
        events_month = [
            e
            for e in events_data
            if e["start_time"].year == year and e["start_time"].month == month
        ]

        print(f"✅ Found {len(events_month)} events for {month}/{year}.")

        pdf_buffer = generate_pdf_from_firestore(year, month, events_month)

        filename = f"calendario_{datetime(year, month, 1).strftime('%Y-%m')}.pdf"
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf",
        )

    except Exception as e:
        print(f"❌ Error al generar el PDF: {e}")
        return "Error al generar el PDF. Por favor, intente de nuevo.", 500


@app.route("/pdf", methods=["GET"])
def reportes_page():
    return render_template("pdf.html")


@app.route("/link", methods=["GET"])
def link_page():
    return render_template("link.html")


@app.route("/export_ics", methods=["POST"])
def export_ics():
    try:
        # Año y mes desde el formulario
        year = int(request.form.get("year"))
        month = int(request.form.get("month"))

        start_of_month = datetime(year, month, 1)
        end_of_month = datetime(
            year, month, calendar.monthrange(year, month)[1], 23, 59, 59
        )

        events_ref = db.collection("events")
        docs = (
            events_ref.where(
                "start_time", ">=", start_of_month.strftime("%Y-%m-%dT%H:%M")
            )
            .where("start_time", "<=", end_of_month.strftime("%Y-%m-%dT%H:%M"))
            .stream()
        )

        # Dos calendarios
        cal_apple = Calendar()
        cal_google = Calendar()

        for doc in docs:
            event_data = doc.to_dict()

            # =====================
            # Evento Apple
            # =====================
            e_apple = Event()
            e_apple.name = f"Predicación - {event_data.get('title', 'Sin título')}"

            # Fechas
            try:
                start_time_str = event_data.get("start_time")
                start_time_dt = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M")
                e_apple.begin = start_time_dt
                e_apple.end = start_time_dt + timedelta(hours=2)
            except (ValueError, TypeError):
                continue

            # Ubicación y URL
            if event_data.get("location_name"):
                e_apple.location = event_data["location_name"]
            if event_data.get("url") and event_data["url"].startswith("http"):
                e_apple.url = event_data["url"]

            # Descripción
            descripcion = []
            if event_data.get("conductor_name"):
                descripcion.append(f"Conductor: {event_data['conductor_name']}")
            if event_data.get("territory_number"):
                descripcion.append(f"Territorio: {event_data['territory_number']}")
            e_apple.description = "\n".join(descripcion) if descripcion else None

            cal_apple.events.add(e_apple)

            # =====================
            # Evento Google
            # =====================
            e_google = Event()
            e_google.name = f"Predicación - {event_data.get('title', 'Sin título')}"

            # Fechas
            e_google.begin = e_apple.begin
            e_google.end = e_apple.end

            # Ubicación = URL
            if event_data.get("url") and event_data["url"].startswith("http"):
                e_google.location = event_data["url"]

            # Descripción Google (Lugar + resto)
            descripcion_google = []
            if event_data.get("location_name"):
                descripcion_google.append(f"Lugar: {event_data['location_name']}")
            if event_data.get("conductor_name"):
                descripcion_google.append(f"Conductor: {event_data['conductor_name']}")
            if event_data.get("territory_number"):
                descripcion_google.append(
                    f"Territorio: {event_data['territory_number']}"
                )
            e_google.description = (
                "\n".join(descripcion_google) if descripcion_google else None
            )

            cal_google.events.add(e_google)

        # Crear ZIP con ambos archivos
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"calendario_apple.ics", cal_apple.serialize())
            zf.writestr(f"calendario_google.ics", cal_google.serialize())
        buffer.seek(0)

        filename = f"calendarios.zip"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/zip",
        )

    except Exception as e:
        print(f"Error al generar los ICS: {e}")
        return "Error al generar los archivos ICS.", 500


if __name__ == "__main__":
    app.run(debug=True)
