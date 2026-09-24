import json
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.paths import SAMPLE_DATA_DIR
from app.db.base import utcnow
from app.models.assessment import Assessment
from app.models.document import Document, DocumentPage, DocumentType, ExtractionStatus
from app.models.evidence import EvidenceRecord
from app.models.project import AnalysisStatus, Project, ProjectStatus
from app.models.requirement import Requirement
from app.models.review_action import ReviewAction
from app.services import storage
from app.services.demo_fixtures import BID_FILENAME, DEMO_REQUIREMENTS, TENDER_FILENAME
from app.services.extraction import extract_document

# Both modules seed is_demo projects, so the "already loaded?" check has to
# identify *this* module's sample specifically rather than any demo project.
DEMO_PROJECT_NAME = "Offshore Well Testing Services Package (Sample)"


class SampleDataMissingError(Exception):
    pass


async def _create_and_extract_document(
    db: AsyncSession,
    *,
    organization_id: str,
    project_id: str,
    uploaded_by_user_id: str,
    document_type: DocumentType,
    filename: str,
) -> Document:
    source_path = SAMPLE_DATA_DIR / filename
    if not source_path.exists():
        raise SampleDataMissingError(
            f"{filename} not found in sample_data/. Run "
            "apps/api/scripts/generate_sample_data.py to create it."
        )
    content = source_path.read_bytes()

    document = Document(
        project_id=project_id,
        uploaded_by_user_id=uploaded_by_user_id,
        document_type=document_type,
        original_filename=filename,
        mime_type="application/pdf",
        size_bytes=len(content),
        file_hash=storage.compute_hash(content),
        storage_path="",
        extraction_status=ExtractionStatus.PROCESSING,
    )
    db.add(document)
    await db.flush()

    storage_path = storage.save_document_file(
        organization_id=organization_id,
        project_id=project_id,
        document_id=document.id,
        filename=filename,
        content=content,
    )
    document.storage_path = storage_path

    result = extract_document(content)
    document.page_count = result.page_count
    for page in result.pages:
        db.add(
            DocumentPage(
                document_id=document.id,
                page_number=page.page_number,
                text=page.text,
                char_count=page.char_count,
                extraction_method=page.extraction_method,
                low_text_warning=page.low_text_warning,
            )
        )
    document.extraction_status = ExtractionStatus.COMPLETED
    await db.flush()
    return document


async def create_demo_project(
    db: AsyncSession, *, organization_id: str, created_by_user_id: str
) -> Project:
    # "Try the sample project" gets clicked more than once in practice, and
    # seeding a fresh copy each time leaves the Projects list full of
    # identical duplicates. Return the existing sample instead, preserving
    # any review decisions already recorded against it.
    existing = await db.scalar(
        select(Project)
        .where(
            Project.organization_id == organization_id,
            Project.is_demo.is_(True),
            Project.name == DEMO_PROJECT_NAME,
            Project.deleted_at.is_(None),
        )
        .order_by(Project.created_at)
        .limit(1)
    )
    if existing is not None:
        return existing

    project = Project(
        organization_id=organization_id,
        created_by_user_id=created_by_user_id,
        owner_user_id=created_by_user_id,
        name=DEMO_PROJECT_NAME,
        client_name="Meridian Energy Company",
        tender_reference="ITB-2026-DEMO-001",
        sector="Oil & Gas",
        status=ProjectStatus.ACTIVE,
        currency="USD",
        # A bid manager's first question is always "when does it close?", so
        # the sample carries a live deadline rather than a blank field.
        submission_deadline=(utcnow() + timedelta(days=12)).date(),
        confidentiality="Fictional — sample data",
        notes=(
            "This is a fictional sample project created for demonstration "
            "purposes. The tender, bidder, company names, and all figures are "
            "invented and do not describe a real procurement. Results below "
            "are precomputed sample data, not a live AI analysis."
        ),
        is_demo=True,
        analysis_status=AnalysisStatus.PROCESSING,
    )
    db.add(project)
    await db.flush()

    tender_doc = await _create_and_extract_document(
        db,
        organization_id=organization_id,
        project_id=project.id,
        uploaded_by_user_id=created_by_user_id,
        document_type=DocumentType.TENDER,
        filename=TENDER_FILENAME,
    )
    bid_doc = await _create_and_extract_document(
        db,
        organization_id=organization_id,
        project_id=project.id,
        uploaded_by_user_id=created_by_user_id,
        document_type=DocumentType.BID,
        filename=BID_FILENAME,
    )

    for item in DEMO_REQUIREMENTS:
        requirement = Requirement(
            project_id=project.id,
            source_document_id=tender_doc.id,
            source_page=item["source_page"],
            source_clause=item["source_clause"],
            source_excerpt=item["source_excerpt"],
            title=item["title"],
            normalized_requirement=item["normalized_requirement"],
            category=item["category"],
            mandatory_status=item["mandatory_status"],
            conditions=item["conditions"],
            required_evidence=item["required_evidence"],
            extraction_uncertain=item["extraction_uncertain"],
        )
        db.add(requirement)
        await db.flush()

        for ev in item["evidence"]:
            db.add(
                EvidenceRecord(
                    requirement_id=requirement.id,
                    document_id=bid_doc.id,
                    page_number=ev["page"],
                    excerpt=ev["excerpt"],
                    retrieval_method=ev["retrieval_method"],
                    evidence_type=ev["evidence_type"],
                    relevance_note=ev["relevance_note"],
                    potential_conflict=ev["potential_conflict"],
                )
            )

        a = item["assessment"]
        db.add(
            Assessment(
                requirement_id=requirement.id,
                status=a["status"],
                evidence_quality=a["evidence_quality"],
                assessment_confidence=a["assessment_confidence"],
                priority=a["priority"],
                reason=a["reason"],
                missing_information=json.dumps(a["missing_information"]),
                requires_human_review=a["requires_human_review"],
                ai_provider="demo-sample-data",
                prompt_version="n/a",
                reviewer_status=a["reviewer_status"],
                reviewer_user_id=created_by_user_id if a["reviewer_status"] == "reviewed" else None,
            )
        )

        if item["review_action"]:
            ra = item["review_action"]
            db.add(
                ReviewAction(
                    requirement_id=requirement.id,
                    user_id=created_by_user_id,
                    action_type="status_change",
                    previous_status=ra["previous_status"],
                    new_status=ra["new_status"],
                    comment=ra["comment"],
                )
            )

    project.analysis_status = AnalysisStatus.COMPLETED
    project.analysis_completed_at = utcnow()
    await db.commit()
    await db.refresh(project)
    return project
