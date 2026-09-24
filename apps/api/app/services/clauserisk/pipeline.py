"""ClauseRisk analysis pipeline orchestration — stages 4 through 12.

Stage 4-5 (segmentation/clause identification): deterministic, see
segmentation.py — no AI involved in deciding clause boundaries.

Stage 6-8 (classification + obligation/parameter extraction): one AI
call per clause via AIProvider.extract_clause.

Stage 9 (cross-clause retrieval): deterministic, see cross_links.py.

Stage 10 (risk analysis): one AI call per clause via
AIProvider.analyze_clause_risk, given the related-clause context from
stage 9 — plus one contract-wide call for "missing protections"
(AIProvider.find_missing_protections).

Stage 11-12 (deterministic + evidence validation): every AI-cited excerpt
is checked against real clause text (app/services/text_verification.py)
before being trusted; every finding's severity/score is computed by
app/services/clauserisk/risk_engine.py, never taken as-is from the AI's
severity_hint.
"""

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.session import AsyncSessionLocal
from app.models.clause import Clause, SourceConfidence
from app.models.contract import Contract, ContractAnalysisStatus, ContractVersion
from app.models.cross_clause_link import CrossClauseLink
from app.models.document import DocumentPage, ExtractionStatus
from app.models.project import Project
from app.models.risk_finding import RiskFinding
from app.services.clauserisk.ai import get_clauserisk_ai_provider
from app.services.clauserisk.ai.prompts import CLAUSE_EXTRACTION_VERSION, RISK_ANALYSIS_VERSION
from app.services.clauserisk.ai.provider import AIProvider, AIProviderError
from app.services.clauserisk.cross_links import ClauseForLinking, build_cross_clause_links
from app.services.clauserisk.risk_categories import category_for_subcategory
from app.services.clauserisk.risk_engine import compute_risk_score
from app.services.clauserisk.risk_types import normalize_risk_type
from app.services.clauserisk.segmentation import PageText, segment_pages
from app.services.text_verification import excerpt_is_verifiable

logger = logging.getLogger("clauserisk.pipeline")

MAX_RELATED_CLAUSES_FOR_CONTEXT = 3


class AnalysisPreconditionError(Exception):
    pass


# Stage labels are shown verbatim to a reviewer waiting on a long run, so
# they describe what is happening rather than naming internal functions.
STAGE_SEGMENTING = "Segmenting clauses"
STAGE_EXTRACTING = "Extracting clause detail"
STAGE_LINKING = "Linking related clauses"
STAGE_ANALYZING = "Analysing clause risk"
STAGE_MISSING_PROTECTIONS = "Checking for missing protections"


async def _set_progress(
    db: AsyncSession,
    version: ContractVersion,
    *,
    stage: str,
    current: int = 0,
    total: int = 0,
) -> None:
    """Record progress and commit.

    The commit matters for more than the UI. This pipeline previously held a
    single transaction open across every AI call in a stage, which on a
    34-clause contract meant one transaction open for the best part of an
    hour, holding row locks the whole time. An `ALTER TABLE contract_versions`
    then queued behind the run, and because Postgres queues later lock
    requests behind a waiting DDL, every other query on the table queued
    behind the ALTER. Committing per clause keeps each transaction to the
    length of one database write instead of one model call.
    """
    version.analysis_stage = stage
    version.analysis_progress_current = current
    version.analysis_progress_total = total
    await db.commit()


async def fail_interrupted_analyses(db: AsyncSession) -> int:
    """Mark runs that were in flight when the process died as failed.

    Analysis runs in a FastAPI background task, so a restart (deploy, crash,
    or a developer's Ctrl-C) kills it with the row still reading
    "processing". Nothing ever moves that row again: the version shows a
    spinner forever and the UI disables its own "Run analysis" button,
    leaving the contract permanently unanalysable. Reconciling at startup
    turns that dead end into a failed run the reviewer can simply retry.
    """
    interrupted = list(
        await db.scalars(
            select(ContractVersion).where(
                ContractVersion.analysis_status == ContractAnalysisStatus.PROCESSING
            )
        )
    )
    for version in interrupted:
        version.analysis_status = ContractAnalysisStatus.FAILED
        version.analysis_error = (
            "Analysis was interrupted when the server restarted. No partial results were "
            "kept. Run it again to start over."
        )
        version.analysis_stage = None
    if interrupted:
        await db.commit()
        logger.warning("Marked %d interrupted contract analyses as failed", len(interrupted))
    return len(interrupted)


