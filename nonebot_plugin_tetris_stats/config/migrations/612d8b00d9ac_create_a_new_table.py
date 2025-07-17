"""Create a new table

迁移 ID: 612d8b00d9ac
父迁移: 5a1b93948494
创建时间: 2025-05-26 04:49:29.664480

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = '612d8b00d9ac'
down_revision: str | Sequence[str] | None = '5a1b93948494'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = '') -> None:
    if name:
        return
    if op.get_bind().dialect.name == 'postgresql':
        return
    op.create_table(
        'nonebot_plugin_tetris_stats_triggerhistoricaldatav2',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trigger_time', sa.DateTime(), nullable=False),
        sa.Column('session_persist_id', sa.Integer(), nullable=False),
        sa.Column('game_platform', sa.String(length=32), nullable=False),
        sa.Column('command_type', sa.String(length=16), nullable=False),
        sa.Column('command_args', sa.JSON(), nullable=False),
        sa.Column('finish_time', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_nonebot_plugin_tetris_stats_triggerhistoricaldatav2')),
        info={'bind_key': 'nonebot_plugin_tetris_stats'},
    )
    with op.batch_alter_table('nonebot_plugin_tetris_stats_triggerhistoricaldatav2', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_nonebot_plugin_tetris_stats_triggerhistoricaldatav2_command_type'),
            ['command_type'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_nonebot_plugin_tetris_stats_triggerhistoricaldatav2_game_platform'),
            ['game_platform'],
            unique=False,
        )


def downgrade(name: str = '') -> None:
    if name:
        return
    if op.get_bind().dialect.name == 'postgresql':
        return
    with op.batch_alter_table('nonebot_plugin_tetris_stats_triggerhistoricaldatav2', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_nonebot_plugin_tetris_stats_triggerhistoricaldatav2_game_platform'))
        batch_op.drop_index(batch_op.f('ix_nonebot_plugin_tetris_stats_triggerhistoricaldatav2_command_type'))

    op.drop_table('nonebot_plugin_tetris_stats_triggerhistoricaldatav2')
