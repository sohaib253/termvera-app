import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.base import utcnow
from app.db.session import AsyncSessionLocal
from app.models.assessment import Assessment
from app.models.document import Document, DocumentPage, DocumentType, ExtractionStatus
from app.models.evidence import EvidenceRecord
from app.models.project import AnalysisStatus, Project
from app.models.requirement import Requirement
from app.schemas.ai import ExtractedRequirement
from app.services.ai.claude_provider import (
    COMPLIANCE_ASSESSMENT_VERSION,
    REQUIREMENT_EXTRACTION_VERSION,
    ClaudeProvider,
)
from app.services.ai.provider import AIProvider, AIProviderError, PageText
from app.services.priority import compute_priority
from app.services.text_verification import excerpt_is_verifiable

logger = logging.getLogger("tenderguard.analysis")


class AnalysisPreconditionError(Exception):
    pass


def get_ai_provider() -> AIProvider | None:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    return ClaudeProvider(api_key=settings.anthropic_api_key, model=settings.anthropic_model)


def _excerpt_is_verifiable(excerpt: str, page_texts: dict[int, str], page_number: int) -> bool:
    page_text = page_texts.get(page_number)
    if page_text is None:
        return False
    return excerpt_is_verifiable(excerpt, page_text)


async def check_analysis_preconditions(db: AsyncSession, *, organization_id: str, project_id: str) -> None:
    project = await db.get(Project, project_id)
    if project is None or project.organization_id != organization_id:
        raise AnalysisPreconditionError("Project not found.")

    tender_docs = (
        await db.scalars(
            select(Document).where(
                Document.project_id == project_id,
                Document.document_type == DocumentType.TENDER,
                Document.extraction_status == ExtractionStatus.COMPLETED,
            )
        )
    ).all()
    bid_docs = (
        await db.scalars(
            select(Document).where(
                Document.project_id == project_id,
                Document.document_type == DocumentType.BID,
                Document.extraction_status == ExtractionStatus.COMPLETED,
            )
        )
    ).all()

    if not tender_docs:
        raise AnalysisPreconditionError(
            "Upload at least one tender document with completed text extraction before running analysis."
        )
    if not bid_docs:
        raise AnalysisPreconditionError(
            "Upload at least one bid document with completed text extraction before running analysis."
        )


async def run_analysis(project_id: str) -> None:
    async with AsyncSessionLocal() as db:
        project = await db.get(Project, project_id)
        if project is None:
            logger.warning("Analysis requested for missing project %s", project_id)
            return

        provider = get_ai_provider()
        if provider is None:
            project.analysis_status = AnalysisStatus.FAILED
            project.analysis_error = (
                "AI provider not configured. Set ANTHROPIC_API_KEY to enable analysis."
            )
            await db.commit()
            return

        project.analysis_status = AnalysisStatus.PROCESSING
        project.analysis_started_at = utcnow()
        await db.commit()

        try:
            await _run_pipeline(db, provider=provider, project_id=project_id)
        except AIProviderError as exc:
            logger.exception("Analysis failed for project %s", project_id)
            project.analysis_status = AnalysisStatus.FAILED
            project.analysis_error = str(exc)
            await db.commit()
            return
        except Exception:
            logger.exception("Unexpected analysis failure for project %s", project_id)
            project.analysis_status = AnalysisStatus.FAILED
            project.analysis_error = "An unexpected error occurred during analysis."
            await db.commit()
            return

        project.analysis_status = AnalysisStatus.COMPLETED
        project.analysis_completed_at = utcnow()
        await db.commit()


async def _clear_previous_analysis(db: AsyncSession, *, project_id: str) -> None:
    """Re-running analysis (the "Re-run analysis" button on an
    already-completed project) regenerates requirements from scratch
    rather than appending to what's there — without this, a second run
    would duplicate every requirement indefinitely. This intentionally
    discards any review actions recorded against the previous run's
    requirements (Requirement's cascade="all, delete-orphan" on
    assessment/evidence_records/review_actions handles that): there's no
    versioned analysis-run history in this MVP, just current-state per
    project.
    """
    requirements = list(
        await db.scalars(select(Requirement).where(Requirement.project_id == project_id))
    )
    for requirement in requirements:
        await db.delete(requirement)
    await db.commit()


