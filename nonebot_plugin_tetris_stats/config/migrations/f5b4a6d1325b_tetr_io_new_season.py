"""TETR.IO new season

迁移 ID: f5b4a6d1325b
父迁移: a1195e989cc6
创建时间: 2024-08-01 20:44:48.644912

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = 'f5b4a6d1325b'
down_revision: str | Sequence[str] | None = 'a1195e989cc6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = '') -> None:
    if name:
        return
    with op.batch_alter_table('nonebot_plugin_tetris_stats_iorank', schema=None) as batch_op:
        batch_op.drop_index('ix_nonebot_plugin_tetris_stats_iorank_file_hash')
        batch_op.drop_index('ix_nonebot_plugin_tetris_stats_iorank_rank')
        batch_op.drop_index('ix_nonebot_plugin_tetris_stats_iorank_update_time')

    op.drop_table('nonebot_plugin_tetris_stats_iorank')

    with op.batch_alter_table('nonebot_plugin_tetris_stats_tetriohistoricaldata', schema=None) as batch_op:
        batch_op.drop_index('ix_nonebot_plugin_tetris_stats_tetriohistoricaldata_api_type')
        batch_op.drop_index('ix_nonebot_plugin_tetris_stats_tetriohistoricaldata_update_time')
        batch_op.drop_index('ix_nonebot_plugin_tetris_stats_tetriohistoricaldata_user_unique_identifier')

    op.drop_table('nonebot_plugin_tetris_stats_tetriohistoricaldata')

    op.create_table(
        'nonebot_plugin_tetris_stats_tetriohistoricaldata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_unique_identifier', sa.String(length=24), nullable=False),
        sa.Column('api_type', sa.String(length=16), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('update_time', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_nonebot_plugin_tetris_stats_tetriohistoricaldata')),
        info={'bind_key': 'nonebot_plugin_tetris_stats'},
    )
    with op.batch_alter_table('nonebot_plugin_tetris_stats_tetriohistoricaldata', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_nonebot_plugin_tetris_stats_tetriohistoricaldata_api_type'), ['api_type'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_nonebot_plugin_tetris_stats_tetriohistoricaldata_update_time'), ['update_time'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_nonebot_plugin_tetris_stats_tetriohistoricaldata_user_unique_identifier'),
            ['user_unique_identifier'],
            unique=False,
        )


def downgrade(name: str = '') -> None:
    if name:
        return
    op.create_table(
        'nonebot_plugin_tetris_stats_iorank',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('rank', sa.VARCHAR(length=2), nullable=False),
        sa.Column('tr_line', sa.FLOAT(), nullable=False),
        sa.Column('player_count', sa.INTEGER(), nullable=False),
        sa.Column('low_pps', sa.JSON(), nullable=False),
        sa.Column('low_apm', sa.JSON(), nullable=False),
        sa.Column('low_vs', sa.JSON(), nullable=False),
        sa.Column('avg_pps', sa.FLOAT(), nullable=False),
        sa.Column('avg_apm', sa.FLOAT(), nullable=False),
        sa.Column('avg_vs', sa.FLOAT(), nullable=False),
        sa.Column('high_pps', sa.JSON(), nullable=False),
        sa.Column('high_apm', sa.JSON(), nullable=False),
        sa.Column('high_vs', sa.JSON(), nullable=False),
        sa.Column('update_time', sa.DATETIME(), nullable=False),
        sa.Column('file_hash', sa.VARCHAR(length=128), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_nonebot_plugin_tetris_stats_iorank'),
    )
    with op.batch_alter_table('nonebot_plugin_tetris_stats_iorank', schema=None) as batch_op:
        batch_op.create_index('ix_nonebot_plugin_tetris_stats_iorank_update_time', ['update_time'], unique=False)
        batch_op.create_index('ix_nonebot_plugin_tetris_stats_iorank_rank', ['rank'], unique=False)
        batch_op.create_index('ix_nonebot_plugin_tetris_stats_iorank_file_hash', ['file_hash'], unique=False)
