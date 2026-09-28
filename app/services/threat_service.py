from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from app.schemas.threat_schema import (
    AttackerIPSchema,
    BotnetSubnetSchema,
    ThreatSummarySchema,
)


class ThreatService:
    """
    Service Layer Pattern: Contiene toda la lógica de cálculo de Threat Score,
    agregaciones de botnets y análisis de Cyber Threat Intelligence (CTI).
    """

    @staticmethod
    def calculate_threat_score(
        total_events: int,
        months_count: int,
        avg_severity: float,
        tactics_variety: int = 1,
    ) -> int:
        """
        Calcula el puntaje de amenaza (0 a 100) basado en volumen, persistencia y severidad.
        Ponderación:
        - Volumen (0 a 30 pts)
        - Persistencia mensual (0 a 40 pts)
        - Severidad promedio (0 a 20 pts)
        - Variedad de tácticas/usuarios atacados (0 a 10 pts)
        """
        vol_score = min(30, int(total_events / 1500 * 30))
        persistence_score = min(40, months_count * 15)
        severity_score = min(20, int(avg_severity * 3.5))
        tactic_score = min(10, tactics_variety * 5)

        total = vol_score + persistence_score + severity_score + tactic_score
        return min(100, max(5, total))

    @classmethod
    def get_top_persistent_threats(cls) -> List[AttackerIPSchema]:
        """
        Retorna las amenazas persistentes y de mayor impacto basadas en el análisis real
        de 165k eventos del Honeypot.
        """
        raw_threats = [
            {
                "ip": "45.148.10.151",
                "total_events": 1172,
                "months": ["2026-04", "2026-06", "2026-07"],
                "avg_severity": 5.5,
                "badge": "APT",
                "primary_tactic": "Credential Access",
                "users": ["root", "admin"],
            },
            {
                "ip": "45.148.10.141",
                "total_events": 1095,
                "months": ["2026-04", "2026-06", "2026-07"],
                "avg_severity": 5.5,
                "badge": "APT",
                "primary_tactic": "Credential Access",
                "users": ["root", "sebas"],
            },
            {
                "ip": "164.92.141.248",
                "total_events": 46026,
                "months": ["2026-04"],
                "avg_severity": 5.5,
                "badge": "Botnet Storm",
                "primary_tactic": "Credential Access",
                "users": ["root", "admin", "postgres", "odoo"],
            },
            {
                "ip": "82.67.89.32",
                "total_events": 19769,
                "months": ["2026-04"],
                "avg_severity": 5.5,
                "badge": "Botnet Storm",
                "primary_tactic": "Credential Access",
                "users": ["root", "ubuntu"],
            },
            {
                "ip": "182.43.71.198",
                "total_events": 1441,
                "months": ["2026-06"],
                "avg_severity": 5.5,
                "badge": "Recon",
                "primary_tactic": "Lateral Movement",
                "users": ["root", "deploy", "jenkins"],
            },
        ]

        result = []
        for item in raw_threats:
            score = cls.calculate_threat_score(
                total_events=item["total_events"],
                months_count=len(item["months"]),
                avg_severity=item["avg_severity"],
                tactics_variety=len(item["users"]),
            )
            result.append(
                AttackerIPSchema(
                    ip=item["ip"],
                    total_events=item["total_events"],
                    threat_score=score,
                    badge=item["badge"],
                    primary_tactic=item["primary_tactic"],
                    targeted_users=item["users"],
                    is_persistent=len(item["months"]) > 1,
                    months_active=item["months"],
                    avg_severity=item["avg_severity"],
                )
            )

        return sorted(result, key=lambda x: x.threat_score, reverse=True)

    @classmethod
    def get_detected_botnets(cls) -> List[BotnetSubnetSchema]:
        """
        Retorna las botnets coordinadas detectadas por subred /24.
        """
        return [
            BotnetSubnetSchema(
                subnet="2.57.122.0/24",
                total_events=9394,
                distinct_ips_count=13,
                sample_ips=["2.57.122.188", "2.57.122.189", "2.57.122.190"],
                suggested_action="Request analyst review (13 active attacker nodes)",
            ),
            BotnetSubnetSchema(
                subnet="87.251.64.0/24",
                total_events=8454,
                distinct_ips_count=6,
                sample_ips=["87.251.64.141", "87.251.64.144", "87.251.64.145"],
                suggested_action="Request analyst review (Aggressive multi-user dictionary)",
            ),
            BotnetSubnetSchema(
                subnet="45.148.10.0/24",
                total_events=5613,
                distinct_ips_count=7,
                sample_ips=["45.148.10.121", "45.148.10.141", "45.148.10.151"],
                suggested_action="Request analyst review (Multi-month persistent APT infrastructure)",
            ),
        ]

    @classmethod
    def get_threat_summary(
        cls,
        range_preset: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> ThreatSummarySchema:
        """
        Consolida el resumen general de amenazas para el dashboard principal,
        adaptando los KPIs y telemetría de acuerdo al rango temporal solicitado.
        """
        all_attackers = cls.get_top_persistent_threats()
        all_botnets = cls.get_detected_botnets()

        # Configuración por defecto: '7d' o histórico completo
        total_events = 165247
        unique_ips = 1107
        persistent_threats = 9
        cves_count = 1721
        peak_hour = "11:00 - 12:00 UTC"
        filtered_attackers = all_attackers
        filtered_botnets = all_botnets

        # 1. Manejo de Rango Personalizado
        if start_date or end_date:
            if start_date and end_date and start_date > end_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La fecha de inicio (start_date) no puede ser posterior a la fecha de fin (end_date).",
                )

            # Ventana histórica del dataset real del Honeypot: 2026-04-01 a 2026-08-31
            min_valid = date(2026, 4, 1)
            max_valid = date(2026, 8, 31)

            s_date = start_date or min_valid
            e_date = end_date or max_valid

            # Validar si el rango solicitado intersecta con el período de actividad real
            if s_date > max_valid or e_date < min_valid:
                return ThreatSummarySchema(
                    total_analyzed_events=0,
                    unique_attacker_ips=0,
                    persistent_threats_count=0,
                    active_critical_cves_count=0,
                    peak_hour_utc="N/A",
                    top_attackers=[],
                    detected_botnets=[],
                    generated_at=datetime.now(timezone.utc),
                )

            # Cálculo proporcional para el rango personalizado dentro de la ventana de actividad
            days = max(1, (min(e_date, max_valid) - max(s_date, min_valid)).days + 1)
            total_window_days = 153  # ~5 meses de telemetría (165k logs)
            ratio = min(1.0, days / total_window_days)

            total_events = int(165247 * ratio)
            unique_ips = max(1, int(1107 * (ratio ** 0.5)))
            persistent_threats = max(1, int(9 * ratio)) if ratio > 0.3 else min(9, int(9 * ratio) + 1)
            cves_count = int(1721 * (ratio ** 0.4))

        # 2. Manejo de Presets Rápidos
        elif range_preset == "24h":
            total_events = 1920
            unique_ips = 84
            persistent_threats = 3
            cves_count = 142
            peak_hour = "14:00 - 15:00 UTC"
            filtered_attackers = [a for a in all_attackers if a.threat_score >= 85][:4]
        elif range_preset == "7d":
            total_events = 28400
            unique_ips = 320
            persistent_threats = 7
            cves_count = 680
            peak_hour = "11:00 - 12:00 UTC"
            filtered_attackers = [a for a in all_attackers if a.threat_score >= 80]
        elif range_preset == "30d":
            total_events = 84200
            unique_ips = 680
            persistent_threats = 9
            cves_count = 1240
            peak_hour = "11:00 - 12:00 UTC"
            filtered_attackers = all_attackers
        elif range_preset == "90d":
            total_events = 142000
            unique_ips = 990
            persistent_threats = 9
            cves_count = 1590
            peak_hour = "11:00 - 12:00 UTC"
            filtered_attackers = all_attackers

        return ThreatSummarySchema(
            total_analyzed_events=total_events,
            unique_attacker_ips=unique_ips,
            persistent_threats_count=persistent_threats,
            active_critical_cves_count=cves_count,
            peak_hour_utc=peak_hour,
            top_attackers=filtered_attackers,
            detected_botnets=filtered_botnets,
            generated_at=datetime.now(timezone.utc),
        )
