from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timedelta
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.report import ReportType, TimePeriod, AccountingReport
from app.services.report_engine import report_engine
import calendar

router = APIRouter()

@router.get("/accounting", response_model=AccountingReport)
async def get_accounting_report(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    report_type: ReportType = Query(..., alias="type"),
    period: TimePeriod = Query(TimePeriod.MONTHLY),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    export_pdf: bool = Query(False)
):
    from app.models.user import PlanType
    if current_user.plan_type == PlanType.FREE:
        raise HTTPException(
            status_code=403, 
            detail="Accounting reports and PDF exports are only available on the PAID plan. Please upgrade to Pro."
        )

    # Calculate date range
    now = datetime.utcnow()
    if period == TimePeriod.DAILY:
        calc_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        calc_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == TimePeriod.WEEKLY:
        calc_start = now - timedelta(days=now.weekday())
        calc_start = calc_start.replace(hour=0, minute=0, second=0, microsecond=0)
        calc_end = calc_start + timedelta(days=6, hour=23, minute=59, second=59)
    elif period == TimePeriod.MONTHLY:
        calc_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = calendar.monthrange(now.year, now.month)[1]
        calc_end = now.replace(day=last_day, hour=23, minute=59, second=59)
    elif period == TimePeriod.YEARLY:
        calc_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        calc_end = now.replace(month=12, day=31, hour=23, minute=59, second=59)
    else:
        # CUSTOM
        if not start_date or not end_date:
            raise HTTPException(status_code=400, detail="start_date and end_date required for custom period")
        calc_start = start_date
        calc_end = end_date

    # Generate Report Data
    report_data = {}
    if report_type == ReportType.PNL:
        report = await report_engine.get_pnl_report(db, current_user, calc_start, calc_end)
        report_data = report.model_dump()
    elif report_type == ReportType.BALANCE_SHEET:
        report = await report_engine.get_balance_sheet_report(db, current_user, calc_end)
        report_data = report.model_dump()
    elif report_type == ReportType.CASH_FLOW:
        report = await report_engine.get_cash_flow_report(db, current_user, calc_start, calc_end)
        report_data = report.model_dump()
    
    # Generate AI Summary
    summary = await report_engine.generate_ai_summary(report_type, report_data, current_user.business_name or "Owner")
    
    if export_pdf:
        pdf_content = report_engine.export_to_pdf(report_type, report_data, summary, current_user)
        filename = f"{report_type.value}_{period.value}_{now.strftime('%Y%m%d')}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    return AccountingReport(
        report_type=report_type,
        period=period,
        data=report_data,
        summary=summary
    )
