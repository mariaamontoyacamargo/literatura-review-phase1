# 🚀 Deployment Guide - Literatura Review Pipeline

**Objetivo**: Paquete local compartible con servidor HTTP integrado

---

## 📦 Estructura para Deployment

```
literatura-review-phase1/
├── README.md                 ← Instrucciones de inicio rápido
├── DEPLOYMENT.md             ← Este archivo
├── START_HERE.md             ← Guía de usuario
├── QUICK_START.sh            ← Script de inicio automático
│
├── data/
│   ├── consolidated_graph.json
│   ├── [pocket]_reviewed.json (7 archivos)
│   └── [pocket]_synthesized.json (7 archivos)
│
├── outputs/
│   ├── dashboard_consolidated.html   ← MAIN DASHBOARD
│   ├── dashboard_v3.html
│   ├── dashboard_v2.html
│   └── dashboard.html
│
├── scripts/
│   ├── requirements.txt
│   ├── pipeline_orchestrator.py
│   ├── generate_pocket_papers.py
│   ├── reviewer.py
│   ├── synthesizer.py
│   └── mapper.py
│
└── pockets_config.yaml
```

---

## 🎯 Requisitos Mínimos

- Python 3.8+
- 50 MB espacio libre (datos + dashboards)
- Navegador moderno (Chrome, Firefox, Safari)
- Puerto 8000 disponible

---

## ⚡ Inicio Rápido (1 minuto)

### Opción 1: Script Automático (Recomendado)

```bash
cd /Users/mariaamontoya/literatura-review-phase1
chmod +x QUICK_START.sh
./QUICK_START.sh
```

**Abre automáticamente**: http://localhost:8000/outputs/dashboard_consolidated.html

### Opción 2: Manual (3 pasos)

```bash
# 1. Ir al directorio
cd /Users/mariaamontoya/literatura-review-phase1

# 2. Instalar dependencias (primera vez solo)
pip install -r scripts/requirements.txt

# 3. Iniciar servidor
python -m http.server 8000

# 4. Abrir navegador
# http://localhost:8000/outputs/dashboard_consolidated.html
```

---

## 📊 Acceso Inmediato

Una vez el servidor está corriendo:

**🔗 Main Dashboard**
```
http://localhost:8000/outputs/dashboard_consolidated.html
```
- 49 papers, 7 pockets, 1,176 conexiones
- Network interactivo (49 nodos)
- Filtros en tiempo real
- 6 tabs: Overview, Pockets, Network, Analysis, Gaps, Data

**🔗 Demo Single Pocket**
```
http://localhost:8000/outputs/dashboard_v3.html
```
- 7 papers ejemplo
- Red interactiva (21 conexiones)
- Demostración de funcionalidad

---

## 🔄 Regenerar Pipeline (Opcional)

Si quieres actualizar papers o rerunear el análisis:

```bash
# Generar nuevos papers para todos los pockets
python scripts/generate_pocket_papers.py

# Ejecutar full pipeline (Reviewer → Synthesizer → Mapper)
python scripts/pipeline_orchestrator.py

# Servidor sigue corriendo automáticamente
```

---

## 📋 Estructura de Datos

### Archivos de Datos (21 total)

```
data/
├── consolidated_graph.json          [340 KB]
│   └── {nodes, edges, stats, gaps}
│
├── management_reviewed.json         [10 KB]
├── management_synthesized.json      [4.9 KB]
├── labor_reviewed.json              [11 KB]
├── labor_synthesized.json           [4.9 KB]
├── ... (5 más)
```

### Acceso a JSON desde navegador
```
http://localhost:8000/data/consolidated_graph.json
http://localhost:8000/data/management_reviewed.json
```

### Descargar desde terminal
```bash
curl http://localhost:8000/data/consolidated_graph.json > graph.json
```

---

## 🛠️ Solución de Problemas

### Problema: "Port 8000 already in use"

```bash
# Encontrar qué proceso usa el puerto
lsof -i :8000

# Matar el proceso
kill -9 <PID>

# O usar otro puerto
python -m http.server 8001
```

### Problema: Dashboard en blanco o sin datos

```bash
# Verificar que los archivos existen
ls -la data/*.json
ls -la outputs/*.html

# Reiniciar servidor
pkill -f "http.server"
python -m http.server 8000
```

### Problema: Gráficas no cargan

- Limpiar caché del navegador (Ctrl+Shift+Delete)
- Abrir en pestaña privada/incógnito
- Verificar conexión a internet (CDNs de Plotly, Vis.js)

### Problema: Network se mueve mucho

- El network ahora se estabiliza después de 5 segundos automáticamente
- Si aún hay movimiento, desactiva "Physics" en red (botón arriba derecha)

---

## 📈 Dashboard Features

### Tabs & Funcionalidad