async def check_analysis_preconditions(
    db: AsyncSession, *, organization_id: str, contract_version_id: str
) -> ContractVersion:
    version = await db.get(ContractVersion, contract_version_id)
    if version is None:
        raise AnalysisPreconditionError("Contract version not found.")

    contract = await db.get(Contract, version.contract_id)
    if contract is None:
        raise AnalysisPreconditionError("Contract not found.")

    project = await db.get(Project, contract.project_id)
    if project is None or project.organization_id != organization_id:
        raise AnalysisPreconditionError("Contract version not found.")

    await db.refresh(version, attribute_names=["document"])
    if version.document.extraction_status != ExtractionStatus.COMPLETED:
        raise AnalysisPreconditionError(
            "This document's text extraction has not completed yet. Wait for extraction to "
            "finish before running analysis."
        )
    return version


async def run_contract_analysis(contract_version_id: str) -> None:
    async with AsyncSessionLocal() as db:
        version = await db.get(ContractVersion, contract_version_id)
        if version is None:
            logger.warning("Analysis requested for missing contract version %s", contract_version_id)
            return

        provider = get_clauserisk_ai_provider()
        if provider is None:
            version.analysis_status = ContractAnalysisStatus.FAILED
            version.analysis_error = (
                "No ClauseRisk AI provider is configured or reachable. Check CLAUSERISK_AI_PROVIDER "
                "and (for Ollama) that the Ollama server is running."
            )
            await db.commit()
            return

        available, reason = await provider.is_available()
        if not available:
            version.analysis_status = ContractAnalysisStatus.FAILED
            version.analysis_error = reason or "AI provider is not available."
            await db.commit()
            return

        version.analysis_status = ContractAnalysisStatus.PROCESSING
        version.analysis_started_at = utcnow()
        version.analysis_error = None
        await db.commit()

        try:
            await _run_pipeline(db, provider=provider, contract_version_id=contract_version_id)
        except AIProviderError as exc:
            logger.exception("ClauseRisk analysis failed for version %s", contract_version_id)
            version.analysis_status = ContractAnalysisStatus.FAILED
            version.analysis_error = str(exc)
            await db.commit()
            return
        except Exception:
            logger.exception(
                "Unexpected ClauseRisk analysis failure for version %s", contract_version_id
            )
            version.analysis_status = ContractAnalysisStatus.FAILED
            version.analysis_error = "An unexpected error occurred during analysis."
            await db.commit()
            return

        version.analysis_status = ContractAnalysisStatus.COMPLETED
        version.analysis_completed_at = utcnow()
        version.analysis_stage = None
        await db.commit()


async def _clear_previous_analysis(db: AsyncSession, *, contract_version_id: str) -> None:
    """Re-running analysis (e.g. the UI's "Re-run analysis" button on an
    already-completed version) regenerates clauses/links/findings from
    scratch rather than appending to what's there — without this, a second
    run would duplicate every clause and finding indefinitely. This
    intentionally discards any review actions recorded against the
    previous run's findings (RiskFinding's cascade="all, delete-orphan"
    on review_actions handles that): there's no versioned analysis-run
    history in this MVP, just current-state per contract version.
    """
    findings = list(
        await db.scalars(
            select(RiskFinding).where(RiskFinding.contract_version_id == contract_version_id)
        )
    )
    for finding in findings:
        await db.delete(finding)

    links = list(
        await db.scalars(
            select(CrossClauseLink).where(CrossClauseLink.contract_version_id == contract_version_id)
        )
    )
    for link in links:
        await db.delete(link)

    clauses = list(
        await db.scalars(select(Clause).where(Clause.contract_version_id == contract_version_id))
    )
    for clause in clauses:
        await db.delete(clause)

    await db.commit()


