"""add io tl map

迁移 ID: 3a294ff14610
父迁移: 6ecf383d646a
创建时间: 2026-01-28 03:25:40.714853

"""

from __future__ import annotations

import os
import re
import time
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from nonebot.log import logger
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    Task,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    filesize,
)
from rich.text import Text
from sqlalchemy import Connection, text
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from typing_extensions import override

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = '3a294ff14610'
down_revision: str | Sequence[str] | None = '6ecf383d646a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class RateColumn(ProgressColumn):
    """Renders human readable processing rate."""

    @override
    def render(self, task: Task) -> Text:
        """Render the speed in iterations per second."""

        def calculate_speed() -> float | None:
            now = time.monotonic()

            if task.start_time is not None:
                elapsed = (task.finished_time or now) - task.start_time
                if elapsed > 0:
                    return task.completed / elapsed
            return None

        speed = task.finished_speed or task.speed or calculate_speed()

        if speed is None:
            return Text('', style='progress.percentage')
        unit, suffix = filesize.pick_unit_and_suffix(
            int(speed),
            ['', '×10³', '×10⁶', '×10⁹', '×10¹²'],  # noqa: RUF001
            1000,
        )
        data_speed = speed / unit
        return Text(f'{data_speed:.1f}{suffix} it/s', style='progress.percentage')


