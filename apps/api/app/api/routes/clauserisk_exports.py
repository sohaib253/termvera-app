from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.models.contract import Contract
from app.services.clauserisk import export_excel
from app.services.clauserisk.access import ClauseRiskNotFoundError, get_owned_version

router = APIRouter(tags=["clauserisk-exports"])


@router.get("/api/contract-versions/{version_id}/exports/risk-report.xlsx")
async def export_risk_report(
    version_id: str,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        version = await get_owned_version(
            db, organization_id=principal.organization.id, contract_version_id=version_id
        )
    except ClauseRiskNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Contract version not found."
        ) from exc

    contract = await db.get(Contract, version.contract_id)
    assert contract is not None

    content = await export_excel.build_risk_report_workbook(db, contract=contract, version=version)
    filename = f"{contract.name.replace(' ', '-')}-risk-report.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
