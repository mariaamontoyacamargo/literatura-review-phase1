#!/bin/bash

# ============================================================================
# QUICK START - Literatura Review Pipeline
# Inicia el dashboard en http://localhost:8000
# ============================================================================

set -e

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║  📚 Literatura Review Dashboard - Quick Start                      ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Check Python
echo "🐍 Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no encontrado. Instala Python 3.8+"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION encontrado"
echo ""

# Check dependencies (solo first time)
echo "📦 Verificando dependencias..."
if ! python3 -c "import plotly, networkx" 2>/dev/null; then
    echo "   Instalando dependencias (primera vez)..."
    pip install -q -r scripts/requirements.txt
    echo "✅ Dependencias instaladas"
else
    echo "✅ Dependencias ya instaladas"
fi
echo ""

# Check data files
echo "📁 Verificando archivos..."
if [ ! -f "data/consolidated_graph.json" ]; then
    echo "❌ Archivos de datos no encontrados"
    echo "   Ejecuta: python scripts/pipeline_orchestrator.py"
    exit 1
fi
echo "✅ 49 papers encontrados (data/consolidated_graph.json)"
echo "✅ Dashboards encontrados (outputs/*.html)"
echo ""

# Kill any existing server on port 8000
if lsof -i :8000 >/dev/null 2>&1; then
    echo "🔄 Deteniendo servidor anterior en puerto 8000..."
    pkill -f "http.server 8000" 2>/dev/null || true
    sleep 1
fi

# Start server
echo "🚀 Iniciando servidor en puerto 8000..."
cd "$(dirname "$0")"
python3 -m http.server 8000 > /tmp/http_server.log 2>&1 &
SERVER_PID=$!
sleep 2

# Verify server started
if ! lsof -i :8000 >/dev/null 2>&1; then
    echo "❌ Servidor falló. Check log:"
    cat /tmp/http_server.log
    exit 1
fi

echo "✅ Servidor corriendo (PID: $SERVER_PID)"
echo ""

# Display info
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║  ✨ LISTO! Dashboard disponible en:                               ║"
echo "║                                                                    ║"
echo "║  📊 http://localhost:8000/outputs/dashboard_consolidated.html     ║"
echo "║                                                                    ║"
echo "║  Características:                                                  ║"
echo "║  • 49 papers | 7 pockets | 1,176 conexiones                       ║"
echo "║  • Network interactivo (49 nodos)                                 ║"
echo "║  • 6 tabs: Overview, Pockets, Network, Analysis, Gaps, Data       ║"
echo "║  • Filtros en tiempo real                                         ║"
echo "║                                                                    ║"
echo "║  Para detener: presiona Ctrl+C                                    ║"
echo "║  Para ayuda: abre START_HERE.md                                   ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Try to open browser (macOS)
if command -v open >/dev/null; then
    echo "🌐 Abriendo navegador..."
    open "http://localhost:8000/outputs/dashboard_consolidated.html" &
fi

# Try to open browser (Linux)
if command -v xdg-open >/dev/null; then
    echo "🌐 Abriendo navegador..."
    xdg-open "http://localhost:8000/outputs/dashboard_consolidated.html" &
fi

# Keep server running
echo ""
echo "📡 Servidor activo. Para detener presiona Ctrl+C"
echo ""
wait $SERVER_PID