async def _run_pipeline(db: AsyncSession, *, provider: AIProvider, contract_version_id: str) -> None:
    version = await db.get(ContractVersion, contract_version_id)
    assert version is not None

    await _clear_previous_analysis(db, contract_version_id=contract_version_id)
    await _set_progress(db, version, stage=STAGE_SEGMENTING)

    pages = list(
        await db.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == version.document_id)
            .order_by(DocumentPage.page_number)
        )
    )
    page_texts = [PageText(page_number=p.page_number, text=p.text) for p in pages]
    raw_segments = segment_pages(page_texts)

    clauses: list[Clause] = []
    for segment in raw_segments:
        clause = Clause(
            contract_version_id=contract_version_id,
            clause_number=segment.clause_number,
            title=segment.title,
            text=segment.text,
            page_start=segment.page_start,
            page_end=segment.page_end,
            sequence_index=segment.sequence_index,
        )
        db.add(clause)
        clauses.append(clause)
    await db.flush()

    await _set_progress(db, version, stage=STAGE_EXTRACTING, total=len(clauses))

    for index, clause in enumerate(clauses, start=1):
        try:
            extraction = await provider.extract_clause(clause_text=clause.text, clause_title=clause.title)
        except AIProviderError:
            clause.extraction_error = "Clause extraction failed for this clause."
            logger.exception("Extraction failed for clause %s", clause.id)
            await _set_progress(
                db, version, stage=STAGE_EXTRACTING, current=index, total=len(clauses)
            )
            continue

        clause.subcategory = extraction.subcategory or None
        clause.category = category_for_subcategory(extraction.subcategory) if extraction.subcategory else None
        clause.source_confidence = SourceConfidence(extraction.confidence)
        clause.set_list_field("extracted_obligations", extraction.obligations)
        clause.set_list_field("extracted_rights", extraction.rights)
        clause.set_list_field("extracted_conditions", extraction.conditions)
        clause.set_list_field("extracted_exceptions", extraction.exceptions)
        clause.set_list_field(
            "extracted_amounts", _keep_verifiable(extraction.amounts, clause.text)
        )
        clause.set_list_field("extracted_dates", _keep_verifiable(extraction.dates, clause.text))
        clause.set_list_field(
            "extracted_percentages", _keep_verifiable(extraction.percentages, clause.text)
        )
        clause.set_list_field("extracted_time_periods", extraction.time_periods)
        referenced = [r for r in extraction.referenced_clauses if r != clause.clause_number]
        clause.set_list_field("referenced_clauses", referenced)

        # Committing per clause (rather than once at the end) is what makes
        # the progress counter move in the UI during a long run, and means an
        # interrupted run keeps the clauses it already extracted.
        await _set_progress(
            db, version, stage=STAGE_EXTRACTING, current=index, total=len(clauses)
        )

    await _set_progress(db, version, stage=STAGE_LINKING, total=len(clauses))

    linkable = [
        ClauseForLinking(
            id=c.id, clause_number=c.clause_number, text=c.text, subcategory=c.subcategory
        )
        for c in clauses
    ]
    links = build_cross_clause_links(linkable)
    for link in links:
        db.add(
            CrossClauseLink(
                contract_version_id=contract_version_id,
                clause_a_id=link.clause_a_id,
                clause_b_id=link.clause_b_id,
                relationship_type=link.relationship_type,
                basis=link.basis,
            )
        )
    await db.commit()

    clauses_by_id = {c.id: c for c in clauses}
    related_by_clause: dict[str, list[Clause]] = {c.id: [] for c in clauses}
    for link in links:
        a, b = clauses_by_id.get(link.clause_a_id), clauses_by_id.get(link.clause_b_id)
        if a and b:
            related_by_clause[a.id].append(b)
            related_by_clause[b.id].append(a)

    await _set_progress(db, version, stage=STAGE_ANALYZING, total=len(clauses))

    for index, clause in enumerate(clauses, start=1):
        if clause.extraction_error:
            continue
        related_clauses = related_by_clause.get(clause.id, [])[:MAX_RELATED_CLAUSES_FOR_CONTEXT]
        related_context = [
            f"[Clause {rc.clause_number or '?'}] {rc.text}" for rc in related_clauses
        ]
        try:
            result = await provider.analyze_clause_risk(
                clause_text=clause.text,
                clause_category=clause.category or "uncategorized",
                related_clauses_context=related_context,
            )
        except AIProviderError:
            logger.exception("Risk analysis failed for clause %s", clause.id)
            await _set_progress(
                db, version, stage=STAGE_ANALYZING, current=index, total=len(clauses)
            )
            continue

        searchable_text = clause.text + "\n" + "\n".join(related_context)
        for candidate in result.findings:
            verified = excerpt_is_verifiable(candidate.evidence_excerpt, searchable_text)
            has_amount_or_percentage = bool(
                clause.get_list_field("extracted_amounts")
                or clause.get_list_field("extracted_percentages")
            )
            has_cap = _mentions_cap_language(clause.text)

            score_result = compute_risk_score(
                severity_hint=candidate.severity_hint,
                subcategory=clause.subcategory,
                has_cap_or_limit=has_cap,
                exposure_stated=has_amount_or_percentage,
                evidence_verified=verified,
                ai_confidence=(
                    clause.source_confidence.value if clause.source_confidence else "medium"
                ),
                uncertainty=candidate.uncertainty,
            )

            finding = RiskFinding(
                contract_version_id=contract_version_id,
                clause_id=clause.id,
                category=clause.category or "contractual",
                risk_type=normalize_risk_type(
                    candidate.risk_type, subcategory=clause.subcategory
                ),
                severity=score_result.final_severity,
                risk_description=candidate.description,
                contractual_effect=candidate.contractual_effect or None,
                potential_exposure=candidate.potential_exposure or None,
                trigger=candidate.trigger or None,
                affected_party=candidate.affected_party,
                uncertainty=candidate.uncertainty,
                recommended_review_action=candidate.recommended_review_action or None,
                computed_score=score_result.final_score,
                ai_provider=provider.name,
                prompt_version=f"{CLAUSE_EXTRACTION_VERSION}/{RISK_ANALYSIS_VERSION}",
            )
            finding.set_evidence(
                [
                    {
                        "clause_id": clause.id,
                        "page": clause.page_start,
                        "excerpt": candidate.evidence_excerpt,
                        "verified": verified,
                    }
                ]
                if verified
                else []
            )
            finding.related_clauses = json.dumps(
                [rc.clause_number for rc in related_clauses if rc.clause_number]
            )
            finding.risk_factors = json.dumps(score_result.factors)
            db.add(finding)

        await _set_progress(
            db, version, stage=STAGE_ANALYZING, current=index, total=len(clauses)
        )

    # Clause-by-clause work is finished by this point; this last stage is a
    # single contract-wide call. Carry the count forward rather than letting
    # it default back to zero, which would show the progress bar jumping
    # backwards to "0 of N" on the final step.
    await _set_progress(
        db,
        version,
        stage=STAGE_MISSING_PROTECTIONS,
        current=len(clauses),
        total=len(clauses),
    )
    await _run_missing_protections(db, provider=provider, version=version, clauses=clauses)


