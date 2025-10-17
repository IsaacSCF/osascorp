from pydantic import BaseModel, field_validator
from datetime import date, datetime
from typing import Optional, List, Union

class OrgBase(BaseModel):
    faccao: str
    tags_fabricacao: Optional[Union[List[str], str]] = None
    contato: Optional[str] = None
    membros_ativos: Optional[int] = None
    data_entrega: Optional[date] = None
    discord_lider: Optional[str] = None
    tipo: str  # "LEGAL" or "ILEGAL"
    ativo: Optional[bool] = True
    entregue: Optional[bool] = False

    @field_validator('tags_fabricacao', mode='before')
    @classmethod
    def parse_tags_fabricacao(cls, v):
        if isinstance(v, str):
            # Split by comma, slash, or pipe and clean up
            tags = [tag.strip().strip('"').strip("'").strip('[').strip(']') for tag in v.replace('/', ',').replace('|', ',').split(',') if tag.strip()]
            return tags if tags else None
        return v

class OrgCreate(OrgBase):
    pass

class OrgUpdate(BaseModel):
    faccao: Optional[str] = None
    tags_fabricacao: Optional[List[str]] = None
    contato: Optional[str] = None
    membros_ativos: Optional[int] = None
    data_entrega: Optional[date] = None
    discord_lider: Optional[str] = None
    tipo: Optional[str] = None
    ativo: Optional[bool] = None
    entregue: Optional[bool] = None

class OrgResponse(OrgBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