def _backfill_postgresql(conn: Connection, chunk_size: int = 20000) -> None:
    result = conn.execute(text('SELECT min(id), max(id) FROM nb_t_io_tl_hist')).one()
    if result[0] is None or result[1] is None:
        return
    min_id, max_id = result
    total = max_id - min_id + 1

    logger.warning('PG backfill: Disabling foreign key constraints...')

    work_mem = os.getenv('TETRIS_STATS_MIGRATION_WORK_MEM', '256MB')
    if not re.fullmatch(r'\d+(kB|MB|GB)', work_mem):
        work_mem = '256MB'
    conn.execute(
        text("SELECT set_config('work_mem', :work_mem, true)"),
        {'work_mem': work_mem},
    )
    temp_buffers = os.getenv('TETRIS_STATS_MIGRATION_TEMP_BUFFERS', '128MB')
    if not re.fullmatch(r'\d+(kB|MB|GB)', temp_buffers):
        temp_buffers = '128MB'
    conn.execute(
        text("SELECT set_config('temp_buffers', :temp_buffers, true)"),
        {'temp_buffers': temp_buffers},
    )
    conn.execute(text('SET LOCAL synchronous_commit = off'))

    logger.warning('tetris_stats: PG backfill synchronous_commit=off')
    logger.warning(f'tetris_stats: PG backfill work_mem={work_mem}')
    logger.warning(f'tetris_stats: PG backfill temp_buffers={temp_buffers}')

    conn.execute(text('SET LOCAL max_parallel_workers_per_gather = 8'))
    conn.execute(text('SET LOCAL parallel_setup_cost = 10'))
    conn.execute(text('SET LOCAL parallel_tuple_cost = 0.01'))

    logger.warning('tetris_stats: PG backfill max_parallel_workers_per_gather=8')
    logger.warning('tetris_stats: PG backfill parallel_setup_cost=10')
    logger.warning('tetris_stats: PG backfill parallel_tuple_cost=0.01')

    with Progress(
        TextColumn('[progress.description]{task.description}'),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        RateColumn(),
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task('生成索引...', total=total)
        for start_id in range(min_id, max_id + 1, chunk_size):
            end_id = min(start_id + chunk_size - 1, max_id)
            conn.execute(
                text(
                    """
                    WITH entries AS (
                        SELECT
                            h.stats_id,
                            h.id AS hist_id,
                            e.ordinality - 1 AS entry_index,
                            COALESCE(e.entry->>'_id', e.entry->>'id') AS uid_str
                        FROM nb_t_io_tl_hist h
                        CROSS JOIN LATERAL jsonb_array_elements(h.data::jsonb->'data'->'entries')
                            WITH ORDINALITY AS e(entry, ordinality)
                        WHERE h.id BETWEEN :start_id AND :end_id
                        AND COALESCE(e.entry->>'_id', e.entry->>'id') IS NOT NULL
                    ),
                    upserted_uids AS (
                        INSERT INTO nb_t_io_uid (user_unique_identifier)
                        SELECT DISTINCT uid_str FROM entries
                        ON CONFLICT (user_unique_identifier)
                        DO UPDATE SET user_unique_identifier = EXCLUDED.user_unique_identifier
                        RETURNING id, user_unique_identifier
                    )
                    INSERT INTO nb_t_io_tl_map (stats_id, uid_id, hist_id, entry_index)
                    SELECT e.stats_id, u.id, e.hist_id, e.entry_index
                    FROM entries e
                    JOIN upserted_uids u ON u.user_unique_identifier = e.uid_str
                """
                ),
                {'start_id': start_id, 'end_id': end_id},
            )
            progress.update(task, advance=end_id - start_id + 1)


def _add_foreign_keys_postgresql(conn: Connection) -> None:
    logger.warning('PG backfill: Re-adding foreign key constraints (validating)...')

    conn.execute(
        text("""
        ALTER TABLE nb_t_io_tl_map
        ADD CONSTRAINT fk_nb_t_io_tl_map_hist_id_nb_t_io_tl_hist
        FOREIGN KEY (hist_id) REFERENCES nb_t_io_tl_hist(id)
        NOT VALID
    """)
    )
    conn.execute(
        text("""
        ALTER TABLE nb_t_io_tl_map
        VALIDATE CONSTRAINT fk_nb_t_io_tl_map_hist_id_nb_t_io_tl_hist
    """)
    )

    conn.execute(
        text("""
        ALTER TABLE nb_t_io_tl_map
        ADD CONSTRAINT fk_nb_t_io_tl_map_stats_id_nb_t_io_tl_stats
        FOREIGN KEY (stats_id) REFERENCES nb_t_io_tl_stats(id)
        NOT VALID
    """)
    )
    conn.execute(
        text("""
        ALTER TABLE nb_t_io_tl_map
        VALIDATE CONSTRAINT fk_nb_t_io_tl_map_stats_id_nb_t_io_tl_stats
    """)
    )

    conn.execute(
        text("""
        ALTER TABLE nb_t_io_tl_map
        ADD CONSTRAINT fk_nb_t_io_tl_map_uid_id_nb_t_io_uid
        FOREIGN KEY (uid_id) REFERENCES nb_t_io_uid(id)
        NOT VALID
    """)
    )
    conn.execute(
        text("""
        ALTER TABLE nb_t_io_tl_map
        VALIDATE CONSTRAINT fk_nb_t_io_tl_map_uid_id_nb_t_io_uid
    """)
    )

    logger.success('PG backfill: Foreign keys validated successfully')


def _backfill_generic(conn: Connection) -> None:
    Base = automap_base()  # noqa: N806
    Base.prepare(autoload_with=conn)
    Hist = Base.classes.nb_t_io_tl_hist  # noqa: N806
    Uid = Base.classes.nb_t_io_uid  # noqa: N806
    Map = Base.classes.nb_t_io_tl_map  # noqa: N806

    with Session(conn) as session:
        count = session.query(Hist).count()
        if count == 0:
            return

        logger.warning('tetris_stats: 正在生成 TETR.IO 玩家分页索引, 请不要关闭程序...')
        uid_map: dict[str, int] = {}

        def refresh_uid_map() -> None:
            uids = session.query(Uid).all()
            uid_map.clear()
            uid_map.update({uid.user_unique_identifier: uid.id for uid in uids})

        with Progress(
            TextColumn('[progress.description]{task.description}'),
            BarColumn(),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            RateColumn(),
            TimeRemainingColumn(),
        ) as progress:
            total = progress.add_task('生成索引...', total=count)
            for hist in session.query(Hist).yield_per(1):
                data = hist.data
                if isinstance(data, str | bytes):
                    msg = 'io tl map migration requires json object data'
                    raise TypeError(msg)
                entries = data.get('data', {}).get('entries', []) if isinstance(data, dict) else []
                entry_info: list[tuple[str, int]] = []
                for index, entry in enumerate(entries):
                    if isinstance(entry, dict):
                        uid = entry.get('_id')
                        if isinstance(uid, str):
                            entry_info.append((uid, index))
                if not entry_info:
                    progress.update(total, advance=1)
                    continue

                session.add_all([Uid(user_unique_identifier=uid) for uid, _ in entry_info if uid not in uid_map])
                session.flush()
                refresh_uid_map()
                session.add_all(
                    [
                        Map(
                            stats_id=hist.stats_id,
                            uid_id=uid_map[uid],
                            hist_id=hist.id,
                            entry_index=index,
                        )
                        for uid, index in entry_info
                    ]
                )
                session.flush()
                progress.update(total, advance=1)


def backfill_mapping(conn: Connection) -> None:
    if conn.dialect.name == 'postgresql':
        logger.warning('tetris_stats: 检测到 PostgreSQL, 使用快速索引回填...')
        _backfill_postgresql(conn)
        _add_foreign_keys_postgresql(conn)
        return
    _backfill_generic(conn)


def upgrade(name: str = '') -> None:
    if name:
        return
    conn = op.get_bind()
    op.create_table(
        'nb_t_io_uid',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_unique_identifier', sa.String(length=24), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_nb_t_io_uid')),
        info={'bind_key': 'nonebot_plugin_tetris_stats'},
    )
    with op.batch_alter_table('nb_t_io_uid', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_nb_t_io_uid_user_unique_identifier'),
            ['user_unique_identifier'],
            unique=True,
        )

    if conn.dialect.name == 'postgresql':
        op.create_table(
            'nb_t_io_tl_map',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('stats_id', sa.Integer(), nullable=False),
            sa.Column('uid_id', sa.Integer(), nullable=False),
            sa.Column('hist_id', sa.Integer(), nullable=False),
            sa.Column('entry_index', sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_nb_t_io_tl_map')),
            sa.UniqueConstraint('uid_id', 'hist_id', name='uq_nb_t_io_tl_map_uid_hist'),
            info={'bind_key': 'nonebot_plugin_tetris_stats'},
        )
    else:
        op.create_table(
            'nb_t_io_tl_map',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('stats_id', sa.Integer(), nullable=False),
            sa.Column('uid_id', sa.Integer(), nullable=False),
            sa.Column('hist_id', sa.Integer(), nullable=False),
            sa.Column('entry_index', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ['stats_id'],
                ['nb_t_io_tl_stats.id'],
                name=op.f('fk_nb_t_io_tl_map_stats_id_nb_t_io_tl_stats'),
            ),
            sa.ForeignKeyConstraint(
                ['uid_id'],
                ['nb_t_io_uid.id'],
                name=op.f('fk_nb_t_io_tl_map_uid_id_nb_t_io_uid'),
            ),
            sa.ForeignKeyConstraint(
                ['hist_id'],
                ['nb_t_io_tl_hist.id'],
                name=op.f('fk_nb_t_io_tl_map_hist_id_nb_t_io_tl_hist'),
            ),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_nb_t_io_tl_map')),
            sa.UniqueConstraint('uid_id', 'hist_id', name='uq_nb_t_io_tl_map_uid_hist'),
            info={'bind_key': 'nonebot_plugin_tetris_stats'},
        )
    backfill_mapping(conn)

    with op.batch_alter_table('nb_t_io_tl_map', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_nb_t_io_tl_map_stats_id'), ['stats_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_nb_t_io_tl_map_uid_id'), ['uid_id'], unique=False)


def downgrade(name: str = '') -> None:
    if name:
        return
    with op.batch_alter_table('nb_t_io_tl_map', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_nb_t_io_tl_map_uid_id'))
        batch_op.drop_index(batch_op.f('ix_nb_t_io_tl_map_stats_id'))

    op.drop_table('nb_t_io_tl_map')
    with op.batch_alter_table('nb_t_io_uid', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_nb_t_io_uid_user_unique_identifier'))

    op.drop_table('nb_t_io_uid')
