"""
Company Insights API Endpoints
Provides multi-layer company classification, industry detection, culture sentiment scoring, and interview intelligence.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CompanyInsightsRequest, CompanyInsightsOut
from app.services.company_insights import get_company_insights

logger = logging.getLogger("memora.routers.insights")
router = APIRouter(prefix="/insights", tags=["insights"])


@router.post("/analyze", response_model=CompanyInsightsOut)
def analyze_company(
    payload: CompanyInsightsRequest,
    db: Session = Depends(get_db)
):
    """
    Analyzes a target company using multi-layer transformer signals:
    1. Layer 1: Zero-shot size classification (MNC vs Startup vs Mid-size) + facts extraction & disagreement check.
    2. Layer 1b: Industry classification (62-tag DistilBERT).
    3. Layer 3: Culture synthesis + quantifiable sentiment breakdown (DistilBERT SST-2).
    4. Layer 4: Interview intelligence & preparation focus areas.
    """
    if not payload.company or not payload.company.strip():
        raise HTTPException(status_code=400, detail="Company name cannot be empty")

    try:
        insights = get_company_insights(
            company_name=payload.company.strip(),
            company_url=payload.company_url,
            about_text=payload.about_text,
            role_title=payload.role_title
        )
        return insights
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        logger.exception("Error analyzing company insights: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to analyze company insights: {str(exc)}")


@router.get("/{company_name}", response_model=CompanyInsightsOut)
def get_insights_by_name(
    company_name: str,
    role_title: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Quick lookup endpoint to generate company insights for a given company name.
    """
    if not company_name or not company_name.strip():
        raise HTTPException(status_code=400, detail="Company name cannot be empty")

    try:
        insights = get_company_insights(
            company_name=company_name.strip(),
            role_title=role_title
        )
        return insights
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        logger.exception("Error analyzing company insights: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to analyze company insights: {str(exc)}")