async def _run_pipeline(db: AsyncSession, *, provider: AIProvider, project_id: str) -> None:
    await _clear_previous_analysis(db, project_id=project_id)

    tender_docs = list(
        await db.scalars(
            select(Document).where(
                Document.project_id == project_id,
                Document.document_type == DocumentType.TENDER,
                Document.extraction_status == ExtractionStatus.COMPLETED,
            )
        )
    )
    bid_docs = list(
        await db.scalars(
            select(Document).where(
                Document.project_id == project_id,
                Document.document_type == DocumentType.BID,
                Document.extraction_status == ExtractionStatus.COMPLETED,
            )
        )
    )

    bid_page_texts: dict[str, dict[int, str]] = {}
    bid_candidate_pages: list[PageText] = []
    for doc in bid_docs:
        pages = list(
            await db.scalars(
                select(DocumentPage)
                .where(DocumentPage.document_id == doc.id)
                .order_by(DocumentPage.page_number)
            )
        )
        bid_page_texts[doc.id] = {p.page_number: p.text for p in pages}
        bid_candidate_pages.extend(PageText(page_number=p.page_number, text=p.text) for p in pages)

    for tender_doc in tender_docs:
        tender_pages = list(
            await db.scalars(
                select(DocumentPage)
                .where(DocumentPage.document_id == tender_doc.id)
                .order_by(DocumentPage.page_number)
            )
        )
        tender_page_texts = {p.page_number: p.text for p in tender_pages}
        page_texts_for_ai = [PageText(page_number=p.page_number, text=p.text) for p in tender_pages]

        extraction = await provider.extract_requirements(pages=page_texts_for_ai)

        for extracted in extraction.requirements:
            if not _excerpt_is_verifiable(
                extracted.source_excerpt, tender_page_texts, extracted.source_page
            ):
                logger.warning(
                    "Dropping extracted requirement with unverifiable excerpt on page %s of document %s",
                    extracted.source_page,
                    tender_doc.id,
                )
                continue

            requirement = Requirement(
                project_id=project_id,
                source_document_id=tender_doc.id,
                source_page=extracted.source_page,
                source_clause=extracted.source_clause,
                source_excerpt=extracted.source_excerpt,
                title=extracted.title,
                normalized_requirement=extracted.normalized_requirement,
                category=extracted.category,
                mandatory_status=extracted.mandatory_status,
                conditions=extracted.conditions,
                required_evidence=extracted.required_evidence,
                extraction_uncertain=extracted.extraction_uncertain,
            )
            db.add(requirement)
            await db.flush()

            await _assess_and_persist(
                db,
                provider=provider,
                requirement=requirement,
                extracted=extracted,
                bid_docs=bid_docs,
                bid_page_texts=bid_page_texts,
                bid_candidate_pages=bid_candidate_pages,
            )

        await db.commit()


async def _assess_and_persist(
    db: AsyncSession,
    *,
    provider: AIProvider,
    requirement: Requirement,
    extracted: ExtractedRequirement,
    bid_docs: list[Document],
    bid_page_texts: dict[str, dict[int, str]],
    bid_candidate_pages: list[PageText],
) -> None:
    if not bid_candidate_pages:
        assessment = Assessment(
            requirement_id=requirement.id,
            status="evidence_not_found",
            evidence_quality="none",
            assessment_confidence="high",
            priority=compute_priority(extracted.mandatory_status, "evidence_not_found"),
            reason="No bid document pages were available to search for evidence.",
            missing_information=json.dumps([]),
            requires_human_review=True,
            ai_provider=provider.name,
            prompt_version=COMPLIANCE_ASSESSMENT_VERSION,
        )
        db.add(assessment)
        return

    bid_document_id = bid_docs[0].id  # MVP: single-bid-document evidence pool per project
    result = await provider.assess_requirement(
        requirement=extracted, document_id=bid_document_id, candidate_pages=bid_candidate_pages
    )

    verified_evidence = [
        ev
        for ev in result.evidence
        if _excerpt_is_verifiable(ev.excerpt, bid_page_texts.get(ev.document_id, {}), ev.page_number)
    ]
    dropped = len(result.evidence) - len(verified_evidence)

    status = (
        result.status
        if verified_evidence or result.status == "evidence_not_found"
        else "evidence_not_found"
    )
    reason = result.reason
    if dropped:
        reason += (
            f" (Note: {dropped} cited evidence excerpt(s) could not be verified against the "
            "source document text and were discarded.)"
        )

    assessment = Assessment(
        requirement_id=requirement.id,
        status=status,
        evidence_quality=result.evidence_quality if verified_evidence else "none",
        assessment_confidence=result.assessment_confidence,
        priority=compute_priority(extracted.mandatory_status, status),
        reason=reason,
        missing_information=json.dumps(result.missing_information),
        requires_human_review=True,  # every AI-generated assessment starts as needing human review
        ai_provider=provider.name,
        prompt_version=COMPLIANCE_ASSESSMENT_VERSION + "/" + REQUIREMENT_EXTRACTION_VERSION,
    )
    db.add(assessment)

    for ev in verified_evidence:
        db.add(
            EvidenceRecord(
                requirement_id=requirement.id,
                document_id=ev.document_id,
                page_number=ev.page_number,
                excerpt=ev.excerpt,
                retrieval_method=ev.retrieval_method,
                evidence_type=ev.evidence_type,
                relevance_note=ev.relevance_note,
                potential_conflict=ev.potential_conflict,
            )
        )
