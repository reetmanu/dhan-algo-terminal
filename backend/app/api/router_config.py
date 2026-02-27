from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from ..db.base import get_db
from ..models.config_dhan import ConfigDhan
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/config", tags=["config"])


class ConfigDhanSchema(BaseModel):
    client_id: str
    access_token: str
    paper_trade: bool = True
    max_daily_loss_pct: float = 2.0
    max_positions: int = 3

    class Config:
        from_attributes = True


class ConfigDhanUpdate(BaseModel):
    client_id: Optional[str] = None
    access_token: Optional[str] = None
    paper_trade: Optional[bool] = None
    max_daily_loss_pct: Optional[float] = None
    max_positions: Optional[int] = None


@router.get("/", response_model=ConfigDhanSchema)
def get_config(db: Session = Depends(get_db)):
    """Get Dhan API configuration"""
    config = db.query(ConfigDhan).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found. Please set up your Dhan credentials.")
    return config


@router.post("/", response_model=ConfigDhanSchema)
def create_config(config_data: ConfigDhanSchema, db: Session = Depends(get_db)):
    """Create or update Dhan API configuration"""
    existing = db.query(ConfigDhan).first()
    if existing:
        for key, value in config_data.dict(exclude_unset=True).items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        logger.info("Config updated")
        return existing
    config = ConfigDhan(**config_data.dict())
    db.add(config)
    db.commit()
    db.refresh(config)
    logger.info("Config created")
    return config


@router.put("/", response_model=ConfigDhanSchema)
def update_config(config_data: ConfigDhanUpdate, db: Session = Depends(get_db)):
    """Update Dhan API configuration"""
    config = db.query(ConfigDhan).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    update_data = config_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    logger.info("Config updated")
    return config


@router.get("/test-connection")
def test_connection(db: Session = Depends(get_db)):
    """Test Dhan API connection"""
    from ..services.dhan_client import get_dhan_client
    config = db.query(ConfigDhan).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    try:
        client = get_dhan_client(db)
        # Try a simple API call
        profile = client.get_fund_limits()
        return {"status": "connected", "message": "Successfully connected to Dhan API", "data": profile}
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")
