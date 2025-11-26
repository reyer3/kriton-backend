from typing import List, Dict, Optional
from datetime import datetime
import json

class ConversacionManager:
    """
    Maneja el contexto conversacional y memoria del agente
    """
    
    def __init__(self, max_history: int = 10):
        self.conversations = {}  # session_id -> historial
        self.max_history = max_history
    
    def crear_sesion(self, session_id: str) -> None:
        """Crea una nueva sesión conversacional"""
        self.conversations[session_id] = {
            'historial': [],
            'contexto': {},
            'created_at': datetime.now().isoformat()
        }
    
    def agregar_mensaje(
        self, 
        session_id: str, 
        mensaje: str, 
        tipo: str = 'usuario',
        metadata: Dict = None
    ) -> None:
        """Agrega un mensaje al historial"""
        
        if session_id not in self.conversations:
            self.crear_sesion(session_id)
        
        self.conversations[session_id]['historial'].append({
            'timestamp': datetime.now().isoformat(),
            'tipo': tipo,
            'mensaje': mensaje,
            'metadata': metadata or {}
        })
        
        # Limitar historial
        if len(self.conversations[session_id]['historial']) > self.max_history:
            self.conversations[session_id]['historial'] = \
                self.conversations[session_id]['historial'][-self.max_history:]
    
    def actualizar_contexto(
        self, 
        session_id: str, 
        lema: str = None,
        periodo: Dict = None,
        ultimo_analisis: Dict = None
    ) -> None:
        """Actualiza el contexto de la conversación"""
        
        if session_id not in self.conversations:
            self.crear_sesion(session_id)
        
        contexto = self.conversations[session_id]['contexto']
        
        if lema:
            contexto['ultimo_lema'] = lema
        
        if periodo:
            contexto['ultimo_periodo'] = periodo
        
        if ultimo_analisis:
            contexto['ultimo_analisis'] = ultimo_analisis
    
    def obtener_contexto(self, session_id: str) -> Dict:
        """Obtiene el contexto actual"""
        
        if session_id not in self.conversations:
            return {}
        
        return self.conversations[session_id]['contexto']
    
    def obtener_historial(self, session_id: str, limit: int = 5) -> List[Dict]:
        """Obtiene el historial reciente"""
        
        if session_id not in self.conversations:
            return []
        
        historial = self.conversations[session_id]['historial']
        return historial[-limit:] if limit else historial
    
    def generar_resumen(self, session_id: str) -> str:
        """Genera un resumen de la conversación"""
        
        if session_id not in self.conversations:
            return "No hay conversación activa."
        
        historial = self.conversations[session_id]['historial']
        contexto = self.conversations[session_id]['contexto']
        
        resumen = f"Conversación iniciada: {self.conversations[session_id]['created_at']}\n"
        resumen += f"Mensajes intercambiados: {len(historial)}\n"
        
        if 'ultimo_lema' in contexto:
            resumen += f"Último lema analizado: {contexto['ultimo_lema']}\n"
        
        return resumen
    
    def limpiar_sesion(self, session_id: str) -> None:
        """Limpia una sesión"""
        if session_id in self.conversations:
            del self.conversations[session_id]