async def _run_missing_protections(
    db: AsyncSession, *, provider: AIProvider, version: ContractVersion, clauses: list[Clause]
) -> None:
    categories_present = sorted({c.category for c in clauses if c.category})
    summary = (
        f"{len(clauses)} clauses identified across categories: "
        f"{', '.join(categories_present) or 'none classified'}."
    )
    try:
        result = await provider.find_missing_protections(
            contract_summary=summary, categories_present=categories_present
        )
    except AIProviderError:
        logger.exception("Missing-protections analysis failed for version %s", version.id)
        return

    for candidate in result.missing_protections:
        # A missing-protection finding has no clause to fall back on, so
        # "missing_protection" is the honest default when the model's answer
        # isn't in the taxonomy.
        risk_type = normalize_risk_type(candidate.risk_type, subcategory=None)
        if risk_type == "other":
            risk_type = "missing_protection"

        score_result = compute_risk_score(
            severity_hint=candidate.severity_hint,
            subcategory=None,
            has_cap_or_limit=False,
            exposure_stated=False,
            evidence_verified=False,
            ai_confidence="medium",
            uncertainty="not_found",
        )
        finding = RiskFinding(
            contract_version_id=version.id,
            clause_id=None,
            category=candidate.category,
            risk_type=risk_type,
            severity=score_result.final_severity,
            risk_description=candidate.description,
            recommended_review_action=candidate.recommended_review_action or None,
            affected_party="unclear",
            uncertainty="not_found",
            computed_score=score_result.final_score,
            ai_provider=provider.name,
            prompt_version="missing_protections/v1",
        )
        finding.set_evidence([])
        finding.risk_factors = json.dumps(score_result.factors)
        db.add(finding)

    await db.commit()


def _keep_verifiable(items: list[str], source_text: str) -> list[str]:
    return [item for item in items if excerpt_is_verifiable(item, source_text)]


def _mentions_cap_language(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in ("shall not exceed", "capped at", "maximum liability", "up to a maximum", "limited to")
    )
