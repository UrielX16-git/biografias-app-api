from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# --- 1. CONFIGURACIÓN DE BASE DE DATOS (SQLAlchemy) ---
DATABASE_URL = "sqlite:///./biografias.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 2. MODELO DE BASE DE DATOS (Entidad) ---
class PersonajeDB(Base):
    __tablename__ = "personajes"
    id = Column(Integer, primary_key=True, index=True)
    nombres = Column(String, index=True)
    lugar_nacimiento = Column(String)
    evento_historico = Column(String)
    dato_vida = Column(String)
    is_activo = Column(Boolean, default=True) # BORRADO LÓGICO

Base.metadata.create_all(bind=engine)

# --- 3. ESQUEMAS PYDANTIC (Para recibir y enviar JSON) ---
class PersonajeCreate(BaseModel):
    # No pedimos foto porque es local en Android
    nombres: str
    lugar_nacimiento: str
    evento_historico: str
    dato_vida: str

class PersonajeResponse(PersonajeCreate):
    id: int
    is_activo: bool
    class Config:
        from_attributes = True

# --- 4. INICIALIZAR FASTAPI ---
app = FastAPI(title="API de Biografías")

# Dependencia para obtener la sesión de la BD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 5. ENDPOINTS (RUTAS) ---

@app.post("/api/personajes", response_model=PersonajeResponse)
def crear_personaje(personaje: PersonajeCreate, db: Session = Depends(get_db)):
    db_personaje = PersonajeDB(**personaje.model_dump())
    db.add(db_personaje)
    db.commit()
    db.refresh(db_personaje)
    return db_personaje

@app.get("/api/personajes", response_model=list[PersonajeResponse])
def listar_personajes(busqueda: str = "", db: Session = Depends(get_db)):
    # Solo devolvemos los activos (is_activo == True)
    query = db.query(PersonajeDB).filter(PersonajeDB.is_activo == True)
    
    # Si hay texto de búsqueda, filtramos por nombre o evento
    if busqueda:
        query = query.filter(
            (PersonajeDB.nombres.contains(busqueda)) | 
            (PersonajeDB.evento_historico.contains(busqueda))
        )
    return query.all()

@app.delete("/api/personajes/{id}")
def eliminar_personaje_logico(id: int, db: Session = Depends(get_db)):
    personaje = db.query(PersonajeDB).filter(PersonajeDB.id == id).first()
    if not personaje:
        raise HTTPException(status_code=404, detail="Personaje no encontrado")
    
    # APLICAMOS EL BORRADO LÓGICO
    personaje.is_activo = False
    db.commit()
    return {"mensaje": "Personaje eliminado (lógicamente)"}
