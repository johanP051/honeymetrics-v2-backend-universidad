from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class LogExportRequest(BaseModel):
    start_date: date = Field(..., alias="startDate", description="Fecha de inicio de extracción (YYYY-MM-DD)")
    end_date: date = Field(..., alias="endDate", description="Fecha de fin de extracción (YYYY-MM-DD)")

    model_config = ConfigDict(populate_by_name=True)


class LogExportResponse(BaseModel):
    id: str = Field(..., description="Identificador correlativo de la exportación (ej. EXP-1045)")
    status: Literal["Listo", "Procesando", "Pendiente de Aprobación", "Rechazada"] = Field(
        ..., description="Estado de la solicitud de exportación"
    )
    count: int = Field(..., description="Cantidad estimada o real de logs a procesar")
    message: str = Field(..., description="Mensaje informativo para el usuario")


class LogExportItemResponse(BaseModel):
    id: str = Field(..., description="Identificador de la exportación (ej. EXP-1045)")
    date_range: str = Field(..., description="Rango de fechas legible")
    count: int = Field(..., description="Cantidad de registros")
    status: Literal["Listo", "Procesando", "Pendiente de Aprobación", "Rechazada"] = Field(
        ..., description="Estado actual de la exportación"
    )
    created_at: str = Field(..., description="Fecha y hora de solicitud formateada para presentación")
    file_format: str = Field(default="JSONL", description="Formato del archivo de exportación")

    model_config = ConfigDict(from_attributes=True)


class LogReportStatsResponse(BaseModel):
    labels: list[str] = Field(..., description="Lista de decoders de Wazuh (rootcheck, kernel, syscheck, etc.)")
    values: list[int] = Field(..., description="Porcentajes o conteos relativos por decoder")
    total_logs: int = Field(..., description="Total de logs agregados en la muestra")
    start_date: str = Field(..., description="Fecha inicial en formato ISO YYYY-MM-DD")
    end_date: str = Field(..., description="Fecha final en formato ISO YYYY-MM-DD")
