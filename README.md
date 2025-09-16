# JWschedule

JWschedule es una aplicación web diseñada para facilitar la gestión de horarios y eventos. Utiliza Python y Firebase para ofrecer una solución eficiente y escalable.

## Características Principales
- **Gestión de eventos y ubicaciones:** Organiza y administra eventos de manera sencilla.
- **Generación de PDFs:** Crea documentos en formato PDF directamente desde la aplicación.
- **Integración con Firebase:** Almacenamiento seguro y autenticación de usuarios.
- **Diseño responsivo:** Interfaz moderna y adaptable gracias a Tailwind CSS.

## Estructura del Proyecto
```
JWschedule/
│
├── static/                # Archivos estáticos (CSS, íconos, etc.)
│   ├── icons/             # Íconos y manifestos
│   └── tailwind.css       # Hoja de estilos principal
│
├── templates/             # Plantillas HTML
│   ├── base.html          # Plantilla base
│   ├── conductors.html    # Página de conductores
│   ├── events.html        # Página de eventos
│   ├── index.html         # Página principal
│   ├── link.html          # Página de enlaces
│   ├── locations.html     # Página de ubicaciones
│   ├── pdf.html           # Página de generación de PDFs
│   └── territories.html   # Página de territorios
│
├── .gitignore             # Archivos y carpetas ignorados por Git
├── app.py                 # Archivo principal de la aplicación
├── firebase_utils.py      # Utilidades para interactuar con Firebase
├── requirements.txt       # Dependencias del proyecto
```

## Requisitos Previos
Antes de comenzar, asegúrate de tener lo siguiente:
- **Python 3.8 o superior**
- **pip:** Gestor de paquetes de Python
- **Cuenta de Firebase:** Configurada con un proyecto activo

## Instalación
Sigue estos pasos para instalar y ejecutar el proyecto:

1. **Clona el repositorio:**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   ```

2. **Accede al directorio del proyecto:**
   ```bash
   cd JWschedule
   ```

3. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configura Firebase:**
   - Crea un proyecto en Firebase.
   - Descarga el archivo `google-services.json` y colócalo en el directorio raíz del proyecto.

## Uso
1. **Ejecuta la aplicación:**
   ```bash
   python app.py
   ```

2. **Accede desde tu navegador:**
   Ve a `http://127.0.0.1:5000` para interactuar con la aplicación.

## Cómo Contribuir
¡Tu ayuda es bienvenida! Sigue estos pasos para contribuir:

1. Haz un fork del repositorio.
2. Crea una nueva rama para tus cambios:
   ```bash
   git checkout -b nombre-de-la-rama
   ```
3. Realiza tus cambios y haz commit:
   ```bash
   git commit -m "Descripción de los cambios"
   ```
4. Sube tus cambios a tu repositorio:
   ```bash
   git push origin nombre-de-la-rama
   ```
5. Abre un Pull Request en este repositorio.

## Licencia
Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más información.

## Contacto
Si tienes preguntas, problemas o sugerencias, no dudes en ponerte en contacto con el desarrollador.