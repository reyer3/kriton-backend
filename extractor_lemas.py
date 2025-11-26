import requests
import json
import re
from datetime import datetime
from typing import Optional, Dict, List
import google.generativeai as genai
from config import get_settings

settings = get_settings()

class ExtractorLemas:
    """
    Extrae lemas y contexto de preguntas usando Ollama
    """
    
    def __init__(self):
        self.ollama_url = settings.OLLAMA_HOST
        self.ollama_model = settings.OLLAMA_MODEL
        
        self.provider = settings.LLM_PROVIDER
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.gemini_model_name = settings.GEMINI_MODEL
        
        if self.provider == 'gemini' and self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel(self.gemini_model_name)
        
        # Cache de lemas comunes (respuesta instantánea)
        self.cache_lemas = {
            'alquiler': ['alquileres', 'renta', 'arriendo', 'alquilar'],
            'juicio': ['juicios', 'demanda', 'demandas', 'legal', 'abogado', 'judicial'],
            'pago': ['pagos', 'pagar', 'abonar', 'cancelar', 'saldar', 'abono'],
            'trabajo': ['empleo', 'desempleo', 'laboral', 'trabajando', 'empleado'],
            'deuda': ['deudas', 'debe', 'adeuda', 'prestamo', 'crédito', 'préstamo'],
            'telefono': ['teléfono', 'llamada', 'llamadas', 'contacto', 'comunicación'],
            'promesa': ['promesas', 'compromiso', 'comprometió', 'acordar']
        }
    
    def buscar_en_cache(self, pregunta: str) -> Optional[str]:
        """Búsqueda rápida en cache"""
        pregunta_lower = pregunta.lower()
        
        for lema_base, variantes in self.cache_lemas.items():
            for variante in variantes + [lema_base]:
                if variante in pregunta_lower:
                    return lema_base
        
        return None
    
    def extraer_periodo_temporal(self, pregunta: str) -> Optional[Dict]:
        """Extrae referencias temporales"""
        pregunta_lower = pregunta.lower()
        
        # Este mes
        if any(x in pregunta_lower for x in ['este mes', 'mes actual', 'del mes']):
            return {
                'tipo': 'mes',
                'valor': datetime.now().strftime('%Y-%m'),
                'filtro_sql': f"DATE_TRUNC('month', fecha::date) = '{datetime.now().strftime('%Y-%m')}-01'::date"
            }
        
        # Mes pasado
        if any(x in pregunta_lower for x in ['mes pasado', 'último mes', 'anterior']):
            from datetime import timedelta
            mes_pasado = (datetime.now() - timedelta(days=30)).strftime('%Y-%m')
            return {
                'tipo': 'mes',
                'valor': mes_pasado,
                'filtro_sql': f"DATE_TRUNC('month', fecha::date) = '{mes_pasado}-01'::date"
            }
        
        # Meses específicos
        meses_map = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }
        
        for mes_nombre, mes_num in meses_map.items():
            if mes_nombre in pregunta_lower:
                año = datetime.now().year
                return {
                    'tipo': 'mes',
                    'valor': f'{año}-{mes_num}',
                    'filtro_sql': f"DATE_TRUNC('month', fecha::date) = '{año}-{mes_num}-01'::date"
                }
        
        return None
    
    def extraer_con_llm(self, pregunta: str) -> Dict:
        """Extrae lema usando el proveedor configurado"""
        
        if self.provider == 'gemini':
            return self._extraer_con_gemini(pregunta)
        else:
            return self._extraer_con_ollama(pregunta)

    def _extraer_con_gemini(self, pregunta: str) -> Dict:
        """Extrae lema usando Google Gemini"""
        if not self.gemini_api_key:
            print("Error: GEMINI_API_KEY no configurada")
            return None
            
        prompt = self._construir_prompt(pregunta)
        
        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1
                )
            )
            
            respuesta_texto = response.text.strip()
            # Limpiar markdown si existe
            respuesta_texto = respuesta_texto.replace('```json', '').replace('```', '').strip()
            
            try:
                return json.loads(respuesta_texto)
            except:
                match = re.search(r'"lema":\s*"([^"]+)"', respuesta_texto)
                if match:
                    return {"lema": match.group(1), "confianza": 0.7}
                    
        except Exception as e:
            print(f"Error llamando a Gemini: {e}")
            
        return None

    def _extraer_con_ollama(self, pregunta: str) -> Dict:
        """Extrae lema usando Ollama"""
        
        prompt = self._construir_prompt(pregunta)

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 50
                    }
                },
                timeout=10
            )
            
            if response.status_code == 200:
                resultado = response.json()
                respuesta_texto = resultado['response'].strip()
                
                try:
                    return json.loads(respuesta_texto)
                except:
                    # Fallback con regex
                    match = re.search(r'"lema":\s*"([^"]+)"', respuesta_texto)
                    if match:
                        return {"lema": match.group(1), "confianza": 0.7}
        
        except Exception as e:
            print(f"Error llamando a Ollama: {e}")
        
        return None

    def _construir_prompt(self, pregunta: str) -> str:
        return f"""Analiza esta pregunta sobre transcripciones de cobranza.

PREGUNTA: "{pregunta}"

CONTEXTO: Transcripciones con temas como:
- alquiler (pagos de alquiler/renta)
- juicio (temas legales, demandas, abogados)
- pago (pagos, deudas, préstamos)
- trabajo (empleo, desempleo, situación laboral)
- promesa (promesas de pago, compromisos)

Responde SOLO este JSON (sin markdown, sin explicaciones):
{{
  "lema": "palabra_clave",
  "confianza": 0.95
}}

Reglas:
- lema en SINGULAR
- Corregir errores ortográficos
- Una sola palabra clave principal"""
    
    def analizar_pregunta(self, pregunta: str) -> Dict:
        """
        Análisis completo de la pregunta
        """
        # Intento 1: Cache (instantáneo)
        lema_cache = self.buscar_en_cache(pregunta)
        
        if lema_cache:
            return {
                'lema': lema_cache,
                'periodo': self.extraer_periodo_temporal(pregunta),
                'metodo': 'cache',
                'confianza': 1.0
            }
        
        # Intento 2: LLM local
        resultado_llm = self.extraer_con_llm(pregunta)
        
        if resultado_llm:
            return {
                'lema': resultado_llm['lema'],
                'periodo': self.extraer_periodo_temporal(pregunta),
                'metodo': 'llm',
                'confianza': resultado_llm.get('confianza', 0.8)
            }
        
        return {
            'lema': None,
            'periodo': self.extraer_periodo_temporal(pregunta),
            'metodo': 'fallback',
            'confianza': 0.0
        }
