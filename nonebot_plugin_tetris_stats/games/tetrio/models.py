from datetime import datetime
from uuid import UUID

from nonebot_plugin_orm import Model
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ...db.models import PydanticType
from .api.schemas.leaderboards.by import BySuccessModel, Entry
from .api.typedefs import ValidRank
from .typedefs import Template


class TETRIOUserConfig(MappedAsDataclass, Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    query_template: Mapped[Template] = mapped_column(String(2))


class TETRIOLeagueStats(MappedAsDataclass, Model):
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    raw: Mapped[list['TETRIOLeagueHistorical']] = relationship(back_populates='stats', lazy='noload')
    fields: Mapped[list['TETRIOLeagueStatsField']] = relationship(back_populates='stats')
    update_time: Mapped[datetime] = mapped_column(DateTime, index=True)


class TETRIOLeagueHistorical(MappedAsDataclass, Model):
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    request_id: Mapped[UUID] = mapped_column(index=True)
    data: Mapped[BySuccessModel] = mapped_column(PydanticType([], {BySuccessModel}))
    update_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    stats_id: Mapped[int] = mapped_column(ForeignKey('nonebot_plugin_tetris_stats_tetrioleaguestats.id'), init=False)
    stats: Mapped['TETRIOLeagueStats'] = relationship(back_populates='raw')


entry_type = PydanticType([], {Entry})


class TETRIOLeagueStatsField(MappedAsDataclass, Model):
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    rank: Mapped[ValidRank] = mapped_column(String(2), index=True)
    tr_line: Mapped[float]
    player_count: Mapped[int]
    low_pps: Mapped[Entry] = mapped_column(entry_type)
    low_apm: Mapped[Entry] = mapped_column(entry_type)
    low_vs: Mapped[Entry] = mapped_column(entry_type)
    avg_pps: Mapped[float]
    avg_apm: Mapped[float]
    avg_vs: Mapped[float]
    high_pps: Mapped[Entry] = mapped_column(entry_type)
    high_apm: Mapped[Entry] = mapped_column(entry_type)
    high_vs: Mapped[Entry] = mapped_column(entry_type)
    stats_id: Mapped[int] = mapped_column(ForeignKey('nonebot_plugin_tetris_stats_tetrioleaguestats.id'), init=False)
    stats: Mapped['TETRIOLeagueStats'] = relationship(back_populates='fields')
