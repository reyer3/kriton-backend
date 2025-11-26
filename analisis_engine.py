from typing import Dict, List, Any
import pandas as pd
import json
from database import DatabaseManager
from query_generator import QueryGenerator

class AnalisisEngine:
    """
    Motor de análisis que ejecuta queries y genera insights
    """
    
    def __init__(self):
        self.db = DatabaseManager()
        self.query_gen = QueryGenerator()
    
    def analizar_lema(
        self, 
        lema: str, 
        periodo: Dict = None
    ) -> Dict[str, Any]:
        """
        Ejecuta análisis completo de un lema
        """
        
        # Generar y ejecutar query
        query = self.query_gen.generar_analisis_lema(lema, periodo)
        df = self.db.execute_query(query)
        
        if df.empty:
            return {
                'success': False,
                'error': f'No se encontraron datos para el lema: {lema}'
            }
        
        # Parsear resultados
        resultados = {}
        for _, row in df.iterrows():
            tipo = row['tipo_resultado']
            datos = json.loads(row['datos']) if isinstance(row['datos'], str) else row['datos']
            resultados[tipo] = datos
        
        # Generar insights
        insights = self._generar_insights(lema, resultados, periodo)
        
        return {
            'success': True,
            'lema': lema,
            'periodo': periodo,
            'datos': resultados,
            'insights': insights,
            'query_ejecutada': query
        }
    
    def _generar_insights(
        self, 
        lema: str, 
        resultados: Dict, 
        periodo: Dict
    ) -> List[str]:
        """
        Genera insights automáticos basados en los datos
        """
        insights = []
        
        # Análisis de temas
        if 'temas' in resultados and resultados['temas']:
            temas = resultados['temas']
            total_casos = sum(t['frecuencia'] for t in temas)
            tema_principal = temas[0] if temas else None
            
            if tema_principal:
                porcentaje = (tema_principal['frecuencia'] / total_casos * 100) if total_casos > 0 else 0
                
                insights.append(
                    f"Se identificaron {total_casos} casos con el lema '{lema}'. "
                    f"El tema dominante es '{tema_principal['temas']}' con {tema_principal['frecuencia']} casos ({porcentaje:.1f}%)."
                )
                
                # Insight sobre duración
                if tema_principal['duracion_promedio'] > 300:
                    insights.append(
                        f"⚠️ Alerta: Duración promedio de {tema_principal['duracion_promedio']:.0f} segundos "
                        f"({tema_principal['duracion_promedio']/60:.1f} minutos) indica conversaciones complejas."
                    )
        
        # Análisis temporal
        if 'temporal' in resultados and resultados['temporal']:
            temporal = resultados['temporal']
            
            if len(temporal) >= 2:
                ultimo_mes = temporal[-1]
                penultimo_mes = temporal[-2]
                
                variacion = ((ultimo_mes['casos'] - penultimo_mes['casos']) / penultimo_mes['casos'] * 100) if penultimo_mes['casos'] > 0 else 0
                
                if abs(variacion) > 50:
                    emoji = "📈" if variacion > 0 else "📉"
                    insights.append(
                        f"{emoji} Tendencia: Variación de {variacion:+.1f}% respecto al mes anterior "
                        f"({penultimo_mes['casos']} → {ultimo_mes['casos']} casos)."
                    )
        
        # Insight sobre distribución
        if 'temas' in resultados and len(resultados['temas']) > 1:
            tema_secundario = resultados['temas'][1]
            insights.append(
                f"El segundo tema más frecuente es '{tema_secundario['temas']}' con "
                f"{tema_secundario['frecuencia']} casos."
            )
        
        return insights
    
    def comparar_periodos(
        self, 
        lema: str, 
        periodo1: str, 
        periodo2: str
    ) -> Dict[str, Any]:
        """
        Compara dos períodos
        """
        query = self.query_gen.generar_comparacion_periodos(lema, periodo1, periodo2)
        df = self.db.execute_query(query)
        
        if df.empty:
            return {'success': False, 'error': 'No hay datos para comparar'}
        
        return {
            'success': True,
            'lema': lema,
            'comparacion': df.to_dict('records'),
            'query_ejecutada': query
        }
    
    def estadisticas_generales(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas generales
        """
        query = self.query_gen.generar_estadisticas_generales()
        df = self.db.execute_query(query)
        
        if df.empty:
            return {'success': False, 'error': 'No hay datos disponibles'}
        
        stats = df.to_dict('records')[0]
        
        return {
            'success': True,
            'estadisticas': stats
        }
