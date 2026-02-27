from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from ..db.base import get_db
from ..models.strategy import Strategy
from ..models.config_dhan import ConfigDhan
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/strategies", tags=["strategies"])


class StrategySchema(BaseModel):
    id: Optional[int] = None
    name: str
    symbol: str
    exchange: str = "NSE"
    quantity: int = 1
    is_active: bool = False
    parameters: Optional[dict] = {}

    class Config:
        from_attributes = True


class StrategyCreate(BaseModel):
    name: str
    symbol: str
    exchange: str = "NSE"
    quantity: int = 1
    parameters: Optional[dict] = {}


class StrategyUpdate(BaseModel):
    symbol: Optional[str] = None
    exchange: Optional[str] = None
    quantity: Optional[int] = None
    is_active: Optional[bool] = None
    parameters: Optional[dict] = None


@router.get("/", response_model=List[StrategySchema])
def list_strategies(db: Session = Depends(get_db)):
    """List all strategies"""
    return db.query(Strategy).all()


@router.post("/", response_model=StrategySchema)
def create_strategy(strategy_data: StrategyCreate, db: Session = Depends(get_db)):
    """Create a new strategy"""
    from ..strategies.registry import strategy_registry
    if strategy_data.name not in strategy_registry:
        raise HTTPException(
            status_code=400,
            detail=f"Strategy '{strategy_data.name}' not found. Available: {list(strategy_registry.keys())}"
        )
    strategy = Strategy(
        name=strategy_data.name,
        symbol=strategy_data.symbol,
        exchange=strategy_data.exchange,
        quantity=strategy_data.quantity,
        parameters=strategy_data.parameters or {}
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    logger.info(f"Strategy created: {strategy.name} for {strategy.symbol}")
    return strategy


@router.get("/{strategy_id}", response_model=StrategySchema)
def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """Get a specific strategy"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.put("/{strategy_id}", response_model=StrategySchema)
def update_strategy(strategy_id: int, strategy_data: StrategyUpdate, db: Session = Depends(get_db)):
    """Update a strategy"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    update_data = strategy_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(strategy, key, value)
    db.commit()
    db.refresh(strategy)
    logger.info(f"Strategy updated: {strategy.id}")
    return strategy


@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """Delete a strategy"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    db.delete(strategy)
    db.commit()
    logger.info(f"Strategy deleted: {strategy_id}")
    return {"message": "Strategy deleted"}


@router.post("/{strategy_id}/toggle")
def toggle_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """Toggle strategy active/inactive"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    strategy.is_active = not strategy.is_active
    db.commit()
    status = "activated" if strategy.is_active else "deactivated"
    logger.info(f"Strategy {strategy_id} {status}")
    return {"id": strategy_id, "is_active": strategy.is_active, "status": status}


@router.get("/available/list")
def list_available_strategies():
    """List available strategy types"""
    from ..strategies.registry import strategy_registry
    return {"strategies": list(strategy_registry.keys())}
