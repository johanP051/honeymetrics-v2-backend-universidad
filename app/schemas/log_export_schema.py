from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

# Límite máximo de rango de exportación (prevención DoS / overflow de fechas)
MAX_EXPORT_RANGE_DAYS = 365


class LogExportRequest(BaseModel):
    start_date: date = Field(..., alias="startDate", description="Fecha de inicio de extracción (YYYY-MM-DD)")
    end_date: date = Field(..., alias="endDate", description="Fecha de fin de extracción (YYYY-MM-DD)")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def validate_date_window(self) -> "LogExportRequest":
        """Anti-DoS: rechaza rangos invertidos, fechas futuras y ventanas > 365 días."""
        if self.start_date > self.end_date:
            raise ValueError("La fecha de inicio debe ser anterior o igual a la fecha de fin.")
        if self.end_date > date.today():
            raise ValueError("No se puede exportar logs de fechas futuras (endDate no puede estar en el futuro).")
        if (self.end_date - self.start_date).days >= MAX_EXPORT_RANGE_DAYS:
            raise ValueError(f"El rango de exportación no puede exceder {MAX_EXPORT_RANGE_DAYS} días.")
        return self


class LogExportResponse(BaseModel):
    id: str = Field(..., description="Identificador correlativo de la exportación (ej. EXP-1045)")
    status: Literal["Listo", "Procesando", "Pendiente de Aprobación", "Rechazada", "Expirado"] = Field(
        ..., description="Estado de la solicitud de exportación"
    )
    count: int = Field(..., description="Cantidad estimada o real de logs a procesar")
    message: str = Field(..., description="Mensaje informativo para el usuario")


class LogExportItemResponse(BaseModel):
    id: str = Field(..., description="Identificador de la exportación (ej. EXP-1045)")
    date_range: str = Field(..., description="Rango de fechas legible")
    count: int = Field(..., description="Cantidad de registros")
    status: Literal["Listo", "Procesando", "Pendiente de Aprobación", "Rechazada", "Expirado"] = Field(
        ..., description="Estado actual de la exportación"
    )
    created_at: str = Field(..., description="Fecha y hora de solicitud formateada para presentación")
    file_format: str = Field(default="JSONL", description="Formato del archivo de exportación")

    model_config = ConfigDict(from_attributes=True)


class LogReportStatsResponse(BaseModel):
    labels: list[str] = Field(
        ...,
        description="Lista de decoders de Wazuh (rootcheck, kernel, syscheck, etc.)",
    )
    values: list[int] = Field(..., description="Porcentajes o conteos relativos por decoder")
    total_logs: int = Field(..., description="Total de logs agregados en la muestra")
    start_date: str = Field(..., description="Fecha inicial en formato ISO YYYY-MM-DD")
    end_date: str = Field(..., description="Fecha final en formato ISO YYYY-MM-DD")
