"""
TestGen AI - FastAPI Backend Application
Complete test case generation system with context-aware LLM integration
"""

import os
import asyncio
import json
import zipfile
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update, delete
from pydantic import BaseModel, EmailStr, validator
from passlib.context import CryptContext
from jose import JWTError, jwt
import uvicorn

from context_aware_generator import ContextAwareTestGenerator, ContextExtractor

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://testgen:testgen123@localhost:5432/testgen_db")
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Initialize FastAPI app
app = FastAPI(
    title="TestGen AI API",
    description="AI-powered test case generation with context awareness",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
# Using simple hash for development - NOT for production!
import hashlib

# Database setup
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, generation_id: str):
        await websocket.accept()
        self.active_connections[generation_id] = websocket

    def disconnect(self, generation_id: str):
        if generation_id in self.active_connections:
            del self.active_connections[generation_id]

    async def send_progress(self, generation_id: str, data: dict):
        if generation_id in self.active_connections:
            try:
                await self.active_connections[generation_id].send_text(json.dumps(data))
            except:
                self.disconnect(generation_id)

manager = ConnectionManager()

# Database Models
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    api_quotas = Column(JSON, default={"openai": 1000, "anthropic": 1000})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    projects = relationship("Project", back_populates="user")
    integrations = relationship("UserIntegration", back_populates="user")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    application_url = Column(String)
    base_context = Column(JSON, default={})
    settings = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="projects")
    context_sources = relationship("ContextSource", back_populates="project")
    test_generations = relationship("TestGeneration", back_populates="project")

class ContextSource(Base):
    __tablename__ = "context_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    source_type = Column(String, nullable=False)  # jira, url, file
    source_config = Column(JSON, nullable=False)
    extracted_context = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship("Project", back_populates="context_sources")

class TestGeneration(Base):
    __tablename__ = "test_generations"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    feature_name = Column(String, nullable=False)
    config = Column(JSON, nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    generated_files = Column(JSON, default={})
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship("Project", back_populates="test_generations")

class UserIntegration(Base):
    __tablename__ = "user_integrations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    integration_type = Column(String, nullable=False)  # openai, anthropic, jira
    encrypted_credentials = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="integrations")

# Pydantic Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    api_quotas: Dict[str, int]
    created_at: datetime

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    application_url: Optional[str] = None
    base_context: Optional[Dict[str, Any]] = {}

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    application_url: Optional[str]
    base_context: Dict[str, Any]
    settings: Dict[str, Any]
    created_at: datetime
    context_sources_count: int = 0
    test_generations_count: int = 0

class ContextSourceCreate(BaseModel):
    source_type: str
    source_config: Dict[str, Any]

class ContextSourceResponse(BaseModel):
    id: int
    source_type: str
    source_config: Dict[str, Any]
    extracted_context: Dict[str, Any]
    created_at: datetime

class TestGenerationCreate(BaseModel):
    feature_name: str
    config: Dict[str, Any]

class TestGenerationResponse(BaseModel):
    id: int
    feature_name: str
    config: Dict[str, Any]
    status: str
    generated_files: Dict[str, Any]
    error_message: Optional[str]
    created_at: datetime

class IntegrationCreate(BaseModel):
    integration_type: str
    credentials: Dict[str, str]

# Database dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Authentication functions - using simple hash for development
def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Simple verification for development - NOT for production!
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

def get_password_hash(password: str) -> str:
    # Simple hash for development - NOT for production!
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)  # Convert string back to int
    except (JWTError, ValueError):
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

# Create dummy user for development
async def create_dummy_user(db: AsyncSession):
    """Create a dummy user for development/testing purposes"""
    try:
        # Check if dummy user already exists
        result = await db.execute(select(User).where(User.email == "demo@testgen.ai"))
        existing_user = result.scalar_one_or_none()
        
        if existing_user is None:
            # Create dummy user with simple password hash for now
            hashed_password = get_password_hash("demo123")
            dummy_user = User(
                email="demo@testgen.ai",
                password_hash=hashed_password,
                full_name="Demo User"
            )
            db.add(dummy_user)
            await db.commit()
            await db.refresh(dummy_user)
            print(f"✅ Created dummy user: demo@testgen.ai (password: demo123)")
        else:
            print(f"ℹ️  Dummy user already exists: demo@testgen.ai")
    except Exception as e:
        print(f"❌ Error creating dummy user: {e}")
        import traceback
        traceback.print_exc()

# API Endpoints

@app.get("/api/debug/users")
async def debug_users(db: AsyncSession = Depends(get_db)):
    """Debug endpoint to check users in database"""
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"id": u.id, "email": u.email, "full_name": u.full_name} for u in users]

@app.post("/api/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return UserResponse(
        id=db_user.id,
        email=db_user.email,
        full_name=db_user.full_name,
        api_quotas=db_user.api_quotas,
        created_at=db_user.created_at
    )

