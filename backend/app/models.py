from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, BigInteger, Numeric, Date, DateTime, ForeignKey, UniqueConstraint, text, Table, Column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import date, datetime
from .db import Base
import uuid

class Ticker(Base):
    __tablename__ = "ticker"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )
    symbol: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    exchange: Mapped[str] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    
    # Relationship to price_daily
    prices = relationship("PriceDaily", back_populates="ticker", cascade="all, delete-orphan")


class PriceDaily(Base):
    __tablename__ = "price_daily"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )
    ticker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("ticker.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[float] = mapped_column(Numeric(18, 6), nullable=True)
    high: Mapped[float] = mapped_column(Numeric(18, 6), nullable=True)
    low: Mapped[float] = mapped_column(Numeric(18, 6), nullable=True)
    close: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=True)
    avg_volume: Mapped[int] = mapped_column(BigInteger, nullable=True)
    pe: Mapped[float] = mapped_column(Numeric(18, 6), nullable=True)
    market_cap: Mapped[int] = mapped_column(BigInteger, nullable=True)
    
    __table_args__ = (
        UniqueConstraint("ticker_id", "date", name="uq_price_daily_ticker_date"),
    )
    
    # Relationship to ticker
    ticker = relationship("Ticker", back_populates="prices")


class RiskFreeSeries(Base):
    __tablename__ = "risk_free_series"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )
    date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    rate: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)


# Association table for watchlist tickers
watchlist_tickers = Table(
    'watchlist_tickers',
    Base.metadata,
    Column('watchlist_id', UUID(as_uuid=True), ForeignKey('watchlist.id', ondelete='CASCADE'), primary_key=True),
    Column('ticker_id', UUID(as_uuid=True), ForeignKey('ticker.id', ondelete='CASCADE'), primary_key=True),
    Column('added_at', DateTime, server_default=text("CURRENT_TIMESTAMP"))
)


class Watchlist(Base):
    __tablename__ = "watchlist"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.now,
        nullable=False
    )
    
    # Many-to-many relationship with tickers
    tickers = relationship("Ticker", secondary=watchlist_tickers, backref="watchlists")


class Portfolio(Base):
    __tablename__ = "portfolio"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    inception_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_value: Mapped[float] = mapped_column(Numeric(18, 2), nullable=True, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.now,
        nullable=False
    )
    
    # Relationship to holdings
    holdings = relationship("PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioHolding(Base):
    __tablename__ = "portfolio_holding"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolio.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    ticker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ticker.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    shares: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    average_cost: Mapped[float] = mapped_column(Numeric(18, 6), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    
    __table_args__ = (
        UniqueConstraint("portfolio_id", "ticker_id", name="uq_portfolio_ticker"),
    )
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")
    ticker = relationship("Ticker")


class FundamentalsCache(Base):
    """Cache for fundamentals data to reduce API calls"""
    __tablename__ = "fundamentals_cache"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )
    ticker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ticker.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    pe_ratio: Mapped[float] = mapped_column(Numeric(18, 6), nullable=True)
    market_cap: Mapped[int] = mapped_column(BigInteger, nullable=True)
    beta: Mapped[float] = mapped_column(Numeric(18, 6), nullable=True)
    week_52_high: Mapped[float] = mapped_column(Numeric(18, 6), nullable=True)
    week_52_low: Mapped[float] = mapped_column(Numeric(18, 6), nullable=True)
    avg_volume: Mapped[int] = mapped_column(BigInteger, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=True)  # Track which API provided data
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    
    # Relationship
    ticker = relationship("Ticker")
