from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime

class PreguntaRequest(BaseModel):
    pregunta: str = Field(..., description="Pregunta del usuario")
    session_id: str = Field(default="default", description="ID de sesión")

class AnalisisResponse(BaseModel):
    success: bool
    lema: Optional[str] = None
    periodo: Optional[Dict] = None
    datos: Optional[Dict[str, Any]] = None
    insights: Optional[List[str]] = None
    query_ejecutada: Optional[str] = None
    contexto: Optional[Dict] = None
    respuesta_conversacional: Optional[str] = None

class EstadisticasResponse(BaseModel):
    success: bool
    estadisticas: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    database: bool
    ollama: bool
