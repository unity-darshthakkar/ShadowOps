from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from backend.database import Base


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(String, primary_key=True, index=True)
    scenario_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    result_json = Column(Text, nullable=True)
