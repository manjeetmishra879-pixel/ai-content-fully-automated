"""
Trend detection and analysis service
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.models import Trend
from app.engines import get_engine


class TrendService:
    """Service for managing trends"""

    def __init__(self, db: Session, redis_client=None, vector_db=None):
        self.db = db
        self.redis = redis_client
        self.vector_db = vector_db
        self.trend_engine = get_engine("trend")
        self.viral_radar_engine = get_engine("viral_radar")

    async def fetch_trends(self, keyword: Optional[str] = None,
                          category: Optional[str] = None,
                          platforms: Optional[List[str]] = None,
                          limit: int = 20) -> Dict[str, Any]:
        """Fetch trends from multiple sources"""
        result = self.trend_engine.run(
            keyword=keyword,
            category=category,
            platforms=platforms,
            limit=limit
        )

        # Store trends in database
        stored_trends = []
        for trend in result.get("topics", []):
            # Check if trend already exists
            existing = self.db.query(Trend).filter(
                Trend.title == trend["title"],
                Trend.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).first()

            if not existing:
                db_trend = Trend(
                    title=trend["title"],
                    description=trend.get("description", ""),
                    category=category or "general",
                    viral_score=trend.get("viral_score", 0),
                    platforms=platforms or ["general"],
                    source=trend.get("source", "aggregated"),
                    extra_metadata=trend
                )
                self.db.add(db_trend)
                stored_trends.append(db_trend)
            else:
                stored_trends.append(existing)

        self.db.commit()

        return {
            "fetched_count": len(result.get("topics", [])),
            "stored_count": len(stored_trends),
            "trends": [
                {
                    "id": t.id,
                    "title": t.title,
                    "viral_score": t.viral_score,
                    "category": t.category,
                    "platforms": t.platforms,
                    "created_at": t.created_at.isoformat()
                } for t in stored_trends
            ]
        }

    async def get_viral_radar(self, platforms: Optional[List[str]] = None,
                             interval_minutes: int = 15) -> Dict[str, Any]:
        """Get real-time viral content radar"""
        # Use viral radar engine
        radar_data = self.viral_radar_engine.run(
            platforms=platforms,
            interval_minutes=interval_minutes
        )

        return radar_data

    async def analyze_trend_score(self, trend_title: str) -> Dict[str, Any]:
        """Calculate trend score and analysis"""
        # Get trend data from database
        trend = self.db.query(Trend).filter(Trend.title == trend_title).first()

        if not trend:
            return {"error": "Trend not found"}

        # Analyze with trend engine
        analysis = self.trend_engine.run(keyword=trend_title, limit=1)

        return {
            "trend": {
                "id": trend.id,
                "title": trend.title,
                "viral_score": trend.viral_score,
                "category": trend.category,
                "platforms": trend.platforms
            },
            "analysis": analysis
        }

    async def detect_rising_trends(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Detect rising fast trends"""
        since_time = datetime.utcnow() - timedelta(hours=hours_back)

        # Get recent trends
        recent_trends = self.db.query(Trend).filter(
            Trend.created_at >= since_time
        ).order_by(Trend.viral_score.desc()).limit(50).all()

        # Analyze for rising patterns
        rising_trends = []
        for trend in recent_trends:
            # Simple rising detection: high viral score and recent
            hours_old = (datetime.utcnow() - trend.created_at).total_seconds() / 3600
            if trend.viral_score > 70 and hours_old < 6:
                rising_trends.append({
                    "id": trend.id,
                    "title": trend.title,
                    "viral_score": trend.viral_score,
                    "category": trend.category,
                    "hours_old": round(hours_old, 1),
                    "platforms": trend.platforms
                })

        return rising_trends

    async def get_trending_topics(self, category: Optional[str] = None,
                                 limit: int = 10) -> List[Dict[str, Any]]:
        """Get currently trending topics"""
        query = self.db.query(Trend).filter(
            Trend.created_at >= datetime.utcnow() - timedelta(hours=24)
        )

        if category:
            query = query.filter(Trend.category == category)

        trends = query.order_by(Trend.viral_score.desc()).limit(limit).all()

        return [
            {
                "id": t.id,
                "title": t.title,
                "viral_score": t.viral_score,
                "category": t.category,
                "platforms": t.platforms,
                "created_at": t.created_at.isoformat()
            } for t in trends
        ]

    async def search_trends(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search trends by keyword"""
        trends = self.db.query(Trend).filter(
            Trend.title.ilike(f"%{query}%")
        ).order_by(Trend.viral_score.desc()).limit(limit).all()

        return [
            {
                "id": t.id,
                "title": t.title,
                "viral_score": t.viral_score,
                "category": t.category,
                "platforms": t.platforms,
                "description": t.description
            } for t in trends
        ]
