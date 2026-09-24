"""ClauseRisk demo seeding.

Deliberately simpler than TenderGuard's app/services/demo.py: rather than
pre-computing fixture requirements/findings, this creates a project,
contract, and two realistic synthetic contract versions (a base contract
and an amendment) with real PyMuPDF-extracted text — then leaves analysis
to be triggered the normal way (POST .../analysis), exactly like a real
contract.

Why: this local Ollama pipeline takes on the order of 10 minutes per
version on this hardware (see docs/ai-evaluation.md) — too slow for a
synchronous "load demo" request, and pre-baking a second fixture-based
demo path (as TenderGuard did) would mean maintaining two different
"what a finished analysis looks like" shapes. Running the exact same
pipeline the demo goes through as a real contract does is more honest
and is less code to keep correct.
"""


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.paths import SAMPLE_DATA_DIR
from app.models.contract import Contract, ContractStatus, ContractType
from app.models.contract import ContractVersion as ContractVersionModel
from app.models.document import Document, DocumentPage, DocumentType, ExtractionStatus
from app.models.project import Project, ProjectStatus
from app.services import storage
from app.services.extraction import extract_document

BASE_CONTRACT_FILENAME = "offshore-well-testing-contract.pdf"
AMENDMENT_FILENAME = "offshore-well-testing-contract-amendment-1.pdf"


class SampleDataMissingError(Exception):
    pass


async def _create_and_extract_version(
    db: AsyncSession,
    *,
    organization_id: str,
    project_id: str,
    contract_id: str,
    uploaded_by_user_id: str,
    filename: str,
    version_number: int,
    version_label: str,
) -> ContractVersionModel:
    source_path = SAMPLE_DATA_DIR / filename
    if not source_path.exists():
        raise SampleDataMissingError(
            f"{filename} not found in sample_data/. Run "
            "apps/api/scripts/generate_clauserisk_sample_data.py to create it."
        )
    content = source_path.read_bytes()

    document = Document(
        project_id=project_id,
        uploaded_by_user_id=uploaded_by_user_id,
        document_type=DocumentType.CONTRACT,
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

    version = ContractVersionModel(
        contract_id=contract_id,
        document_id=document.id,
        uploaded_by_user_id=uploaded_by_user_id,
        version_number=version_number,
        version_label=version_label,
    )
    db.add(version)
    await db.flush()
    return version


async def create_demo_contract(
    db: AsyncSession, *, organization_id: str, created_by_user_id: str
) -> Contract:
    # "Try the sample contract" is a button a user will click more than once
    # (going back to it from the dashboard, a second browser tab, a demo to a
    # colleague). Seeding a fresh copy each time leaves the Contracts list and
    # Risk Register full of identical duplicates, so return the existing one
    # instead. Any analysis already run against it is preserved.
    existing = await db.scalar(
        select(Contract)
        .join(Project, Contract.project_id == Project.id)
        .where(
            Project.organization_id == organization_id,
            Contract.is_demo.is_(True),
            Contract.deleted_at.is_(None),
        )
        .order_by(Contract.created_at)
        .limit(1)
    )
    if existing is not None:
        await db.refresh(existing, attribute_names=["versions"])
        return existing

    project = Project(
        organization_id=organization_id,
        created_by_user_id=created_by_user_id,
        owner_user_id=created_by_user_id,
        name="ClauseRisk Sample Review",
        client_name="Meridian Energy Company",
        sector="Oil & Gas",
        status=ProjectStatus.ACTIVE,
        notes=(
            "Fictional sample project for the ClauseRisk module. The contract, "
            "counterparty, and all figures are invented."
        ),
        is_demo=True,
    )
    db.add(project)
    await db.flush()

    contract = Contract(
        project_id=project.id,
        created_by_user_id=created_by_user_id,
        name="Offshore Services Agreement (Sample)",
        contract_type=ContractType.SERVICES,
        status=ContractStatus.UNDER_REVIEW,
        counterparty_name="Meridian Energy Company",
        notes=(
            "This is a fictional sample contract created for demonstration purposes. "
            "It does not describe a real agreement. Click \"Run analysis\" on a version "
            "to see the real ClauseRisk pipeline (clause segmentation, AI extraction via "
            "your local Ollama model, cross-clause linking, and deterministic risk "
            "scoring) run against it."
        ),
        is_demo=True,
    )
    db.add(contract)
    await db.flush()

    await _create_and_extract_version(
        db,
        organization_id=organization_id,
        project_id=project.id,
        contract_id=contract.id,
        uploaded_by_user_id=created_by_user_id,
        filename=BASE_CONTRACT_FILENAME,
        version_number=1,
        version_label="Original — 3 February 2026",
    )
    await _create_and_extract_version(
        db,
        organization_id=organization_id,
        project_id=project.id,
        contract_id=contract.id,
        uploaded_by_user_id=created_by_user_id,
        filename=AMENDMENT_FILENAME,
        version_number=2,
        version_label="Amendment No. 1 — 14 May 2026",
    )

    await db.commit()
    await db.refresh(contract, attribute_names=["versions"])
    return contract
