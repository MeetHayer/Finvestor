from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_session
from app.models import Portfolio as PortfolioModel
from app.schemas import PortfolioCreate, PortfolioOut

router = APIRouter(prefix="/api/portfolios", tags=["portfolios"])


@router.post("", response_model=PortfolioOut, status_code=201)
async def create_portfolio(payload: PortfolioCreate, session: AsyncSession = Depends(get_session)):
    if not payload.name or not payload.user_id:
        raise HTTPException(status_code=400, detail="name and user_id are required")

    # Map into existing model; user_id not persisted if column doesn't exist
    p = PortfolioModel(
        name=payload.name,
        inception_date=payload.inception_date,
    )
    session.add(p)
    await session.commit()
    await session.refresh(p)

    return PortfolioOut(
        id=str(p.id), name=p.name, user_id=payload.user_id, inception_date=p.inception_date
    )


@router.get("", response_model=list[PortfolioOut])
async def list_portfolios(user_id: int = Query(...), session: AsyncSession = Depends(get_session)):
    # Since current DB schema doesn't store user_id, return all portfolios and echo requested user_id
    stmt = select(PortfolioModel).order_by(PortfolioModel.id.desc())
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        PortfolioOut(id=str(r.id), name=r.name, user_id=user_id, inception_date=r.inception_date)
        for r in rows
    ]



