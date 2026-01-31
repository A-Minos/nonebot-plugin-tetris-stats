"""fix json storage

迁移 ID: 1c5346b657d4
父迁移: 2ff388a8c486
创建时间: 2026-01-30 03:35:00

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import msgspec
import sqlalchemy as sa
from alembic import op
from nonebot.log import logger
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.engine import Connection

_LOG_INTERVAL = 10000
_BATCH_SIZE = 1000
_PG_CHUNK_SIZE = 50000
_SQLITE_FETCH_SIZE = 500

revision: str = '1c5346b657d4'
down_revision: str | Sequence[str] | None = '2ff388a8c486'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

tables: dict[str, list[str]] = {
    'nb_t_io_tl_stats_field': [
        'low_pps',
        'low_apm',
        'low_vs',
        'high_pps',
        'high_apm',
        'high_vs',
    ],
    'nb_t_io_hist_data': ['data'],
    'nb_t_top_hist_data': ['data'],
    'nb_t_tos_hist_data': ['data'],
    'nb_t_io_tl_hist': ['data'],
}


def _pg_convert_column(conn: Connection, table: str, column: str) -> None:
    tbl = sa.table(table, sa.column('id'), sa.column(column))
    col = getattr(tbl.c, column)
    path = sa.cast(sa.literal('{}'), ARRAY(sa.Text))
    payload = sa.cast(sa.cast(col, JSONB).op('#>>')(path), sa.JSON)
    base = sa.func.json_typeof(col) == 'string'
    min_max_stmt = sa.select(sa.func.min(tbl.c.id), sa.func.max(tbl.c.id)).where(base)
    result = conn.execute(min_max_stmt).one()
    if result[0] is None or result[1] is None:
        return
    start_id, end_id = result
    total = end_id - start_id + 1
    processed = 0
    context = op.get_context()
    with context.autocommit_block():
        for chunk_start in range(start_id, end_id + 1, _PG_CHUNK_SIZE):
            chunk_end = min(chunk_start + _PG_CHUNK_SIZE - 1, end_id)
            stmt = (
                sa.update(tbl).values({column: payload}).where(base).where(sa.between(tbl.c.id, chunk_start, chunk_end))
            )
            conn.execute(stmt)
            processed += chunk_end - chunk_start + 1
            logger.warning(
                f'tetris_stats: converting {table}.{column} chunk {chunk_start}-{chunk_end} '
                f'processed={processed}/{total}'
            )
    remaining_stmt = sa.select(sa.func.count()).select_from(tbl).where(base)
    remaining = conn.execute(remaining_stmt).scalar()
    if remaining:
        msg = f'json storage fix failed: {table}.{column} still has string rows'
        raise ValueError(msg)


def _pg_convert(conn: Connection) -> None:
    for table, columns in tables.items():
        for column in columns:
            logger.warning(f'tetris_stats: converting {table}.{column} from json string to object')
            _pg_convert_column(conn, table, column)


def _convert_table_python(conn: Connection, table_name: str, columns: list[str]) -> None:  # noqa: C901
    meta = sa.MetaData()
    table = sa.Table(table_name, meta, autoload_with=conn)
    update_stmt = (
        table.update().where(table.c.id == sa.bindparam('b_id')).values(**{col: sa.bindparam(col) for col in columns})
    )
    batch: list[dict[str, object]] = []
    last_id = 0
    processed = 0
    while True:
        rows = (
            conn.execute(
                sa.select(table.c.id, *[table.c[col] for col in columns])
                .where(table.c.id > last_id)
                .order_by(table.c.id)
                .limit(_SQLITE_FETCH_SIZE)
            )
            .mappings()
            .all()
        )
        if not rows:
            break
        for row in rows:
            last_id = row['id']
            processed += 1
            update_values: dict[str, object] = {'b_id': row['id']}
            changed = False
            for column in columns:
                value = row[column]
                if isinstance(value, str | bytes):
                    parsed = msgspec.json.decode(value)
                    if not isinstance(parsed, dict | list):
                        msg = f'json storage fix failed: {table_name}.{column} value is not object'
                        raise TypeError(msg)
                    update_values[column] = parsed
                    changed = True
                elif isinstance(value, dict | list):
                    update_values[column] = value
                else:
                    msg = f'json storage fix failed: {table_name}.{column} invalid type {type(value)}'
                    raise TypeError(msg)
            if changed:
                batch.append(update_values)
            if processed % _LOG_INTERVAL == 0:
                logger.warning(f'tetris_stats: converting {table_name} processed={processed}')
            if len(batch) >= _BATCH_SIZE:
                conn.execute(update_stmt, batch)
                batch.clear()
    if batch:
        conn.execute(update_stmt, batch)


def _generic_convert(conn: Connection) -> None:
    for table, columns in tables.items():
        logger.warning(f'tetris_stats: converting {table} via python')
        _convert_table_python(conn, table, columns)


def upgrade(name: str = '') -> None:
    if name:
        return
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        _pg_convert(conn)
    else:
        _generic_convert(conn)


def downgrade(name: str = '') -> None:
    if name:
        return
