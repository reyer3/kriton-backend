from typing import Dict, Optional, List
import json

class QueryGenerator:
    """
    Genera queries SQL dinámicas basadas en análisis de preguntas
    """
    
    @staticmethod
    def generar_analisis_lema(
        lema: str, 
        periodo: Optional[Dict] = None,
        limite: int = 20
    ) -> str:
        """
        Genera query para análisis de lema
        """
        
        query = f"""
-- Análisis del lema: {lema}
WITH casos_filtrados AS (
    SELECT 
        uid,
        fecha::date as fecha,
        region,
        supervisor,
        temas_detectados,
        duracion_seg,
        lemas,
        similarity(lemas, '{lema}') as score
    FROM transcripciones_procesadas
    WHERE similarity(lemas, '{lema}') > 0.4
"""
        
        # Agregar filtro temporal si existe
        if periodo and periodo.get('filtro_sql'):
            query += f"      AND {periodo['filtro_sql']}\n"
        
        query += f"""),
agregacion_temas AS (
    SELECT 
        temas_detectados,
        COUNT(*) as frecuencia,
        AVG(duracion_seg) as duracion_promedio,
        AVG(score) as similitud_promedio
    FROM casos_filtrados
    GROUP BY temas_detectados
    ORDER BY frecuencia DESC
    LIMIT {limite}
),
distribucion_temporal AS (
    SELECT 
        DATE_TRUNC('month', fecha) as mes,
        COUNT(*) as casos,
        AVG(duracion_seg) as duracion_promedio
    FROM casos_filtrados
    GROUP BY DATE_TRUNC('month', fecha)
    ORDER BY mes
)
SELECT 
    'temas' as tipo_resultado,
    json_agg(
        json_build_object(
            'temas', temas_detectados,
            'frecuencia', frecuencia,
            'duracion_promedio', ROUND(duracion_promedio::numeric, 2),
            'similitud', ROUND(similitud_promedio::numeric, 3)
        ) ORDER BY frecuencia DESC
    ) as datos
FROM agregacion_temas

UNION ALL

SELECT 
    'temporal' as tipo_resultado,
    json_agg(
        json_build_object(
            'mes', mes::text,
            'casos', casos,
            'duracion_promedio', ROUND(duracion_promedio::numeric, 2)
        ) ORDER BY mes
    ) as datos
FROM distribucion_temporal;
"""
        
        return query
    
    @staticmethod
    def generar_comparacion_periodos(
        lema: str,
        periodo1: str,
        periodo2: str
    ) -> str:
        """
        Compara dos períodos para un lema
        """
        
        query = f"""
-- Comparación: {lema} entre {periodo1} y {periodo2}
WITH periodo_1 AS (
    SELECT 
        COUNT(*) as casos,
        AVG(duracion_seg) as duracion_promedio,
        '{periodo1}' as periodo
    FROM transcripciones_procesadas
    WHERE similarity(lemas, '{lema}') > 0.4
      AND DATE_TRUNC('month', fecha::date) = '{periodo1}-01'::date
),
periodo_2 AS (
    SELECT 
        COUNT(*) as casos,
        AVG(duracion_seg) as duracion_promedio,
        '{periodo2}' as periodo
    FROM transcripciones_procesadas
    WHERE similarity(lemas, '{lema}') > 0.4
      AND DATE_TRUNC('month', fecha::date) = '{periodo2}-01'::date
)
SELECT 
    periodo,
    casos,
    ROUND(duracion_promedio::numeric, 2) as duracion_promedio,
    ROUND(
        100.0 * (casos - LAG(casos) OVER (ORDER BY periodo)) / 
        NULLIF(LAG(casos) OVER (ORDER BY periodo), 0),
        2
    ) as variacion_porcentual
FROM (
    SELECT * FROM periodo_1
    UNION ALL
    SELECT * FROM periodo_2
) combined
ORDER BY periodo;
"""
        
        return query
    
    @staticmethod
    def generar_top_supervisores(
        lema: str,
        limite: int = 10
    ) -> str:
        """
        Top supervisores por lema
        """
        
        query = f"""
-- Top supervisores: {lema}
SELECT 
    supervisor,
    COUNT(*) as casos,
    AVG(duracion_seg) as duracion_promedio,
    ROUND(AVG(similarity(lemas, '{lema}'))::numeric, 3) as similitud_promedio
FROM transcripciones_procesadas
WHERE similarity(lemas, '{lema}') > 0.4
  AND supervisor IS NOT NULL
GROUP BY supervisor
ORDER BY casos DESC
LIMIT {limite};
"""
        
        return query
    
    @staticmethod
    def generar_estadisticas_generales() -> str:
        """
        Estadísticas generales de la tabla
        """
        
        query = """
-- Estadísticas generales
SELECT 
    COUNT(*) as total_registros,
    COUNT(DISTINCT fecha::date) as dias_unicos,
    MIN(fecha::date) as fecha_min,
    MAX(fecha::date) as fecha_max,
    COUNT(DISTINCT region) as regiones,
    COUNT(DISTINCT supervisor) as supervisores,
    ROUND(AVG(duracion_seg)::numeric, 2) as duracion_promedio,
    ROUND(AVG(num_turnos_cliente)::numeric, 2) as turnos_promedio
FROM transcripciones_procesadas;
"""
        
        return query