| Tab | Features | Data |
|-----|----------|------|
| **Overview** | Tablas filtrables, métricas | 49 papers |
| **Pockets** | Estadísticas por pocket | 7 grupos |
| **Network** | Vis.js interactivo, 1,176 edges | Grafo completo |
| **Analysis** | 4 gráficas (score, año, pocket, metodología) | Distribuciones |
| **Gaps** | Coverage issues identificados | Por pocket |
| **Data** | Download botones para todos los JSON | 21 archivos |

### Filtros en Tiempo Real
- **Pocket**: 7 opciones + Todos
- **Status**: ACEPTADO, REVISAR
- **Score Mínimo**: Slider 0-10

### Interactividad
- Tabla: Click en headers para más info
- Network: Drag nodos, zoom con rueda, pan con click
- Gráficas: Hover para valores, click legend para toggle series

---

## 🔐 Seguridad & Privacidad

- ✅ Servidor corre localmente (localhost)
- ✅ Sin conexión a bases de datos externas
- ✅ Sin autenticación (acceso local solamente)
- ✅ Todos los datos en archivos JSON (inspectable)

**Nota**: Para servir públicamente en internet, requiere:
- HTTPS
- Autenticación
- Rate limiting
- CORS headers

---

## 💾 Backup & Recuperación

### Backup de datos
```bash
# Copiar carpeta data/
cp -r data/ data_backup_$(date +%Y%m%d)

# O zip
zip -r literatura_data.zip data/
```

### Restaurar datos
```bash
# Si se corrompieron archivos
rm data/*.json
# Regenerar con pipeline
python scripts/pipeline_orchestrator.py
```

---

## 📦 Para Compartir (Share Package)

Si quieres compartir el proyecto con otros:

```bash
# Crear archivo comprimido sin dependencias pesadas
zip -r literatura-review.zip \
  outputs/ \
  data/ \
  scripts/ \
  pockets_config.yaml \
  QUICK_START.sh \
  START_HERE.md \
  DEPLOYMENT.md \
  requirements.txt \
  -x "scripts/__pycache__/*" "*/.DS_Store"

# Compartir archivo (10-15 MB total)
# Receptor ejecuta: unzip literatura-review.zip && bash QUICK_START.sh
```

---

## 🌐 Para Deployment en Servidor (Futuro)

Si eventualmente quieres servir públicamente:

### Opción 1: Nginx + Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 \
  --directory outputs \
  http.server:WSGIRequestHandler
```

### Opción 2: Docker (Simple)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r scripts/requirements.txt
EXPOSE 8000
CMD ["python", "-m", "http.server", "8000"]
```

### Opción 3: Cloud Platforms
- **Vercel**: Soporta static files (outputs/)
- **Netlify**: Soporta static files
- **AWS S3 + CloudFront**: Distribución global
- **Heroku**: Para backend Python si agregamos API

---

## 📞 Support

### Verificar instalación
```bash
# Python version
python --version  # ≥3.8

# Dependencies
pip list | grep -E "networkx|plotly|pyyaml"

# Server
curl http://localhost:8000/outputs/dashboard_consolidated.html
```

### Logs
```bash
# Ver logs del servidor
# El servidor corre en foreground, logs en consola
# Para guardar en archivo:
python -m http.server 8000 > server.log 2>&1 &
tail -f server.log
```

---

## ✅ Checklist Pre-Deployment

- [ ] Python 3.8+ instalado
- [ ] `pip install -r scripts/requirements.txt` ejecutado
- [ ] Archivo `data/consolidated_graph.json` existe (340 KB)
- [ ] 7 archivos `[pocket]_reviewed.json` existen
- [ ] 4 archivos `.html` en `outputs/` existen
- [ ] Puerto 8000 disponible (`lsof -i :8000` vacío)
- [ ] Servidor inicia sin errores
- [ ] Dashboard carga en navegador
- [ ] Red con 49 nodos visible
- [ ] Filtros funcionan en tiempo real

---

## 📊 Performance

**Esperado al abrir dashboard**:
- Carga inicial: 2-3 segundos (cargar 49 papers)
- Filtros: <100ms por actualización
- Network render: 3-5 segundos (stabilización física)
- Cambiar tabs: <200ms

**Si es más lento**:
1. Limpiar caché navegador (Ctrl+Shift+Delete)
2. Desactivar extensiones
3. Verificar conexión a internet (CDNs)
4. Usar navegador moderno (Chrome/Firefox recomendado)

---

## 🎉 ¡Listo!

Dashboard deployado y accesible en:
```
http://localhost:8000/outputs/dashboard_consolidated.html
```

Para ayuda: Lee `START_HERE.md`

---

**Version**: 1.0  
**Last Updated**: 2026-04-13  
**Status**: Production Ready ✅
