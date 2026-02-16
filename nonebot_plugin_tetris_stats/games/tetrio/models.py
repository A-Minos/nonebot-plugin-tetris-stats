from datetime import datetime, timedelta
from uuid import UUID

from nonebot_plugin_orm import Model
from sqlalchemy import DateTime, ForeignKey, Integer, Interval, String, UniqueConstraint
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ...db.models import PydanticType
from .api.schemas.leaderboards.by import BySuccessModel, Entry
from .api.typedefs import ValidRank
from .typedefs import Template


class TETRIOUserConfig(MappedAsDataclass, Model):
    __tablename__ = 'nb_t_io_u_cfg'

    id: Mapped[int] = mapped_column(primary_key=True)
    query_template: Mapped[Template] = mapped_column(String(2))
    compare_delta: Mapped[timedelta | None] = mapped_column(Interval(native=True), nullable=True)


class TETRIOLeagueStats(MappedAsDataclass, Model):
    __tablename__ = 'nb_t_io_tl_stats'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    raw: Mapped[list['TETRIOLeagueHistorical']] = relationship(back_populates='stats', lazy='noload')
    fields: Mapped[list['TETRIOLeagueStatsField']] = relationship(back_populates='stats')
    update_time: Mapped[datetime] = mapped_column(DateTime, index=True)


class TETRIOLeagueHistorical(MappedAsDataclass, Model):
    __tablename__ = 'nb_t_io_tl_hist'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    request_id: Mapped[UUID] = mapped_column(index=True)
    data: Mapped[BySuccessModel] = mapped_column(PydanticType([], {BySuccessModel}))
    update_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    stats_id: Mapped[int] = mapped_column(ForeignKey('nb_t_io_tl_stats.id'), init=False)
    stats: Mapped['TETRIOLeagueStats'] = relationship(back_populates='raw')


entry_type = PydanticType([], {Entry})


class TETRIOLeagueStatsField(MappedAsDataclass, Model):
    __tablename__ = 'nb_t_io_tl_stats_field'

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
    stats_id: Mapped[int] = mapped_column(ForeignKey('nb_t_io_tl_stats.id'), init=False)
    stats: Mapped['TETRIOLeagueStats'] = relationship(back_populates='fields')


class TETRIOUserUniqueIdentifier(MappedAsDataclass, Model):
    __tablename__ = 'nb_t_io_uid'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    user_unique_identifier: Mapped[str] = mapped_column(String(24), unique=True, index=True)


class TETRIOLeagueUserMap(MappedAsDataclass, Model):
    __tablename__ = 'nb_t_io_tl_map'
    __table_args__ = (UniqueConstraint('uid_id', 'hist_id', name='uq_nb_t_io_tl_map_uid_hist'),)

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    stats_id: Mapped[int] = mapped_column(ForeignKey('nb_t_io_tl_stats.id'), index=True)
    uid_id: Mapped[int] = mapped_column(ForeignKey('nb_t_io_uid.id'), index=True)
    hist_id: Mapped[int] = mapped_column(ForeignKey('nb_t_io_tl_hist.id'))
    entry_index: Mapped[int] = mapped_column(Integer)
