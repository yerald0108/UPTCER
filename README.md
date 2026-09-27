# UPTCER — Sistema de Gestión de Permisos de Importación de Equipos de Telecomunicaciones

**Ministerio de Comunicaciones — República de Cuba**

Sistema web institucional que digitaliza el proceso de solicitud, revisión, evaluación y aprobación de permisos de importación de equipos de telecomunicaciones por personas naturales.

---

## Índice

1. [Descripción general](#1-descripción-general)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Arquitectura del proyecto](#3-arquitectura-del-proyecto)
4. [Roles del sistema](#4-roles-del-sistema)
5. [Flujo principal](#5-flujo-principal)
6. [Estados de una solicitud](#6-estados-de-una-solicitud)
7. [Modelos de datos](#7-modelos-de-datos)
8. [Apps del sistema](#8-apps-del-sistema)
9. [Sistema de estilos y diseño](#9-sistema-de-estilos-y-diseño)
10. [Instalación y configuración](#10-instalación-y-configuración)
11. [Usuarios de prueba](#11-usuarios-de-prueba)
12. [Convenciones y buenas prácticas](#12-convenciones-y-buenas-prácticas)
13. [Tests automatizados](#13-tests-automatizados)

---

## 1. Descripción general

UPTCER digitaliza completamente el ciclo de vida de una solicitud de importación de equipos de telecomunicaciones, desde que la persona natural crea el formulario F43 hasta que se genera la licencia oficial de importación tras el pago de la factura correspondiente.

### Qué hace el sistema

- Permite a personas naturales llenar y enviar el **formulario oficial F43** en formato digital, visualizado como hoja A4 fiel al documento físico
- La categoría del equipo se asigna **automáticamente** según el equipo seleccionado del catálogo, enrutando la solicitud al especialista del área correspondiente
- Si el equipo no está en el catálogo, la solicitud va directamente al **Especialista Superior** para evaluación técnica
- El directivo aprueba la solicitud y el sistema genera automáticamente una **factura**
- Al registrar el pago de la factura se genera la **licencia oficial** imprimible
- Todo queda registrado en un historial de cambios con fecha, usuario y observaciones
- Sistema de notificaciones internas y por correo en cada transición del flujo

---

## 2. Stack tecnológico

| Componente | Tecnología |
|---|---|
| Backend | Django 6.x (Python) |
| Base de datos | SQLite (desarrollo) / PostgreSQL (producción) |
| Frontend | HTML5 + CSS3 + JavaScript vanilla |
| Iconos | Lucide Icons (SVG, sin dependencias de build) |
| Gráficas | Chart.js 4.4 (CDN) |
| Fuente tipográfica | Inter (Google Fonts) |
| Gestión de configuración | python-decouple (.env) |
| Cálculo de fechas | python-dateutil |

No se usa ningún framework de JavaScript. Todo el frontend es HTML, CSS y JS vanilla.

---

## 3. Arquitectura del proyecto

```
config/          → Configuración global (settings, urls, wsgi)
apps/
  accounts/      → Usuarios, autenticación, roles, perfil, dashboards
  solicitudes/   → Solicitudes F43, historial, evaluaciones, cambio de estado
  equipos/       → Catálogo de equipos y categorías, búsqueda AJAX
  notificaciones/ → Sistema de notificaciones internas y por correo
  licencias/     → Facturas y licencias de importación
templates/       → Todos los templates HTML
static/          → CSS, JS, fuentes
media/           → Archivos subidos por usuarios (documentos adjuntos)
```

---

## 4. Roles del sistema

El sistema tiene **8 roles** definidos en el modelo `Usuario`:

| Rol | Username de prueba | Descripción |
|---|---|---|
| `persona_natural` | persona1, persona2, persona3 | Crea y sigue sus solicitudes F43 |
| `especialista_radiofaro` | esp_radiofaro | Revisa solicitudes de categoría Radiofaro |
| `especialista_movil` | esp_movil | Revisa solicitudes de categoría Móvil |
| `especialista_maritimo` | esp_maritimo | Revisa solicitudes de categoría Marítimo |
| `especialista_internet` | esp_internet | Revisa solicitudes de categoría Internet |
| `especialista_superior` | esp_superior | Evalúa equipos no listados en el catálogo |
| `aduana` | aduana | Gestiona solicitudes RATS (equipos retenidos) |
| `directivo` | directivo | Aprobación final, gestión de usuarios, reportes |

### Propiedades helper del modelo Usuario

```python
usuario.es_persona_natural        # True si es persona natural
usuario.es_especialista_base      # True para los 4 especialistas de área
usuario.es_especialista_superior  # True para el especialista superior
usuario.es_especialista           # True para cualquier tipo de especialista
usuario.es_aduana                 # True si es aduana
usuario.es_directivo              # True si es directivo
```

---

## 5. Flujo principal

### Paso 1 — Persona Natural crea la solicitud F43

- Llena el formulario F43 digital (hoja A4 fiel al documento físico oficial)
- En la sección de equipos puede **buscar en el catálogo** mientras escribe
- Si selecciona un equipo del catálogo → la categoría se asigna automáticamente
- Si el equipo no está en el catálogo → va directamente al Especialista Superior
- Al enviar: estado **ENVIADA** → notificación al especialista del área correspondiente

### Paso 2 — Especialista de área revisa su solicitud

Cada especialista ve **solo** las solicitudes de su categoría en estados `enviada` o `en_revision`.

- **Equipo correcto** → aprueba o deniega → si aprueba: estado **PENDIENTE_APROBACION** → notifica al directivo
- **Equipo no listado** → escala al superior → estado **EN_REVISION_SUPERIOR** → notifica al especialista superior

### Paso 3 — Especialista Superior evalúa equipos no listados

Solo ve solicitudes en estado `en_revision_superior`. Puede agregar el equipo al catálogo.

- Si aprueba → estado **PENDIENTE_APROBACION** → notifica al directivo
- Si deniega → estado **DENEGADA** → notifica al solicitante

### Paso 4 — Directivo aprueba

- Revisa las solicitudes en **PENDIENTE_APROBACION**
- Si aprueba → estado **APROBADA** → sistema genera **Factura** automáticamente
- Si deniega → estado **DENEGADA**

### Paso 5 — Factura y pago

- El directivo ve la factura en el menú **Facturas** (estado: pendiente de pago)
- Al registrar el pago → factura pasa a **PAGADA**
- El módulo de cálculo de montos se integrará en una fase posterior

### Paso 6 — Licencia generada automáticamente

- Al pagarse la factura → el sistema genera la **Licencia** con número único `LIC-YYYY-NNNNN`
- La licencia puede ser definitiva o temporal (con fecha de vencimiento)
- El solicitante puede verla e imprimirla desde su dashboard

### Transversal

- **Historial** completo de cada cambio de estado: quién, cuándo, con qué observación
- **Notificaciones** internas y por correo en cada transición
- **Directivo** puede supervisar cualquier solicitud en cualquier momento

---

## 6. Estados de una solicitud

```
BORRADOR
    ↓
ENVIADA ──────────────────────────────────────────────────────────┐
    ↓ (equipo en catálogo)         ↓ (equipo no listado)         │
EN_REVISION               EN_REVISION_SUPERIOR                   │
    ↓                              ↓                              │
PENDIENTE_APROBACION ←────────────┘                              │
    ↓                                                             │
APROBADA → Factura generada → Factura pagada → Licencia          │
    │                                                             │
DENEGADA ←────────────────────────────────────────────────────────┘
    │
CANCELADA
```

---

## 7. Modelos de datos

### Solicitud

- `flujo`: `f43` o `rats`
- `categoria`: `radiofaro`, `movil`, `maritimo`, `internet` — asignada automáticamente
- `estado`: ver sección 6
- `equipo_descripcion`: JSON con todos los datos del formulario F43
- `equipo_no_listado`: True cuando el equipo no está en el catálogo
- `numero`: generado automáticamente `F43-YYYY-NNNN`

### Datos F43 serializados (JSON)

```json
{
  "nombre_apellidos": "Juan Pérez Morales",
  "numero_pasaporte": "A12345678",
  "provincia": "la_habana",
  "modo_importacion": "equipaje",
  "objetivo_importacion": "empleo_directo",
  "periodo_importacion": "definitiva",
  "equipos": [
    {
      "descripcion": "Teléfono inteligente de gama alta",
      "marca": "Samsung",
      "modelo": "Galaxy S24",
      "cantidad": 1,
      "equipoId": "93",
      "listado": true
    }
  ]
}
```

### Factura

- `numero`: generado automáticamente `FAC-YYYY-NNNNN`
- `estado`: `pendiente`, `pagada`, `anulada`
- `total`, `subtotal`, `impuesto`: calculados por el módulo de cálculo (pendiente)
- `fecha_pago` y `registrado_pago_por`: se llenan al registrar el pago

### Licencia

- `numero`: generado automáticamente `LIC-YYYY-NNNNN`
- `estado`: `vigente`, `vencida`, `revocada`
- `fecha_vencimiento`: solo para importaciones temporales
- Se genera automáticamente al pagar la factura

### Historial de Solicitud

Registra cada cambio de estado con: estado anterior, estado nuevo, usuario responsable, observación y fecha.

---

## 8. Apps del sistema

### `apps/accounts`

Usuarios, autenticación, roles y dashboards por rol.

**Vistas principales:**

| Vista | URL | Descripción |
|---|---|---|
| `vista_login` | `/` | Login institucional |
| `vista_dashboard` | `/acceso/dashboard/` | Redirige al dashboard correcto según el rol |
| `lista_usuarios` | `/acceso/usuarios/` | Gestión de usuarios (solo directivo) |
| `perfil` | `/acceso/perfil/` | Perfil del usuario autenticado |

### `apps/solicitudes`

Núcleo del sistema. Gestiona el ciclo de vida completo de una solicitud.

**Función clave — asignación automática de categoría:**

```python
def _resolver_categoria_y_estado(equipos):
    """
    Analiza los equipos declarados en el F43 y determina:
    - Categoría según el primer equipo listado del catálogo
    - Estado inicial (enviada o en_revision_superior)
    - Si hay equipos no listados
    """
```

**Mapa de categorías:**

```python
CATEGORIA_EQUIPO_MAP = {
    'Teléfonos móviles':       'movil',
    'Routers y access points': 'internet',
    'Tablets y computadoras':  'internet',
    'Equipos de radio':        'radiofaro',
    'Cámaras y vigilancia':    'internet',
    'Wearables y accesorios':  'movil',
    'Equipos satelitales':     'maritimo',
    'Modems y equipos de red': 'internet',
}
```

**Vistas principales:**

| Vista | URL | Descripción |
|---|---|---|
| `nueva_solicitud_f43` | `/solicitudes/nueva/f43/` | Formulario F43 como hoja A4 |
| `mis_solicitudes` | `/solicitudes/mis/` | Lista de solicitudes del solicitante |
| `lista_solicitudes` | `/solicitudes/lista/` | Lista filtrada por rol del usuario |
| `detalle_solicitud` | `/solicitudes/<pk>/` | Detalle + historial + panel de gestión |
| `cambiar_estado` | `/solicitudes/<pk>/estado/` | Cambia estado + historial + notificaciones |
| `cola_evaluaciones` | `/solicitudes/evaluaciones/` | Cola del especialista superior |
| `evaluar_solicitud` | `/solicitudes/<pk>/evaluar/` | Evaluación técnica de equipo no listado |

### `apps/equipos`

Catálogo de equipos con búsqueda AJAX para el formulario F43.

El endpoint `/equipos/buscar/?q=` devuelve equipos en tiempo real mientras el solicitante escribe. Con `q` vacío devuelve todos los equipos activos para mostrar al hacer foco en el campo.

### `apps/notificaciones`

**Funciones de notificación:**

| Función | Cuándo se llama |
|---|---|
| `notificar_solicitud_nueva(solicitud)` | Al enviar F43 → notifica al especialista del área |
| `notificar_derivacion_superior(solicitud)` | Al escalar equipo no listado → notifica al superior |
| `notificar_pendiente_aprobacion(solicitud)` | Al estar lista para aprobar → notifica al directivo |
| `notificar_criterio_tecnico(solicitud)` | Al emitir criterio el superior → notifica al directivo |
| `notificar_cambio_estado(solicitud, estado_anterior, usuario)` | En cada cambio → notifica al solicitante |

### `apps/licencias`

Gestiona facturas y licencias.

**Servicios:**

```python
generar_factura(solicitud, emitida_por)  # Al aprobarse la solicitud
registrar_pago(factura, usuario)          # Al registrar el pago → genera la licencia
generar_licencia(solicitud, emitida_por) # Al pagarse la factura
```

**URLs:**

```
/licencias/                         → lista de licencias
/licencias/<numero>/                → detalle de licencia (imprimible)
/licencias/<numero>/revocar/        → revocar licencia (solo directivo)
/licencias/facturas/                → lista de facturas
/licencias/facturas/<numero>/       → detalle de factura
/licencias/facturas/<numero>/pagar/ → registrar pago (solo directivo)
```

---

## 9. Sistema de estilos y diseño

Todo el sistema visual se define en `static/css/global.css` mediante variables CSS:

```css
:root {
  --color-primario:    #1A3A5C;   /* Azul institucional */
  --color-secundario:  #2E7D32;   /* Verde aprobado */
  --color-acento:      #C62828;   /* Rojo denegado */
  --color-advertencia: #F57F17;   /* Naranja pendiente */
}
```

**Componentes CSS disponibles:**

| Clase | Uso |
|---|---|
| `.tarjeta` | Contenedor con borde y sombra |
| `.stat-card` | Tarjeta de estadística con icono y valor |
| `.btn-primario` | Botón azul institucional |
| `.badge-aprobado/denegado/pendiente/revision` | Badges de estado |
| `.tabla` | Tabla con estilos institucionales |
| `.alerta-success/error/warning/info` | Alertas de color |
| `.grid-2/3/4` | Grillas CSS de 2, 3 o 4 columnas |
| `.campo-input/select/textarea` | Inputs de formulario estilizados |

**Iconos:** Lucide Icons (SVG). Se inicializan con `lucide.createIcons()`. Para elementos añadidos dinámicamente: `lucide.createIcons({ nodes: [elemento] })`.

---

## 10. Instalación y configuración

### Requisitos previos

- Python 3.10 o superior
- Git instalado

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/yerald0108/UPTCER.git
cd UPTCER

# 2. Crear y activar entorno virtual
python -m venv venv

# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Linux / Mac
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Crear archivo .env en la raíz del proyecto
# Contenido:
# SECRET_KEY=clave-secreta-de-desarrollo-cambiar-en-produccion
# DEBUG=True
# ALLOWED_HOSTS=127.0.0.1,localhost

# 5. Aplicar migraciones
python manage.py migrate

# 6. Poblar base de datos con datos de prueba
python manage.py poblar_datos

# 7. Arrancar el servidor
python manage.py runserver
```

El sistema estará disponible en `http://127.0.0.1:8000`.

Para limpiar todos los datos y empezar desde cero:

```bash
python manage.py poblar_datos --limpiar
```

### Dependencias

| Paquete | Versión | Para qué se usa |
|---|---|---|
| Django | 6.0.6 | Framework principal |
| pillow | 12.2.0 | Procesamiento de imágenes |
| python-decouple | 3.8 | Variables de entorno desde `.env` |
| python-dateutil | 2.9.0 | Calcular fechas de vencimiento de licencias |
| sqlparse | 0.5.5 | Dependencia interna de Django |
| tzdata | 2026.2 | Zonas horarias (America/Havana) |

---

## 11. Usuarios de prueba

El comando `poblar_datos` crea los siguientes usuarios:

| Usuario | Contraseña | Rol |
|---|---|---|
| `directivo` | `directivo123` | Directivo |
| `esp_radiofaro` | `especialista123` | Especialista Radiofaro |
| `esp_movil` | `especialista123` | Especialista Móvil |
| `esp_maritimo` | `especialista123` | Especialista Marítimo |
| `esp_internet` | `especialista123` | Especialista Internet |
| `esp_superior` | `superior123` | Especialista Superior |
| `aduana` | `aduana123` | Aduana |
| `persona1` | `persona123` | Persona Natural |
| `persona2` | `persona123` | Persona Natural |
| `persona3` | `persona123` | Persona Natural |

También crea 8 solicitudes de ejemplo con diferentes estados para explorar todos los flujos del sistema desde el primer inicio.

---

## 12. Convenciones y buenas prácticas

### Nombres en español

Todo el código de negocio usa nombres en español: modelos, vistas, templates, clases CSS.

### `@never_cache` en todas las vistas autenticadas

```python
@never_cache
@login_required
def vista_dashboard(request):
    ...
```

### Historial siempre registrado

Cada cambio de estado SIEMPRE crea un `HistorialSolicitud`:

```python
solicitud.estado = nuevo_estado
solicitud.save()
HistorialSolicitud.objects.create(
    solicitud       = solicitud,
    estado_anterior = estado_anterior,
    estado_nuevo    = nuevo_estado,
    usuario         = request.user,
    observacion     = observacion,
)
```

### Datos del F43 como JSON

Los datos del formulario F43 se guardan serializados en `equipo_descripcion`. Para leerlos en una vista:

```python
import json
datos_f43 = json.loads(solicitud.equipo_descripcion or '{}')
equipos = datos_f43.get('equipos', [])
```

### Asignación automática de categoría

La función `_resolver_categoria_y_estado()` en `solicitudes/views.py` determina la categoría de una solicitud analizando los equipos declarados en el F43. Si el equipo está en el catálogo, lee su categoría y la mapea al rol del especialista correspondiente. Si no está en el catálogo, marca `equipo_no_listado=True` y asigna estado `en_revision_superior`.

### Flujo factura → licencia

Al aprobar una solicitud se genera la **factura** (no la licencia). La licencia se genera solo al registrar el **pago** de la factura. Esto se maneja en `apps/licencias/servicios.py`:

```python
# Al aprobar: genera factura
generar_factura(solicitud, usuario)

# Al pagar: genera licencia
registrar_pago(factura, usuario)  # Internamente llama a generar_licencia()
```

---

## 13. Tests automatizados

El sistema tiene una suite de **149 tests automatizados**.

```bash
# Ejecutar todos los tests
python manage.py test apps

# Con salida detallada
python manage.py test apps --verbosity=2

# Por app específica
python manage.py test apps.accounts
python manage.py test apps.solicitudes
python manage.py test apps.equipos
python manage.py test apps.licencias
python manage.py test apps.notificaciones
```

| App | Tests |
|---|---|
| accounts | 33 |
| solicitudes | 40 |
| equipos | 29 |
| licencias | 25 |
| notificaciones | 22 |
| **Total** | **149** |

---

*Sistema desarrollado con Django + Python*
*Ministerio de Comunicaciones — República de Cuba*