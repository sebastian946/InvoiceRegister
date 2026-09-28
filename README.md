# InvoiceRegister

Registro automático de facturas. Recibe un PDF por HTTP, extrae sus datos con un modelo de lenguaje y los escribe en una hoja de Google Sheets.

```
PDF  ──▶  Texto (pdfplumber / OCR)  ──▶  Invoice (Claude, salida estructurada)  ──▶  Google Sheets
```

## Qué hace

1. **Recibe el PDF** en `POST /invoices/upload` y lo guarda en `backend/files_upload/`.
2. **Extrae el texto.** Si el PDF tiene texto embebido usa `pdfplumber`. Si es un escaneo, lo rasteriza y aplica OCR con Tesseract en español.
3. **Estructura los datos** con Claude a través de LangChain. El modelo devuelve un objeto `Invoice` validado por Pydantic: número, fechas, proveedor, NIT, cliente, totales y las líneas de producto.
4. **Registra la factura** en dos pestañas de la hoja de cálculo:
   - `Hoja 1`: una fila por factura.
   - `Detalle`: una fila por línea de producto, enlazada por el número de factura.

## Requisitos

| Requisito | Notas |
|---|---|
| Python 3.12 | Versión fijada en `backend/.python-version` |
| [uv](https://docs.astral.sh/uv/) | Gestor de dependencias y entornos |
| poppler (`pdftoppm`) | Necesario para rasterizar PDFs escaneados |
| tesseract + paquete `spa` | Opcional. Solo para PDFs escaneados sin texto |
| Cuenta de Anthropic | Llave de API con acceso a `claude-opus-5` |
| Proyecto en Google Cloud | Cuenta de servicio con la API de Sheets habilitada |

En Ubuntu o Debian:

```bash
sudo apt install poppler-utils tesseract-ocr tesseract-ocr-spa
```

## Configuración

### 1. Google Sheets

1. Crea un proyecto en Google Cloud y habilita la **Google Sheets API**.
2. Crea una **cuenta de servicio** y descarga su llave en formato JSON.
3. Guarda el JSON en `backend/utils/` con un nombre que termine en `-service-account.json`, por ejemplo `dzlabs-service-account.json`, para que `.gitignore` lo excluya y el código lo encuentre solo. También puedes indicar otra ruta con `GOOGLE_CREDENTIALS_FILE`.
4. Crea la hoja de cálculo y ponle estos encabezados en la fila 1 de la primera pestaña:

   ```
   Número | Emisión | Vencimiento | Proveedor | NIT | Cliente | Total
   ```

   La pestaña `Detalle` se crea sola la primera vez que se registra una factura.
5. **Comparte la hoja como Editor** con el correo de la cuenta de servicio, que aparece en el JSON como `client_email`.
6. Copia el ID de la hoja desde la URL. Es el tramo entre `/d/` y `/edit`.

Abrir la hoja por ID solo requiere la API de Sheets. Si dejas `GOOGLE_SHEET_ID` vacío, el código la busca por nombre y entonces también necesita la API de Drive.

### 2. Anthropic

Crea una llave en la [consola de Anthropic](https://console.anthropic.com/). Al crearla, **asígnala a un workspace**. Una llave a nivel de organización es rechazada con un error 400 a menos que definas `ANTHROPIC_WORKSPACE_ID`.

### 3. Variables de entorno

Crea `backend/.env`:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_SHEET_ID=<id-de-la-hoja>   # tramo entre /d/ y /edit en la URL
PORT=8080
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Opcionales
# ANTHROPIC_WORKSPACE_ID=wrkspc_...
# DEBUG=true
# ENV=development
```

## Instalación y ejecución

Todos los comandos se ejecutan desde `backend/`:

```bash
cd backend
uv sync                              # crea .venv e instala las dependencias
uv run uvicorn main:app --reload     # levanta la API en http://127.0.0.1:8000
```

La documentación interactiva queda en `http://127.0.0.1:8000/docs`.

### Interfaz web

El frontend está en `frontend/` y usa React, TypeScript, Vite y Tailwind CSS. Requiere Node 20 o superior.

Para desarrollar, con el backend corriendo en otra terminal:

```bash
cd frontend
npm install
npm run dev                          # abre http://localhost:5173
```

Vite reenvía las llamadas de la API al backend en `http://127.0.0.1:8000`, así que no hay que configurar CORS.

Para probar como en producción, compila el frontend y deja que el backend lo sirva todo:

```bash
cd frontend && npm run build
cd ../backend && uv run uvicorn main:app
```

La aplicación completa queda en `http://127.0.0.1:8000/`.

## Despliegue

Frontend y backend se despliegan juntos como un solo servicio de Cloud Run. El `Dockerfile` de la raíz compila el frontend y lo empaqueta junto con la API. Desde la raíz del repositorio:

```bash
gcloud run deploy invoice-register --source . --region us-central1
```

El servicio es privado. El acceso desde el navegador se controla con Identity-Aware Proxy, que exige iniciar sesión con una cuenta de la organización.

## API

### `GET /Health`

```bash
curl http://127.0.0.1:8000/Health
```

### `POST /invoices/upload`

Recibe un PDF como `multipart/form-data`, lo procesa y devuelve la factura extraída.

| Parámetro | Tipo | Descripción |
|---|---|---|
| `file` | archivo | El PDF de la factura. Solo se acepta `application/pdf` |
| `register` | query, opcional | `false` para extraer sin escribir en la hoja. Por defecto `true` |

```bash
# Extraer y registrar en la hoja
curl --max-time 180 \
  -F "file=@test/fixtures/04_factura_papeleria.pdf;type=application/pdf" \
  http://127.0.0.1:8000/invoices/upload

# Solo extraer, sin escribir
curl --max-time 180 \
  -F "file=@test/fixtures/05_factura_logistica.pdf;type=application/pdf" \
  "http://127.0.0.1:8000/invoices/upload?register=false"
```

La extracción tarda cerca de un minuto porque el modelo razona sobre el documento. Usa un `--max-time` amplio.

Respuesta `201`:

```json
{
  "invoice": {
    "invoice_number": "FE-20931",
    "issue_date": "2026-09-03",
    "due_date": "2026-10-03",
    "supplier_name": "PAPELERÍA CENTRAL S.A.S.",
    "supplier_tax_id": "800.123.456-1",
    "customer_name": "INVERSIONES LA CUMBRE S.A.S.",
    "currency": "COP",
    "subtotal": 1225000.0,
    "tax": 232750.0,
    "total": 1457750.0,
    "items": [
      {"description": "Resma papel carta 75g (500 hojas)", "quantity": 20, "unit_price": 18500, "total": 370000}
    ]
  },
  "filename": "04_factura_papeleria.pdf",
  "registered": true
}
```

Errores:

| Código | Causa |
|---|---|
| `415` | El archivo no es un PDF |
| `422` | El PDF no contiene texto legible |
| `502` | Falló la llamada a Claude o a Google Sheets |

## Pruebas

```bash
uv run pytest            # unitarias, sin red ni costo
uv run pytest -v         # una línea por prueba
uv run pytest -k routes  # solo las que coincidan con el nombre
```

Las pruebas unitarias simulan Claude, Google Sheets y Tesseract, así que corren en un par de segundos y no gastan créditos.

Las pruebas de integración sí usan los servicios reales y están excluidas por defecto:

```bash
uv run pytest -m integration -k real_connection   # lee la hoja, no escribe
uv run pytest -m integration -k real_extraction   # llama a Claude, no escribe
uv run pytest -m integration                      # todas, incluida la que escribe una fila
```

### Archivos de prueba

En `backend/test/fixtures/` hay siete PDFs para probar la API:

| Archivo | Tipo | Uso |
|---|---|---|
| `01_factura_electronica_digital.pdf` | Factura con texto | Caso principal |
| `02_factura_escaneada_imagen.pdf` | Escaneo | Requiere Tesseract instalado |
| `03_formulario_reembolso_gastos.pdf` | Formulario, no factura | Caso límite |
| `04_factura_papeleria.pdf` | Factura con texto, 3 líneas | Prueba de la API |
| `05_factura_logistica.pdf` | Factura con texto, 4 líneas | Prueba de la API |
| `06_factura_consultoria.pdf` | Factura con texto, 5 líneas y retención en la fuente | Prueba de la API, total con descuento por retención |
| `07_factura_ferreteria.pdf` | Factura con texto, 6 líneas, pago de contado | Prueba de la API |

## Estructura del proyecto

```
Dockerfile                       # Imagen única: compila el frontend y ejecuta la API
backend/
├── main.py                      # App de FastAPI, rutas y servidor del frontend compilado
├── routes/routes.py             # POST /invoices/upload
├── controllers/
│   └── invoice_controller.py    # Orquesta PDF -> texto -> Invoice -> hoja
├── llm/llm.py                   # Extracción estructurada con Claude
├── models/models.py             # Invoice, InvoiceItem, FileUploadResponse
├── utils/
│   ├── config_env.py            # Settings desde .env
│   ├── pdf_reader.py            # Texto embebido u OCR
│   └── google_sheet_connection.py
├── files_upload/                # PDFs subidos por la API (ignorado por git)
└── test/
    ├── fixtures/                # PDFs de muestra
    └── test_*.py
frontend/
├── vite.config.ts               # Tailwind y proxy de desarrollo hacia la API
└── src/
    ├── App.tsx                  # Pantalla principal y estado
    ├── api.ts                   # Cliente de la API, tipos y mensajes de error
    ├── format.ts                # Formato de moneda, fechas y tamaños
    └── components/              # Zona de carga, resultado e historial
```

## Decisiones de diseño

- **Salida estructurada en vez de un agente.** La extracción es una sola llamada con `with_structured_output(Invoice, method="json_schema")`. No hay herramientas ni bucles de agente porque el modelo no necesita decidir pasos.
- **Sin `temperature`.** Los modelos actuales de Anthropic rechazan los parámetros de muestreo. El determinismo lo aporta el esquema JSON.
- **Conexión perezosa.** Ni el cliente de Claude ni el de Sheets se crean al importar el módulo, así que las pruebas y las herramientas de análisis no exigen credenciales.
- **Nombres de archivo saneados.** El nombre que envía el cliente se reduce a su último componente para impedir rutas como `../../etc/passwd`.

## Pendiente

- Procesamiento en segundo plano. Hoy la petición espera a que termine la extracción.
- Historial permanente en la interfaz. Hoy la lista de facturas procesadas se pierde al recargar.
- Despliegue automático con GitHub Actions.
