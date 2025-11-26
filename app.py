from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import uvicorn

from config import get_settings
from database import DatabaseManager
from extractor_lemas import ExtractorLemas
from analisis_engine import AnalisisEngine
from conversacion_manager import ConversacionManager
from models import (
    PreguntaRequest, 
    AnalisisResponse, 
    EstadisticasResponse,
    HealthResponse
)

# Configuración
settings = get_settings()

# Inicializar FastAPI
app = FastAPI(
    title="OnBotGo Analytics Agent",
    description="Agente conversacional para análisis de transcripciones de cobranza",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción: especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instancias globales
db_manager = DatabaseManager()
extractor = ExtractorLemas()
analisis_engine = AnalisisEngine()
conversacion_manager = ConversacionManager(max_history=settings.CONVERSATION_HISTORY_LIMIT)

# ============================================
# ENDPOINTS
# ============================================

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    
    # Verificar conexiones
    db_ok = db_manager.test_connection()
    
    # Verificar Ollama
    import requests
    ollama_ok = False
    try:
        response = requests.get(f"{settings.OLLAMA_HOST}/api/tags", timeout=2)
        ollama_ok = response.status_code == 200
    except:
        pass
    
    return HealthResponse(
        status="healthy" if db_ok and ollama_ok else "degraded",
        timestamp=datetime.now().isoformat(),
        database=db_ok,
        ollama=ollama_ok
    )

@app.post("/api/preguntar", response_model=AnalisisResponse)
async def preguntar(request: PreguntaRequest):
    """
    Endpoint principal: recibe pregunta y retorna análisis
    """
    
    try:
        # 1. Extraer lema y contexto
        analisis_pregunta = extractor.analizar_pregunta(request.pregunta)
        
        if not analisis_pregunta['lema']:
            return AnalisisResponse(
                success=False,
                respuesta_conversacional="No pude identificar un tema específico en tu pregunta. "
                                        "¿Podrías reformularla? Por ejemplo: 'Analiza los casos de juicio este mes'"
            )
        
        # 2. Ejecutar análisis
        resultado_analisis = analisis_engine.analizar_lema(
            lema=analisis_pregunta['lema'],
            periodo=analisis_pregunta.get('periodo')
        )
        
        if not resultado_analisis['success']:
            return AnalisisResponse(
                success=False,
                respuesta_conversacional=f"No encontré datos para '{analisis_pregunta['lema']}'. "
                                        f"Intenta con: juicio, alquiler, pago, trabajo, deuda."
            )
        
        # 3. Actualizar contexto conversacional
        conversacion_manager.agregar_mensaje(
            session_id=request.session_id,
            mensaje=request.pregunta,
            tipo='usuario'
        )
        
        conversacion_manager.actualizar_contexto(
            session_id=request.session_id,
            lema=analisis_pregunta['lema'],
            periodo=analisis_pregunta.get('periodo'),
            ultimo_analisis=resultado_analisis
        )
        
        # 4. Generar respuesta conversacional
        respuesta_conversacional = _generar_respuesta_conversacional(
            analisis_pregunta['lema'],
            resultado_analisis
        )
        
        conversacion_manager.agregar_mensaje(
            session_id=request.session_id,
            mensaje=respuesta_conversacional,
            tipo='agente',
            metadata={'lema': analisis_pregunta['lema']}
        )
        
        # 5. Retornar respuesta completa
        return AnalisisResponse(
            success=True,
            lema=analisis_pregunta['lema'],
            periodo=analisis_pregunta.get('periodo'),
            datos=resultado_analisis['datos'],
            insights=resultado_analisis['insights'],
            query_ejecutada=resultado_analisis['query_ejecutada'],
            contexto=conversacion_manager.obtener_contexto(request.session_id),
            respuesta_conversacional=respuesta_conversacional
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/estadisticas", response_model=EstadisticasResponse)
async def obtener_estadisticas():
    """Obtiene estadísticas generales de la base de datos"""
    
    try:
        resultado = analisis_engine.estadisticas_generales()
        return EstadisticasResponse(**resultado)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sesion/{session_id}/historial")
async def obtener_historial(session_id: str, limit: int = 10):
    """Obtiene el historial de una sesión"""
    
    historial = conversacion_manager.obtener_historial(session_id, limit)
    
    return {
        'session_id': session_id,
        'historial': historial,
        'total_mensajes': len(historial)
    }

@app.delete("/api/sesion/{session_id}")
async def limpiar_sesion(session_id: str):
    """Limpia una sesión conversacional"""
    
    conversacion_manager.limpiar_sesion(session_id)
    
    return {
        'success': True,
        'message': f'Sesión {session_id} limpiada'
    }

@app.get("/api/lemas-disponibles")
async def lemas_disponibles():
    """Lista de lemas conocidos por el sistema"""
    
    return {
        'lemas': list(extractor.cache_lemas.keys()),
        'total': len(extractor.cache_lemas)
    }

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def _generar_respuesta_conversacional(lema: str, resultado: dict) -> str:
    """Genera respuesta en lenguaje natural"""
    
    insights = resultado.get('insights', [])
    datos = resultado.get('datos', {})
    
    respuesta = f"📊 **Análisis de '{lema}'**\n\n"
    
    # Agregar insights
    if insights:
        for insight in insights:
            respuesta += f"• {insight}\n"
    
    # Resumen de datos
    if 'temas' in datos and datos['temas']:
        total_casos = sum(t['frecuencia'] for t in datos['temas'])
        respuesta += f"\n**Total de casos encontrados:** {total_casos}\n"
    
    respuesta += "\n💡 *Puedes pedirme más detalles o hacer otra pregunta.*"
    
    return respuesta

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD
    )