@app.post("/api/auth/login")
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    # Find user
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            api_quotas=user.api_quotas,
            created_at=user.created_at
        )
    }

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        api_quotas=current_user.api_quotas,
        created_at=current_user.created_at
    )

# Projects endpoints
@app.get("/api/projects", response_model=List[ProjectResponse])
async def get_projects(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project)
        .where(Project.user_id == current_user.id)
        .options(selectinload(Project.context_sources), selectinload(Project.test_generations))
    )
    projects = result.scalars().all()
    
    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            application_url=p.application_url,
            base_context=p.base_context,
            settings=p.settings,
            created_at=p.created_at,
            context_sources_count=len(p.context_sources),
            test_generations_count=len(p.test_generations)
        )
        for p in projects
    ]

@app.post("/api/projects", response_model=ProjectResponse)
async def create_project(project_data: ProjectCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    db_project = Project(
        user_id=current_user.id,
        name=project_data.name,
        description=project_data.description,
        application_url=project_data.application_url,
        base_context=project_data.base_context
    )
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    
    return ProjectResponse(
        id=db_project.id,
        name=db_project.name,
        description=db_project.description,
        application_url=db_project.application_url,
        base_context=db_project.base_context,
        settings=db_project.settings,
        created_at=db_project.created_at,
        context_sources_count=0,
        test_generations_count=0
    )

@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id, Project.user_id == current_user.id)
        .options(selectinload(Project.context_sources), selectinload(Project.test_generations))
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        application_url=project.application_url,
        base_context=project.base_context,
        settings=project.settings,
        created_at=project.created_at,
        context_sources_count=len(project.context_sources),
        test_generations_count=len(project.test_generations)
    )

