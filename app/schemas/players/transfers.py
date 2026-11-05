from datetime import date
from typing import Optional

from app.schemas.base import AuditMixin, TransfermarktBaseModel


class PlayerTransferClub(TransfermarktBaseModel):
    id: str
    name: str


class PlayerTransfer(TransfermarktBaseModel):
    id: str
    club_from: PlayerTransferClub
    club_to: PlayerTransferClub
    date: date
    date_raw: Optional[str]
    upcoming: bool
    season: str
    market_value: Optional[int]
    fee: Optional[int]
    fee_raw: Optional[str]


class PlayerTransfers(TransfermarktBaseModel, AuditMixin):
    id: str
    transfers: list[PlayerTransfer]
    youth_clubs: Optional[list[str]]
