from datetime import datetime, timezone

from nonebot_plugin_orm import Model
from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from .typing import Rank

UTC = timezone.utc


class IORank(MappedAsDataclass, Model):
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    rank: Mapped[Rank] = mapped_column(String(2), index=True)
    tr_line: Mapped[float]
    player_count: Mapped[int]
    low_pps: Mapped[tuple[dict[str, str], float]] = mapped_column(JSON)
    low_apm: Mapped[tuple[dict[str, str], float]] = mapped_column(JSON)
    low_vs: Mapped[tuple[dict[str, str], float]] = mapped_column(JSON)
    avg_pps: Mapped[float]
    avg_apm: Mapped[float]
    avg_vs: Mapped[float]
    high_pps: Mapped[tuple[dict[str, str], float]] = mapped_column(JSON)
    high_apm: Mapped[tuple[dict[str, str], float]] = mapped_column(JSON)
    high_vs: Mapped[tuple[dict[str, str], float]] = mapped_column(JSON)
    create_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(tz=UTC),
        index=True,
        init=False,
    )
