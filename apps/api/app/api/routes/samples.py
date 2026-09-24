"""Downloadable sample documents.

The point of these is practical rather than decorative: a user can
download the tender, bid, and contract, look at them as documents, then
upload them through the normal flow and watch the real pipeline run on
them. That is a far more convincing evaluation than a pre-seeded demo
project, because nothing about it is special-cased.

Served from sample_data/ by an allow-list of known keys, never by a
client-supplied path, so this cannot be turned into an arbitrary file read.
"""

from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.api.deps import CurrentPrincipal, get_current_principal
from app.core.paths import SAMPLE_DATA_DIR
from app.schemas.sample import SampleDocumentRead

router = APIRouter(prefix="/api/samples", tags=["samples"])


@dataclass(frozen=True)
class SampleDocument:
    key: str
    filename: str
    title: str
    description: str
    module: str
    document_type: str


SAMPLE_DOCUMENTS: dict[str, SampleDocument] = {
    doc.key: doc
    for doc in (
        SampleDocument(
            key="tender",
            filename="offshore-well-testing-tender.pdf",
            title="Invitation to Tender (ITB-2026-DEMO-001)",
            description=(
                "A full offshore well testing ITT: instructions to bidders, scope, "
                "qualification and HSE screening criteria, technical and commercial "
                "requirements, mandatory forms, and evaluation basis."
            ),
            module="tenderguard",
            document_type="tender",
        ),
        SampleDocument(
            key="bid",
            filename="apex-well-services-bid.pdf",
            title="Bidder proposal (Apex Well Services)",
            description=(
                "A matching proposal with realistic gaps: a missing mandatory form, an "
                "incomplete certification set, a safety statistic above the stated "
                "threshold, and two commercial terms the bidder tried to re-trade."
            ),
            module="tenderguard",
            document_type="bid",
        ),
        SampleDocument(
            key="contract",
            filename="offshore-well-testing-contract.pdf",
            title="Offshore Well Testing Services Agreement",
            description=(
                "The executed agreement that follows the tender: 34 clauses spanning "
                "payment, schedule and liquidated damages, liability and indemnity, "
                "insurance, termination, and dispute resolution."
            ),
            module="clauserisk",
            document_type="contract",
        ),
        SampleDocument(
            key="amendment",
            filename="offshore-well-testing-contract-amendment-1.pdf",
            title="Amendment No. 1 to the Services Agreement",
            description=(
                "Six amended clauses: payment stretched to 60 days, retention raised to "
                "15%, the liability cap cut to 15%, termination notice cut to 7 days, and "
                "a new cyber security clause. Use it to try contract comparison."
            ),
            module="clauserisk",
            document_type="contract",
        ),
    )
}


@router.get("", response_model=list[SampleDocumentRead])
async def list_samples(
    _principal: CurrentPrincipal = Depends(get_current_principal),
) -> list[SampleDocumentRead]:
    return [
        SampleDocumentRead(
            key=doc.key,
            filename=doc.filename,
            title=doc.title,
            description=doc.description,
            module=doc.module,
            document_type=doc.document_type,
            size_bytes=(SAMPLE_DATA_DIR / doc.filename).stat().st_size
            if (SAMPLE_DATA_DIR / doc.filename).exists()
            else 0,
        )
        for doc in SAMPLE_DOCUMENTS.values()
    ]


@router.get("/{key}/file")
async def download_sample(
    key: str,
    _principal: CurrentPrincipal = Depends(get_current_principal),
) -> Response:
    sample = SAMPLE_DOCUMENTS.get(key)
    if sample is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sample document not found."
        )

    path = SAMPLE_DATA_DIR / sample.filename
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"{sample.filename} is missing from sample_data/. Run "
                "apps/api/scripts/generate_sample_data.py to regenerate it."
            ),
        )

    return Response(
        content=path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{sample.filename}"'},
    )
