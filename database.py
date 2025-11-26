from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import pandas as pd
from config import get_settings

settings = get_settings()

DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db():
    """Context manager para sesión de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class DatabaseManager:
    """Maneja operaciones de base de datos"""
    
    @staticmethod
    def execute_query(query: str, params: dict = None) -> pd.DataFrame:
        """
        Ejecuta query y retorna DataFrame
        """
        with get_db() as db:
            try:
                result = db.execute(text(query), params or {})
                
                # Convertir a DataFrame
                if result.returns_rows:
                    columns = result.keys()
                    data = result.fetchall()
                    return pd.DataFrame(data, columns=columns)
                
                return pd.DataFrame()
            
            except Exception as e:
                raise Exception(f"Error ejecutando query: {str(e)}")
    
    @staticmethod
    def test_connection() -> bool:
        """Prueba conexión a la base de datos"""
        try:
            with get_db() as db:
                db.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"Error de conexión: {e}")
            return False
    
    @staticmethod
    def get_table_stats() -> dict:
        """Obtiene estadísticas de la tabla"""
        query = """
        SELECT 
            COUNT(*) as total_registros,
            COUNT(DISTINCT fecha) as dias_unicos,
            MIN(fecha::date) as fecha_min,
            MAX(fecha::date) as fecha_max,
            COUNT(DISTINCT region) as regiones,
            COUNT(DISTINCT supervisor) as supervisores
        FROM transcripciones_procesadas
        """
        
        df = DatabaseManager.execute_query(query)
        return df.to_dict('records')[0] if not df.empty else {}
    
    @staticmethod
    def buscar_por_similitud(lema: str, umbral: float = 0.4, limite: int = 100) -> pd.DataFrame:
        """
        Búsqueda por similitud de lemas usando pg_trgm
        """
        query = """
        SELECT 
            uid,
            fecha,
            region,
            supervisor,
            temas_detectados,
            duracion_seg,
            lemas,
            similarity(lemas, :lema) as score
        FROM transcripciones_procesadas
        WHERE similarity(lemas, :lema) > :umbral
        ORDER BY score DESC
        LIMIT :limite
        """
        
        params = {
            'lema': lema,
            'umbral': umbral,
            'limite': limite
        }
        
        return DatabaseManager.execute_query(query, params)
