"""
Servicio de Métricas y Reporte Ejecutivo del Dashboard.
HoneyMetrics Backend v2.0 (UDEC)
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.blacklist_model import BlacklistEntry
from app.models.log_export_model import LogExport
from app.models.user_model import User


class DashboardService:
    @staticmethod
    def get_executive_report(db: Session) -> dict:
        total_threats = db.query(BlacklistEntry).count()
        blocked_threats = (
            db.query(BlacklistEntry)
            .filter(BlacklistEntry.status.in_(["Bloqueada", "Blocked"]))
            .count()
        )

        top_countries = (
            db.query(BlacklistEntry.country, func.count(BlacklistEntry.id).label("total"))
            .group_by(BlacklistEntry.country)
            .order_by(func.count(BlacklistEntry.id).desc())
            .limit(5)
            .all()
        )

        total_users = db.query(User).count()
        total_exports = db.query(LogExport).count()
        average_score = (
            db.query(func.coalesce(func.avg(BlacklistEntry.threat_score), 0)).scalar() or 0
        )
        top_threats = (
            db.query(BlacklistEntry)
            .order_by(BlacklistEntry.threat_score.desc(), BlacklistEntry.updated_at.desc())
            .limit(10)
            .all()
        )

        return {
            "summary": {
                "total_threats_tracked": total_threats,
                "active_blocks": blocked_threats,
                "registered_users": total_users,
                "total_forensic_exports": total_exports,
                "average_threat_score": round(float(average_score), 2),
            },
            "threat_landscape": {
                "top_countries": [
                    {"country": c[0] or "Unknown", "count": int(c[1])} for c in top_countries
                ],
                "top_threats": [
                    {
                        "ip": threat.ip,
                        "score": threat.threat_score,
                        "category": threat.category or "Unknown",
                        "status": threat.status or "Monitoreada",
                    }
                    for threat in top_threats
                ],
            },
        }
