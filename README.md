# CardTrack - Control de Gastos 💳

Aplicación web full-stack para trackear gastos de tarjeta de crédito con categorización automática, dashboard interactivo y recomendaciones inteligentes.

![CardTrack](https://img.shields.io/badge/CardTrack-v1.0-00f0ff?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green?style=flat-square)

## ✨ Features

- 📤 **Subida de resúmenes** - Arrastrá y soltá tu PDF o CSV
- 📊 **Dashboard interactivo** - Gráficos de barras, donut y tendencias
- 🏷️ **Categorías editables** - Personalizá tus categorías de gastos
- 🤖 **Analytics inteligente** - Recomendaciones basadas en tus hábitos
- 📥 **Exportar PDF** - Descargá tu dashboard completo
- 👥 **Multi-usuario** - Registro abierto con autenticación JWT
- 🌙 **Tema Dark Neon** - Diseño moderno y profesional

## 🚀 Deploy en Railway

### 1. Crear proyecto en Railway

1. Andá a [Railway](https://railway.app)
2. Creá un nuevo proyecto
3. Agregá una base de datos PostgreSQL

### 2. Conectar repositorio

1. Subí este código a GitHub
2. En Railway, conectá tu repo
3. Railway detectará automáticamente el Procfile

### 3. Variables de entorno

Configurá estas variables en Railway:

```
DATABASE_URL=postgresql://... (automático con PostgreSQL addon)
SECRET_KEY=tu-clave-secreta-muy-larga-y-segura
```

### 4. Deploy

Railway hace deploy automático cuando pusheás a main.

## 💻 Desarrollo Local

### Requisitos

- Python 3.9+
- pip

### Instalación

```bash
# Clonar repo
git clone <tu-repo>
cd Tarjeta

# Crear virtualenv
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
```

### Correr servidor

```bash
uvicorn backend.main:app --reload
```

Abrí http://localhost:8000 en tu navegador.

### Base de datos

Por defecto usa SQLite local (`cardtrack.db`). Para PostgreSQL:

```bash
set DATABASE_URL=postgresql://user:pass@host:port/dbname
```

## 📁 Estructura

```
Tarjeta/
├── backend/
│   ├── __init__.py
│   ├── main.py          # FastAPI app
│   ├── auth.py          # Autenticación JWT
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py       # Pydantic schemas
│   ├── database.py      # Conexión DB
│   └── analytics.py     # Motor de recomendaciones
├── index.html           # Frontend
├── styles.css           # Estilos
├── app.js               # Lógica frontend
├── requirements.txt     # Dependencias Python
├── Procfile             # Railway
└── railway.json         # Config Railway
```

## 🔒 Seguridad

- Contraseñas hasheadas con bcrypt
- Tokens JWT con expiración de 7 días
- CORS configurado
- Variables de entorno para secrets

## 📝 API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/auth/register` | Registrar usuario |
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Info usuario actual |
| GET | `/api/categories` | Listar categorías |
| POST | `/api/categories` | Crear categoría |
| PUT | `/api/categories/{id}` | Editar categoría |
| DELETE | `/api/categories/{id}` | Eliminar categoría |
| GET | `/api/transactions` | Listar transacciones |
| POST | `/api/transactions` | Crear transacción |
| POST | `/api/upload` | Subir archivo |
| GET | `/api/analytics` | Obtener analytics |

## 🛠️ Tecnologías

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: HTML, CSS, JavaScript vanilla
- **Auth**: JWT con python-jose
- **Charts**: Chart.js
- **PDF**: html2pdf.js

## 📄 Licencia

MIT
