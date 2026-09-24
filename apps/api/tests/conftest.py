from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_maker = async_sessionmaker(
        bind=db_engine, expire_on_commit=False, autoflush=False
    )
    async with session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine, db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    # Background tasks (document extraction, AI analysis) open their own
    # session via `AsyncSessionLocal` imported directly into those service
    # modules — FastAPI's dependency override above doesn't reach them.
    # Point those at a session factory bound to the SAME in-memory SQLite
    # engine (StaticPool keeps one shared connection) so a background task
    # sees data the test's request session already committed.
    background_session_maker = async_sessionmaker(
        bind=db_engine, expire_on_commit=False, autoflush=False
    )
    import app.services.analysis as analysis_module
    import app.services.clauserisk.pipeline as clauserisk_pipeline_module
    import app.services.document as document_module

    original_document_session = document_module.AsyncSessionLocal
    original_analysis_session = analysis_module.AsyncSessionLocal
    original_clauserisk_session = clauserisk_pipeline_module.AsyncSessionLocal
    document_module.AsyncSessionLocal = background_session_maker
    analysis_module.AsyncSessionLocal = background_session_maker
    clauserisk_pipeline_module.AsyncSessionLocal = background_session_maker

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    document_module.AsyncSessionLocal = original_document_session
    analysis_module.AsyncSessionLocal = original_analysis_session
    clauserisk_pipeline_module.AsyncSessionLocal = original_clauserisk_session
    app.dependency_overrides.clear()


@pytest.fixture
def clauserisk_fake_provider(monkeypatch):
    """Patches the ClauseRisk pipeline's provider factory so tests exercise
    the real pipeline (segmentation, cross-linking, deterministic
    validation, risk scoring, persistence) against canned, deterministic
    AI output instead of a live Ollama/Claude call — fast and CI-safe,
    same rationale as TenderGuard's approach to AI-dependent tests."""
    from tests.clauserisk_fakes import FakeClauseRiskProvider

    provider = FakeClauseRiskProvider()
    monkeypatch.setattr(
        "app.services.clauserisk.pipeline.get_clauserisk_ai_provider", lambda: provider
    )
    return provider


@pytest.fixture
def tenderguard_fake_provider(monkeypatch):
    """Patches TenderGuard's analysis provider factory so tests exercise
    the real pipeline against canned, deterministic AI output instead of
    a live Claude call — same rationale as clauserisk_fake_provider above."""
    from tests.tenderguard_fakes import FakeTenderGuardProvider

    provider = FakeTenderGuardProvider()
    monkeypatch.setattr("app.services.analysis.get_ai_provider", lambda: provider)
    return provider


@pytest.fixture
def registration_payload():
    return {
        "email": "bidmanager@example.com",
        "password": "SecurePass123",
        "full_name": "Jordan Bidmanager",
        "organization_name": "Example Contracting LLC",
        "industry": "Oil & Gas",
        "country": "UAE",
    }
