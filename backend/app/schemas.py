from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1)
    user_id: int
    inception_date: Optional[date] = None


class PortfolioOut(BaseModel):
    id: str
    name: str
    user_id: int
    inception_date: Optional[date] = None


