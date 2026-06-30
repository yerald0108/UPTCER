# UPTCER — Documentación Técnica del Sistema
## Sistema de Gestión de Permisos para la Importación de Equipos de Telecomunicaciones
### Ministerio de Comunicaciones — República de Cuba

---

## Índice

1. [Descripción general del sistema](#1-descripción-general-del-sistema)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Arquitectura del proyecto](#3-arquitectura-del-proyecto)
4. [Estructura de archivos](#4-estructura-de-archivos)
5. [Modelos de datos](#5-modelos-de-datos)
6. [Roles y permisos](#6-roles-y-permisos)
7. [Flujos de trabajo](#7-flujos-de-trabajo)
8. [Apps del sistema](#8-apps-del-sistema)
9. [Sistema de estilos y diseño](#9-sistema-de-estilos-y-diseño)
10. [Sistema de notificaciones](#10-sistema-de-notificaciones)
11. [Sistema de licencias](#11-sistema-de-licencias)
12. [Catálogo de equipos](#12-catálogo-de-equipos)
13. [Gestión de usuarios](#13-gestión-de-usuarios)
14. [Configuración del proyecto](#14-configuración-del-proyecto)
15. [Guía de despliegue](#15-guía-de-despliegue)
16. [Convenciones y buenas prácticas](#16-convenciones-y-buenas-prácticas)

---

## 1. Descripción general del sistema

UPTCER es un sistema web institucional desarrollado para el **Ministerio de Comunicaciones de Cuba** que gestiona el proceso de solicitud, revisión, evaluación y aprobación de **permisos de importación de equipos de telecomunicaciones** por personas naturales.

### Problema que resuelve

Anteriormente el proceso era manual en papel. UPTCER digitaliza completamente el ciclo de vida de una solicitud, desde que la persona natural la crea hasta que se emite la licencia oficial de importación.

### Qué hace el sistema

- Permite a personas naturales llenar y enviar el formulario oficial **F43** en formato digital
- El formulario se visualiza como una hoja A4 fiel al documento físico oficial
- Los operadores del Ministerio reciben, revisan y gestionan las solicitudes
- Si el equipo no está en el catálogo, la solicitud se deriva automáticamente al **Especialista Técnico**
- El especialista evalúa el equipo, emite su criterio técnico y puede agregarlo al catálogo
- Cuando se aprueba una solicitud, se genera automáticamente una **licencia oficial** imprimible
- Todo queda registrado en un historial de cambios con fecha, usuario y observaciones

---

## 2. Stack tecnológico

| Componente | Tecnología |
|------------|------------|
| Backend | Django 6.x (Python) |
| Base de datos | SQLite (desarrollo) / PostgreSQL (producción) |
| Frontend | HTML5 + CSS3 + JavaScript vanilla |
| Iconos | Lucide Icons (SVG, sin dependencias de build) |
| Gráficas | Chart.js 4.4 (CDN) |
| Fuente tipográfica | Inter (Google Fonts) |
| Gestión de configuración | python-decouple (.env) |
| Cálculo de fechas | python-dateutil |

No se usa ningún framework de JavaScript (React, Vue, Angular). Todo el frontend es HTML, CSS y JS vanilla, lo que simplifica el despliegue y el mantenimiento.

---

## 3. Arquitectura del proyecto

El proyecto sigue la arquitectura estándar de Django con apps separadas por dominio de negocio. Todas las apps viven dentro de la carpeta `apps/` para mantener el código organizado.

```
config/          → Configuración global del proyecto (settings, urls, wsgi)
apps/            → Todas las aplicaciones del sistema
  accounts/      → Usuarios, autenticación, roles, perfil
  solicitudes/   → Solicitudes F43, historial, evaluaciones
  equipos/       → Catálogo de equipos y categorías
  notificaciones/ → Sistema de notificaciones internas
  licencias/     → Generación y gestión de licencias
templates/       → Todos los templates HTML del sistema
static/          → CSS, JS, imágenes estáticas
media/           → Archivos subidos por usuarios (documentos adjuntos)
```

### Principio de separación de responsabilidades

Cada app tiene responsabilidad única:

- `accounts` sabe de usuarios y autenticación, no de solicitudes
- `solicitudes` sabe del ciclo de vida de una solicitud, importa de `equipos` y `licencias`
- `equipos` sabe del catálogo, no sabe quién hace solicitudes
- `notificaciones` recibe eventos de otras apps y notifica usuarios
- `licencias` se genera automáticamente cuando una solicitud es aprobada

---

## 4. Estructura de archivos

A continuación se documenta cada archivo del sistema, su ubicación y su propósito.

### 4.1 Raíz del proyecto

```
uptcer/
├── .env                    ← Variables de entorno (SECRET_KEY, DEBUG, etc.) — NUNCA subir a git
├── manage.py               ← Comando principal de Django
├── db.sqlite3              ← Base de datos SQLite (solo desarrollo)
└── requirements.txt        ← Dependencias Python del proyecto
```

### 4.2 Configuración (`config/`)

```
config/
├── __init__.py
├── settings.py             ← Configuración principal: apps instaladas, BD, static, auth, timezone
├── urls.py                 ← URLs raíz del proyecto — registra las URLs de cada app
├── wsgi.py                 ← Punto de entrada WSGI para producción
└── asgi.py                 ← Punto de entrada ASGI (opcional, para async)
```

**`config/settings.py`** — Los puntos más importantes:
- `AUTH_USER_MODEL = 'accounts.Usuario'` → modelo de usuario personalizado
- `LOGIN_URL = 'accounts:login'` → redirige a login cuando no está autenticado
- `LOGIN_REDIRECT_URL = 'accounts:dashboard'` → redirige al dashboard tras login
- `LANGUAGE_CODE = 'es-cu'` y `TIME_ZONE = 'America/Havana'` → localización cubana
- `SESSION_COOKIE_AGE = 28800` → sesión expira en 8 horas
- `AUTH_PASSWORD_VALIDATORS = []` → validadores de contraseña desactivados en desarrollo

**`config/urls.py`** — Registra todas las apps:
```python
path('',            include('apps.accounts.urls'))       # login, dashboard, usuarios, perfil
path('solicitudes/', include('apps.solicitudes.urls'))   # F43, lista, detalle, evaluaciones
path('equipos/',    include('apps.equipos.urls'))        # catálogo, búsqueda AJAX
path('licencias/',  include('apps.licencias.urls'))      # lista y detalle de licencias
path('notificaciones/', include('apps.notificaciones.urls'))
```

### 4.3 App `accounts`

Gestiona todo lo relacionado con usuarios: autenticación, roles, perfil, y gestión de usuarios por el directivo.

```
apps/accounts/
├── __init__.py
├── apps.py                 ← Configuración de la app (name = 'apps.accounts')
├── models.py               ← Modelo Usuario personalizado con 5 roles
├── forms.py                ← Formularios: crear usuario, editar perfil, cambiar contraseña
├── views.py                ← Todas las vistas de la app
├── urls.py                 ← URLs de la app con namespace 'accounts'
├── admin.py                ← Registro del modelo Usuario en el admin de Django
└── migrations/             ← Migraciones de base de datos
```

**`models.py`** — El modelo `Usuario` extiende `AbstractBaseUser` y define:
- 5 roles: `persona_natural`, `operador`, `especialista`, `aduana`, `directivo`
- Campos: `username`, `email`, `nombre`, `apellidos`, `rol`, `telefono`, `activo`
- Propiedades helper: `es_persona_natural`, `es_operador`, `es_especialista`, `es_aduana`, `es_directivo`
- Método `get_nombre_completo()` → retorna nombre + apellidos

**`views.py`** — Contiene las siguientes vistas:

| Vista | URL | Descripción |
|-------|-----|-------------|
| `vista_login` | `/` | Login con autenticación segura |
| `vista_logout` | `/logout/` | Cierre de sesión (solo POST) |
| `vista_dashboard` | `/dashboard/` | Redirige al dashboard correcto según el rol |
| `_dashboard_persona_natural` | — | Dashboard interno para persona natural |
| `_dashboard_operador` | — | Dashboard interno para operador |
| `_dashboard_especialista` | — | Dashboard interno para especialista |
| `_dashboard_aduana` | — | Dashboard interno para aduana |
| `_dashboard_directivo` | — | Dashboard directivo con gráficas Chart.js |
| `lista_usuarios` | `/usuarios/` | Lista de todos los usuarios (directivo/operador) |
| `nuevo_usuario` | `/usuarios/nuevo/` | Crear usuario nuevo (solo directivo) |
| `detalle_usuario` | `/usuarios/<pk>/` | Ver perfil y estadísticas de un usuario |
| `editar_usuario` | `/usuarios/<pk>/editar/` | Editar datos de un usuario |
| `cambiar_password_usuario` | `/usuarios/<pk>/password/` | Cambiar contraseña de un usuario |
| `togglear_usuario` | `/usuarios/<pk>/toggle/` | Activar/desactivar un usuario |
| `perfil` | `/perfil/` | Ver y editar el propio perfil |
| `cambiar_mi_password` | `/perfil/password/` | Cambiar la propia contraseña |

### 4.4 App `solicitudes`

El núcleo del sistema. Gestiona todo el ciclo de vida de una solicitud.

```
apps/solicitudes/
├── __init__.py
├── apps.py
├── models.py               ← Modelos Solicitud e HistorialSolicitud
├── forms.py                ← FormularioF43 con validaciones
├── views.py                ← Todas las vistas de solicitudes y evaluaciones
├── urls.py                 ← URLs con namespace 'solicitudes'
├── admin.py                ← Registro en admin de Django
├── templatetags/           ← Template tags personalizados
│   ├── __init__.py
│   └── json_extras.py      ← Filtro parse_json para templates
└── migrations/
```

**`models.py`** — Dos modelos principales:

`Solicitud`:
- Campos de flujo: `FLUJO_F43` y `FLUJO_RATS`
- Estados: `borrador`, `enviada`, `en_revision`, `aprobada`, `denegada`, `cancelada`
- Datos del formulario F43 se guardan serializados como JSON en `equipo_descripcion`
- `numero` se genera automáticamente: `F43-2025-0001` o `RAT-2025-0001`
- `equipo_no_listado` = True cuando el equipo no está en el catálogo
- `clase_badge` → propiedad que retorna la clase CSS del badge de estado

`HistorialSolicitud`:
- Registra cada cambio de estado con: estado anterior, estado nuevo, usuario responsable, observación y fecha
- Se crea automáticamente en cada cambio de estado

**`forms.py`** — `FormularioF43` define todos los campos del formulario oficial:
- Datos del solicitante (nombre, pasaporte, país, dirección, correo, teléfono)
- Datos de importación (provincia, modo, vuelo, arribo, aduana, RAD, objetivo, período)
- Validaciones cruzadas (RAD obligatorio si modo=RAD, tiempo obligatorio si período=temporal)

**`views.py`** — Vistas principales:

| Vista | URL | Descripción |
|-------|-----|-------------|
| `nueva_solicitud_f43` | `/solicitudes/nueva/f43/` | Formulario F43 como hoja A4 |
| `mis_solicitudes` | `/solicitudes/mis/` | Lista de solicitudes del usuario actual |
| `lista_solicitudes` | `/solicitudes/lista/` | Lista para operador/directivo con filtros |
| `detalle_solicitud` | `/solicitudes/<pk>/` | Detalle con hoja F43 + historial + panel de gestión |
| `cambiar_estado` | `/solicitudes/<pk>/estado/` | Cambia estado + registra historial + notifica |
| `cola_evaluaciones` | `/solicitudes/evaluaciones/` | Cola del especialista con pendientes y completadas |
| `evaluar_solicitud` | `/solicitudes/<pk>/evaluar/` | Vista especializada del especialista para emitir criterio |

**`templatetags/json_extras.py`** — Define el filtro `parse_json` que permite parsear el JSON del F43 directamente en los templates:
```django
{% with d=solicitud.equipo_descripcion|parse_json %}
  {{ d.nombre_apellidos }}
{% endwith %}
```

### 4.5 App `equipos`

Gestiona el catálogo de equipos de telecomunicaciones registrados en el sistema.

```
apps/equipos/
├── __init__.py
├── apps.py
├── models.py               ← Modelos CategoriaEquipo y Equipo
├── forms.py                ← FormularioEquipo y FormularioCategoria
├── views.py                ← Vistas del catálogo + endpoint AJAX de búsqueda
├── urls.py                 ← URLs con namespace 'equipos'
├── admin.py
└── migrations/
```

**`models.py`** — Dos modelos:

`CategoriaEquipo`: agrupa los equipos (ej: Teléfonos móviles, Routers, Tablets)

`Equipo`:
- `banda_frecuencia`: `libre` (2.4/5.7 GHz), `restringida`, `no_aplica`
- `requiere_permiso`: booleano que indica si necesita autorización
- Propiedades: `es_banda_libre`, `es_restringido`
- Restricción única: no pueden existir dos equipos con misma marca+modelo

**`views.py`** — Incluye `buscar_equipos_ajax` que es el endpoint JSON que usa el formulario F43 para buscar equipos mientras el solicitante escribe. Devuelve hasta 10 resultados con id, nombre, marca, modelo, banda y si está restringido.

### 4.6 App `notificaciones`

Sistema de notificaciones internas entre usuarios del sistema.

```
apps/notificaciones/
├── __init__.py
├── apps.py
├── models.py               ← Modelo Notificacion
├── servicios.py            ← Funciones helper para crear notificaciones
├── views.py                ← Lista, marcar leída, contador AJAX
├── urls.py
├── admin.py
└── migrations/
```

**`models.py`** — Modelo `Notificacion`:
- Tipos: `solicitud_nueva`, `derivada_especialista`, `cambio_estado`, `criterio_tecnico`, `general`
- `leida` / `fecha_lectura` para rastrear lectura
- `clase_icono` → propiedad que retorna el nombre del icono Lucide según el tipo
- `marcar_leida()` → método que marca la notificación y registra la fecha

**`servicios.py`** — Funciones de alto nivel que se llaman desde otras apps:

| Función | Cuándo se llama |
|---------|----------------|
| `notificar_solicitud_nueva(solicitud)` | Cuando persona natural envía F43 → notifica a operadores |
| `notificar_derivacion_especialista(solicitud)` | Cuando operador pone en revisión un equipo no listado → notifica a especialistas |
| `notificar_cambio_estado(solicitud, estado_anterior, usuario)` | En cada cambio de estado → notifica al solicitante |
| `notificar_criterio_tecnico(solicitud)` | Cuando especialista emite criterio → notifica a operadores |

### 4.7 App `licencias`

Genera y gestiona las licencias oficiales de importación.

```
apps/licencias/
├── __init__.py
├── apps.py
├── models.py               ← Modelo Licencia
├── servicios.py            ← Función generar_licencia()
├── views.py                ← Lista, detalle, revocar
├── urls.py
├── admin.py
└── migrations/
```

**`models.py`** — Modelo `Licencia`:
- `numero` se genera automáticamente: `LIC-2025-00001`
- `OneToOneField` con `Solicitud` — una solicitud tiene máximo una licencia
- Estados: `vigente`, `vencida`, `revocada`
- `fecha_vencimiento` → solo para importaciones temporales
- `verificar_vencimiento()` → verifica si una licencia temporal venció y actualiza el estado
- `es_temporal` → True si tiene fecha de vencimiento
- `es_vigente` → True si está vigente y no ha vencido

**`servicios.py`** — `generar_licencia(solicitud, emitida_por)`:
- Se llama automáticamente cuando una solicitud cambia a estado `aprobada`
- Calcula la fecha de vencimiento a partir del período de la solicitud (usa `python-dateutil`)
- Si ya existe una licencia para la solicitud, la retorna sin duplicar

---

## 5. Modelos de datos

### Diagrama de relaciones

```
Usuario (accounts.Usuario)
  │
  ├─── Solicitud.solicitante (FK)
  ├─── Solicitud.operador_asignado (FK)
  ├─── HistorialSolicitud.usuario (FK)
  ├─── Notificacion.destinatario (FK)
  └─── Licencia.emitida_por (FK)

Solicitud (solicitudes.Solicitud)
  │
  ├─── HistorialSolicitud.solicitud (FK, related_name='historial')
  ├─── Notificacion.solicitud (FK)
  ├─── Licencia.solicitud (OneToOne)
  └─── Equipo.solicitudes (FK, opcional)

Equipo (equipos.Equipo)
  └─── CategoriaEquipo.equipos (FK)
```

### Datos F43 serializados

Los datos del formulario F43 se guardan como JSON en el campo `Solicitud.equipo_descripcion`. Esto permite almacenar toda la información del formulario sin crear decenas de columnas. El JSON tiene esta estructura:

```json
{
  "nombre_apellidos": "Juan Pérez Rodríguez",
  "numero_pasaporte": "A12345678",
  "pais_residencia": "Cuba",
  "direccion_residencia": "Calle 23 #456, La Habana",
  "correo_electronico": "juan@ejemplo.cu",
  "telefono": "+53 5 123 4567",
  "provincia": "la_habana",
  "modo_importacion": "equipaje",
  "numero_vuelo": "CU123",
  "fecha_arribo": "2025-07-15",
  "pais_procedencia": "México",
  "aduana_acceso": "Aeropuerto",
  "lugar_acceso": "Aeropuerto José Martí",
  "numero_rad": "",
  "objetivo_importacion": "empleo_directo",
  "objetivo_otros_detalle": "",
  "periodo_importacion": "definitiva",
  "tiempo_solicitado": "",
  "firma_ci": "12345678901",
  "fecha_solicitud": "2025-06-20",
  "equipos": [
    {
      "descripcion": "Teléfono inteligente",
      "marca": "Samsung",
      "modelo": "Galaxy S24",
      "cantidad": 1,
      "equipoId": "15",
      "listado": true
    }
  ]
}
```

Los datos de evaluación técnica del especialista se guardan como JSON en `Solicitud.observaciones_tecnicas`:

```json
{
  "banda_detectada": "libre",
  "cumple_normativa": true,
  "criterio": "El equipo opera en banda libre de 2.4 GHz...",
  "evaluador": "Carlos García López"
}
```

---

## 6. Roles y permisos

El sistema tiene 5 roles definidos en el modelo `Usuario`:

### Persona Natural (`persona_natural`)
- Puede crear solicitudes F43
- Ve solo sus propias solicitudes
- Ve el estado de sus solicitudes en tiempo real
- Accede a sus licencias generadas
- Puede editar su propio perfil

### Operador (`operador`)
- Ve todas las solicitudes del sistema
- Puede cambiar el estado de cualquier solicitud
- Gestiona el catálogo de equipos (agregar, editar, desactivar)
- Puede revocar licencias
- Ve la lista de usuarios (solo lectura)

### Especialista Técnico (`especialista`)
- Accede a la cola de evaluaciones de equipos no listados
- Emite criterios técnicos con banda de frecuencia detectada
- Puede agregar equipos al catálogo directamente desde la evaluación
- Puede aprobar o denegar solicitudes con equipo no listado

### Aduana (`aduana`)
- Registra equipos retenidos (flujo RATS — pendiente de implementación completa)
- Verifica permisos existentes

### Directivo (`directivo`)
- Acceso completo al sistema
- Gestión de usuarios: crear, editar, activar/desactivar, cambiar contraseña
- Dashboard ejecutivo con gráficas de Chart.js
- Ve reportes y estadísticas globales

### Control de acceso en vistas

Cada vista usa `@login_required` y verifica el rol explícitamente:

```python
@never_cache
@login_required
def nueva_solicitud_f43(request):
    if not request.user.es_persona_natural:
        messages.error(request, 'No tiene permisos para acceder a esta sección.')
        return redirect('accounts:dashboard')
```

No se usa el sistema de grupos ni permisos de Django — el control se hace directamente con las propiedades del modelo `Usuario`.

---

## 7. Flujos de trabajo

### 7.1 Flujo F43 — Equipo listado en catálogo

```
Persona Natural
    │
    ▼
Llena formulario F43 (hoja A4 digital)
Busca equipo en catálogo mientras escribe
    │
    ▼
Envía solicitud → Estado: ENVIADA
    │
    ▼ (notificación automática a operadores)
Operador revisa la solicitud
    │
    ├── Aprueba → Estado: APROBADA
    │               └── Se genera LICENCIA automáticamente
    │               └── Se notifica al solicitante
    │
    └── Deniega → Estado: DENEGADA
                    └── Se notifica al solicitante
```

### 7.2 Flujo F43 — Equipo NO listado en catálogo

```
Persona Natural
    │
    ▼
Llena F43 con equipo no registrado
(el sistema lo marca como "no listado")
    │
    ▼
Envía solicitud → Estado: ENVIADA
equipo_no_listado = True
    │
    ▼
Operador revisa → Cambia a: EN_REVISIÓN
    │
    ▼ (notificación automática a especialistas)
Especialista evalúa en cola de evaluaciones
    │
    ├── Emite criterio + Aprueba → Estado: APROBADA
    │   │                           └── Licencia generada
    │   └── (opcionalmente agrega el equipo al catálogo)
    │
    └── Emite criterio + Deniega → Estado: DENEGADA
```

### 7.3 Flujo de estados de una solicitud

```
BORRADOR → ENVIADA → EN_REVISIÓN → APROBADA
                                 → DENEGADA
                   → CANCELADA
```

Las transiciones se registran en `HistorialSolicitud` con usuario responsable, fecha y observación.

### 7.4 Flujo de generación de licencia

```
Solicitud aprobada
    │
    ▼
generar_licencia(solicitud, usuario_que_aprobó)
    │
    ├── Parsea datos F43 del JSON
    ├── Si periodo = "temporal": calcula fecha_vencimiento = hoy + N meses
    └── Crea Licencia con número único LIC-YYYY-NNNNN
    │
    ▼
Licencia disponible para imprimir como hoja A4 oficial
```

---

## 8. Apps del sistema

### Templates — estructura completa

```
templates/
├── base/
│   ├── base.html                    ← Template padre de todas las vistas autenticadas
│   │                                  Contiene: sidebar, navbar, mensajes, scripts
│   └── base_auth.html               ← Template padre del login (sin sidebar)
│
├── accounts/
│   ├── login.html                   ← Pantalla de login con dos paneles
│   ├── perfil.html                  ← Perfil del usuario autenticado
│   ├── cambiar_password.html        ← Formulario de cambio de contraseña propia
│   ├── dashboard_persona_natural.html
│   ├── dashboard_operador.html
│   ├── dashboard_especialista.html
│   ├── dashboard_aduana.html
│   ├── dashboard_directivo.html     ← Con gráficas Chart.js
│   └── usuarios/
│       ├── lista.html               ← Lista de usuarios con filtros
│       ├── detalle.html             ← Perfil de un usuario + estadísticas
│       ├── form_usuario.html        ← Crear y editar usuario (mismo template)
│       └── cambiar_password.html    ← Cambiar contraseña de otro usuario
│
├── solicitudes/
│   ├── f43.html                     ← Formulario F43 como hoja A4
│   ├── mis_solicitudes.html         ← Lista de solicitudes del solicitante
│   ├── lista.html                   ← Lista para operador/directivo con filtros
│   ├── detalle.html                 ← Hoja F43 solo lectura + historial + panel gestión
│   └── especialista/
│       ├── cola.html                ← Cola de evaluaciones pendientes y completadas
│       └── evaluar.html             ← Vista de evaluación técnica del especialista
│
├── equipos/
│   ├── lista.html                   ← Catálogo con búsqueda y filtros
│   ├── detalle.html                 ← Ficha del equipo
│   ├── form_equipo.html             ← Crear y editar equipo
│   └── categorias.html             ← Gestión de categorías
│
├── licencias/
│   ├── lista.html                   ← Lista de licencias con filtros
│   └── detalle.html                 ← Documento oficial imprimible de la licencia
│
└── notificaciones/
    └── lista.html                   ← Centro de notificaciones del usuario
```

### Static — estructura completa

```
static/
├── css/
│   ├── global.css          ← Sistema de diseño completo: variables, layout, componentes
│   ├── login.css           ← Estilos específicos de la pantalla de login
│   ├── toast.css           ← Sistema de notificaciones toast animadas
│   ├── f43.css             ← Estilos de la hoja A4 del formulario F43
│   └── licencia.css        ← Estilos del documento oficial de licencia
└── js/
    ├── toast.js            ← Sistema de toasts: mostrar, cerrar, contador de progreso
    └── f43.js              ← Lógica del formulario F43: búsqueda, filas dinámicas, envío
```

---

## 9. Sistema de estilos y diseño

Todo el sistema visual se define en `static/css/global.css` mediante **variables CSS (Design Tokens)**. Esto significa que cambiar un color o espaciado en `:root` afecta todo el sistema automáticamente.

### Variables principales

```css
:root {
  /* Paleta institucional */
  --color-primario:        #1A3A5C;   /* Azul institucional */
  --color-secundario:      #2E7D32;   /* Verde aprobado */
  --color-acento:          #C62828;   /* Rojo denegado */
  --color-advertencia:     #F57F17;   /* Naranja pendiente */

  /* Sidebar */
  --sidebar-ancho:          260px;    /* Ancho expandido */
  --sidebar-ancho-colapsado: 68px;   /* Ancho colapsado (solo iconos) */

  /* Tipografía — mínimo 16px en toda la interfaz */
  --texto-base: 1rem;   /* 16px */
  --texto-sm:   0.875rem; /* 14px */
}
```

### Layout principal

El layout usa CSS Flexbox:

```
┌─────────────────────────────────────────┐
│  .layout-wrapper (flex)                 │
│  ┌──────────┬──────────────────────────┐│
│  │ .layout  │ .layout-main             ││
│  │ -sidebar │ ┌──────────────────────┐ ││
│  │ (fixed)  │ │ .layout-navbar       │ ││
│  │          │ └──────────────────────┘ ││
│  │          │ ┌──────────────────────┐ ││
│  │          │ │ .layout-contenido    │ ││
│  │          │ │ (max-width: 1280px,  │ ││
│  │          │ │  centrado)           │ ││
│  │          │ └──────────────────────┘ ││
│  └──────────┴──────────────────────────┘│
└─────────────────────────────────────────┘
```

### Sidebar colapsable

El sidebar tiene dos estados guardados en `localStorage`:
- **Expandido**: muestra icono + texto
- **Colapsado** (`clase 'colapsado'`): muestra solo iconos, con tooltips al hacer hover

El botón flotante `.btn-colapsar-sidebar` se posiciona con `position: fixed` fuera del sidebar para que siempre sea visible.

### Componentes CSS disponibles

| Clase | Uso |
|-------|-----|
| `.tarjeta` | Contenedor con borde, sombra y borde redondeado |
| `.stat-card` | Tarjeta de estadística con icono y valor |
| `.btn-primario` | Botón azul institucional |
| `.btn-secundario` | Botón con borde azul |
| `.btn-peligro` | Botón rojo |
| `.badge-aprobado` | Badge verde |
| `.badge-denegado` | Badge rojo |
| `.badge-pendiente` | Badge naranja |
| `.badge-revision` | Badge azul claro |
| `.campo-input` | Input de formulario estilizado |
| `.campo-select` | Select estilizado |
| `.campo-textarea` | Textarea estilizado |
| `.tabla` | Tabla con estilos institucionales |
| `.alerta-success/error/warning/info` | Alertas de color |
| `.grid-2/3/4` | Grillas CSS de 2, 3 o 4 columnas |

---

## 10. Sistema de notificaciones

### Toast notifications (`static/js/toast.js`)

Las notificaciones toast aparecen en la esquina superior derecha con animación de entrada y barra de progreso.

**Cómo usar en JavaScript:**
```javascript
mostrarToast({
  tipo: 'success',    // success, error, warning, info
  titulo: 'Título',  // opcional
  mensaje: 'Texto del mensaje',
  duracion: 4000,    // ms, opcional (default: 4000)
});
```

**Cómo Django envía mensajes que se convierten en toasts:**

En `base.html`, los mensajes de Django se convierten en elementos HTML ocultos:
```html
<div id="django-messages" style="display:none;">
  <span data-toast data-tipo="success" data-mensaje="Operación exitosa"></span>
</div>
```

El archivo `toast.js` lee estos elementos en `DOMContentLoaded` y los convierte en toasts animados.

### Notificaciones internas

El modelo `Notificacion` almacena notificaciones en la BD. El contador en el navbar se actualiza cada 60 segundos mediante un fetch al endpoint `/notificaciones/contador/`.

---

## 11. Sistema de licencias

### Generación automática

Cuando una solicitud pasa a estado `APROBADA`, sea por el operador o el especialista, se llama automáticamente a:

```python
from apps.licencias.servicios import generar_licencia
generar_licencia(solicitud, usuario)
```

Esta función:
1. Verifica que no exista ya una licencia para esta solicitud
2. Parsea el JSON del F43 para extraer el período de importación
3. Si es temporal, calcula `fecha_vencimiento = hoy + N meses` (usando `relativedelta`)
4. Crea la licencia con número único `LIC-YYYY-NNNNN`

### Documento imprimible

La licencia en `templates/licencias/detalle.html` usa los mismos estilos de hoja A4 que el F43 (`static/css/f43.css` y `static/css/licencia.css`). Al imprimir (`window.print()`), se ocultan el sidebar, navbar y botones de acción, dejando solo el documento oficial.

### Verificación de vencimiento

El método `licencia.verificar_vencimiento()` se llama cada vez que se abre una licencia. Si la fecha de vencimiento ya pasó y el estado es `vigente`, lo cambia automáticamente a `vencida`.

---

## 12. Catálogo de equipos

### Búsqueda AJAX en F43

El formulario F43 tiene un campo de búsqueda en cada fila de la tabla de equipos. Mientras el usuario escribe (con debounce de 300ms), se hace un fetch al endpoint:

```
GET /equipos/buscar/?q=samsung
```

Que retorna JSON con hasta 10 equipos que coincidan con nombre, marca o modelo.

Si el equipo se encuentra, se autocompleta la fila con marca, modelo y se muestra un badge de estado (banda libre / restringida).

Si no se encuentra, se muestra "No encontrado en catálogo" y la fila queda marcada con `data-listado="false"`, lo que hace que al guardar se marque `equipo_no_listado = True` en la solicitud.

### Flujo de agregación al catálogo desde evaluación

Cuando el especialista evalúa un equipo no listado y lo aprueba, puede marcar "Agregar al catálogo". El formulario de evaluación incluye campos adicionales (nombre, categoría, banda). Si el checkbox está marcado y la acción es "aprobar", la vista `evaluar_solicitud` crea el equipo en el catálogo automáticamente.

---

## 13. Gestión de usuarios

Solo el directivo puede crear y gestionar usuarios. El flujo es:

1. Directivo accede a `/usuarios/nuevo/`
2. Llena el formulario con nombre, apellidos, username, email, rol y contraseña
3. El usuario puede hacer login inmediatamente
4. El directivo puede cambiar la contraseña, editar datos o desactivar la cuenta en cualquier momento

Los validadores de contraseña están desactivados en desarrollo (`AUTH_PASSWORD_VALIDATORS = []`) para facilitar la creación de usuarios de prueba.

**IMPORTANTE para producción:** activar los validadores de contraseña en `settings.py`:
```python
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
```

---

## 14. Configuración del proyecto

### Archivo `.env`

El archivo `.env` en la raíz del proyecto **nunca debe subirse a git**. Contiene:

```env
SECRET_KEY=tu-clave-secreta-aqui-cambiar-en-produccion
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

Para producción:
```env
SECRET_KEY=clave-larga-aleatoria-de-50-caracteres-minimo
DEBUG=False
ALLOWED_HOSTS=tu-dominio.cu,www.tu-dominio.cu
```

### Instalar dependencias

```bash
pip install -r requirements.txt
```

### Primera ejecución

```bash
# Activar entorno virtual
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/Mac

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Arrancar servidor
python manage.py runserver
```

### Crear un usuario desde el admin

1. Ir a `http://127.0.0.1:8000/admin/`
2. Entrar con el superusuario
3. Ir a Accounts → Usuarios → Agregar usuario
4. Asignar el rol correspondiente

---

## 15. Guía de despliegue

### Para producción en Linux (Ubuntu)

```bash
# 1. Clonar el repositorio
git clone <repo-url> /var/www/uptcer
cd /var/www/uptcer

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install django pillow python-decouple python-dateutil gunicorn

# 4. Configurar .env
cp .env.example .env
nano .env  # Editar con valores de producción

# 5. Recolectar archivos estáticos
python manage.py collectstatic --noinput

# 6. Aplicar migraciones
python manage.py migrate

# 7. Crear superusuario
python manage.py createsuperuser

# 8. Arrancar con Gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### Cambiar a PostgreSQL en producción

En `config/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME':     config('DB_NAME'),
        'USER':     config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST':     config('DB_HOST', default='localhost'),
        'PORT':     config('DB_PORT', default='5432'),
    }
}
```

Y agregar al `.env`:
```env
DB_NAME=uptcer_db
DB_USER=uptcer_user
DB_PASSWORD=contraseña-segura
DB_HOST=localhost
DB_PORT=5432
```

---

## 16. Convenciones y buenas prácticas

### Nombres en español

Todo el código de negocio usa nombres en español para que el equipo cubano pueda entenderlo sin barreras:
- Modelos: `Usuario`, `Solicitud`, `Licencia`, `Notificacion`
- Vistas: `vista_login`, `nueva_solicitud_f43`, `cambiar_estado`
- Templates: `dashboard_operador.html`, `mis_solicitudes.html`
- CSS: `.sidebar-enlace`, `.campo-input`, `.btn-primario`

### Nunca usar emojis en el código

Todos los iconos son SVG de Lucide Icons. Se inicializan con:
```javascript
lucide.createIcons();
```

Para iconos añadidos dinámicamente (por JavaScript):
```javascript
lucide.createIcons({ nodes: [elemento] });
```

### `@never_cache` en todas las vistas autenticadas

Previene que el navegador guarde en caché páginas con datos sensibles:
```python
@never_cache
@login_required
def vista_dashboard(request):
    ...
```

### Imports dentro de funciones cuando es necesario

Para evitar importaciones circulares entre apps, algunos imports se hacen dentro de las funciones:
```python
def cambiar_estado(request, pk):
    ...
    from apps.licencias.servicios import generar_licencia
    generar_licencia(solicitud, usuario)
```

### Datos del F43 como JSON

Los datos del formulario F43 se guardan serializados en un solo campo JSON (`equipo_descripcion`) en lugar de crear decenas de columnas. Esto facilita agregar nuevos campos al formulario sin nuevas migraciones.

Para leer estos datos en una vista:
```python
import json
datos_f43 = json.loads(solicitud.equipo_descripcion or '{}')
equipos = datos_f43.get('equipos', [])
```

Para leer en un template se usa el filter personalizado:
```django
{% load json_extras %}
{% with d=solicitud.equipo_descripcion|parse_json %}
  {{ d.nombre_apellidos }}
{% endwith %}
```

### Historial siempre registrado

Cada cambio de estado SIEMPRE crea un `HistorialSolicitud`. Nunca cambiar el estado de una solicitud sin crear el historial:
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

### Formulario F43 como hoja A4

El formulario y el detalle de la solicitud se muestran como una hoja de papel A4 (`210mm × 297mm`) con `box-shadow` para dar sensación de documento físico. Al imprimir, los estilos `@media print` ocultan toda la interfaz web y dejan solo el documento limpio.

---

*Documentación generada para el equipo de desarrollo de UPTCER*
*Ministerio de Comunicaciones — República de Cuba*
*Sistema desarrollado con Django + Python*