# Context sources endpoints
@app.get("/api/projects/{project_id}/contexts", response_model=List[ContextSourceResponse])
async def get_context_sources(project_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Verify project ownership
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == current_user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")
    
    result = await db.execute(select(ContextSource).where(ContextSource.project_id == project_id))
    sources = result.scalars().all()
    
    return [
        ContextSourceResponse(
            id=s.id,
            source_type=s.source_type,
            source_config=s.source_config,
            extracted_context=s.extracted_context,
            created_at=s.created_at
        )
        for s in sources
    ]

@app.post("/api/projects/{project_id}/contexts", response_model=ContextSourceResponse)
async def create_context_source(
    project_id: int, 
    source_data: ContextSourceCreate, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    # Verify project ownership
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == current_user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Extract context based on source type
    extractor = ContextExtractor()
    extracted_context = {}
    
    try:
        if source_data.source_type == "jira":
            extracted_context = await extractor.extract_jira_context(source_data.source_config)
        elif source_data.source_type == "url":
            extracted_context = await extractor.extract_url_context(source_data.source_config)
        elif source_data.source_type == "file":
            extracted_context = await extractor.extract_file_context(source_data.source_config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Context extraction failed: {str(e)}")
    
    db_source = ContextSource(
        project_id=project_id,
        source_type=source_data.source_type,
        source_config=source_data.source_config,
        extracted_context=extracted_context
    )
    db.add(db_source)
    await db.commit()
    await db.refresh(db_source)
    
    return ContextSourceResponse(
        id=db_source.id,
        source_type=db_source.source_type,
        source_config=db_source.source_config,
        extracted_context=db_source.extracted_context,
        created_at=db_source.created_at
    )

# Test generation endpoints
@app.post("/api/projects/{project_id}/generations", response_model=TestGenerationResponse)
async def create_test_generation(
    project_id: int,
    generation_data: TestGenerationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify project ownership
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id, Project.user_id == current_user.id)
        .options(selectinload(Project.context_sources))
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create test generation record
    db_generation = TestGeneration(
        project_id=project_id,
        feature_name=generation_data.feature_name,
        config=generation_data.config,
        status="pending"
    )
    db.add(db_generation)
    await db.commit()
    await db.refresh(db_generation)
    
    # Start generation process in background
    asyncio.create_task(generate_tests_async(db_generation.id, project, generation_data.config, current_user, generation_data.feature_name))
    
    return TestGenerationResponse(
        id=db_generation.id,
        feature_name=db_generation.feature_name,
        config=db_generation.config,
        status=db_generation.status,
        generated_files=db_generation.generated_files,
        error_message=db_generation.error_message,
        created_at=db_generation.created_at
    )

async def generate_tests_async(generation_id: int, project: Project, config: dict, user: User, feature_name: str):
    """Background task for test generation"""
    async with AsyncSessionLocal() as db:
        try:
            # Update status to processing
            await db.execute(
                update(TestGeneration)
                .where(TestGeneration.id == generation_id)
                .values(status="processing")
            )
            await db.commit()
            
            # Send progress update
            await manager.send_progress(str(generation_id), {
                "status": "processing",
                "stage": "initializing",
                "progress": 10
            })
            
            # Get user integrations
            result = await db.execute(
                select(UserIntegration)
                .where(UserIntegration.user_id == user.id, UserIntegration.is_active == True)
            )
            integrations = result.scalars().all()
            
            # Initialize test generator with user integrations
            generator = ContextAwareTestGenerator(integrations=integrations)
            
            # Send progress update
            await manager.send_progress(str(generation_id), {
                "status": "processing",
                "stage": "extracting_context",
                "progress": 30
            })
            
            # Collect all context
            all_context = {
                "project_context": project.base_context,
                "context_sources": []
            }
            
            for source in project.context_sources:
                all_context["context_sources"].append({
                    "type": source.source_type,
                    "config": source.source_config,
                    "extracted": source.extracted_context
                })
            
            # Send progress update
            await manager.send_progress(str(generation_id), {
                "status": "processing",
                "stage": "generating_tests",
                "progress": 60
            })
            
            # Generate tests
            generated_files = await generator.generate_tests(
                feature_name=feature_name,
                context=all_context,
                config=config,
                integrations=integrations
            )
            
            # Send progress update
            await manager.send_progress(str(generation_id), {
                "status": "processing",
                "stage": "saving_files",
                "progress": 90
            })
            
            # Update generation record
            await db.execute(
                update(TestGeneration)
                .where(TestGeneration.id == generation_id)
                .values(
                    status="completed",
                    generated_files=generated_files
                )
            )
            await db.commit()
            
            # Send completion update
            await manager.send_progress(str(generation_id), {
                "status": "completed",
                "stage": "completed",
                "progress": 100,
                "files": generated_files
            })
            
        except Exception as e:
            # Update generation record with error
            await db.execute(
                update(TestGeneration)
                .where(TestGeneration.id == generation_id)
                .values(
                    status="failed",
                    error_message=str(e)
                )
            )
            await db.commit()
            
            # Send error update
            await manager.send_progress(str(generation_id), {
                "status": "failed",
                "error": str(e)
            })

@app.get("/api/projects/{project_id}/generations", response_model=List[TestGenerationResponse])
async def get_test_generations(project_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Verify project ownership
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == current_user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")
    
    result = await db.execute(select(TestGeneration).where(TestGeneration.project_id == project_id))
    generations = result.scalars().all()
    
    return [
        TestGenerationResponse(
            id=g.id,
            feature_name=g.feature_name,
            config=g.config,
            status=g.status,
            generated_files=g.generated_files,
            error_message=g.error_message,
            created_at=g.created_at
        )
        for g in generations
    ]

# WebSocket endpoint
@app.websocket("/ws/generation/{generation_id}")
async def websocket_endpoint(websocket: WebSocket, generation_id: str):
    await manager.connect(websocket, generation_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(generation_id)

# File download endpoints
@app.get("/api/generations/{generation_id}/download")
async def download_generation_files(generation_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Get generation
    result = await db.execute(
        select(TestGeneration)
        .join(Project)
        .where(TestGeneration.id == generation_id, Project.user_id == current_user.id)
    )
    generation = result.scalar_one_or_none()
    
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    if generation.status != "completed":
        raise HTTPException(status_code=400, detail="Generation not completed")
    
    # Create ZIP file
    zip_path = f"generated-tests/generation_{generation_id}.zip"
    os.makedirs("generated-tests", exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file_path, content in generation.generated_files.items():
            zipf.writestr(file_path, content)
    
    return FileResponse(
        zip_path,
        media_type='application/zip',
        filename=f"{generation.feature_name}_tests.zip"
    )

# Integrations endpoints
@app.get("/api/integrations")
async def get_integrations(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserIntegration)
        .where(UserIntegration.user_id == current_user.id)
    )
    integrations = result.scalars().all()
    
    return [
        {
            "id": i.id,
            "integration_type": i.integration_type,
            "is_active": i.is_active,
            "created_at": i.created_at
        }
        for i in integrations
    ]

@app.post("/api/integrations")
async def create_integration(
    integration_data: IntegrationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Simple encryption (in production, use proper encryption)
    encrypted_credentials = json.dumps(integration_data.credentials)
    
    db_integration = UserIntegration(
        user_id=current_user.id,
        integration_type=integration_data.integration_type,
        encrypted_credentials=encrypted_credentials
    )
    db.add(db_integration)
    await db.commit()
    await db.refresh(db_integration)
    
    return {
        "id": db_integration.id,
        "integration_type": db_integration.integration_type,
        "is_active": db_integration.is_active,
        "created_at": db_integration.created_at
    }

# Database initialization
@app.on_event("startup")
async def startup_event():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create generated-tests directory
    os.makedirs("generated-tests", exist_ok=True)
    
    # Create dummy user for development
    async with AsyncSessionLocal() as db:
        await create_dummy_user(db)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
