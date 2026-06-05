from typing import Optional

from app.schemas.base import AuditMixin, TransfermarktBaseModel


class PlayerNationalTeam(TransfermarktBaseModel, AuditMixin):
    id: str
    is_international: bool = False
    is_former: bool = False
    national_team: Optional[str] = None
    national_team_id: Optional[str] = None
    caps: Optional[int] = None
    goals: Optional[int] = None
