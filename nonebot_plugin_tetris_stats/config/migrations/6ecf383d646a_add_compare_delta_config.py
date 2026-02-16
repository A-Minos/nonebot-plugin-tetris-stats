"""add compare delta config

迁移 ID: 6ecf383d646a
父迁移: 2ff388a8c486
创建时间: 2026-01-27 06:05:04.481654

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = '6ecf383d646a'
down_revision: str | Sequence[str] | None = '1c5346b657d4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = '') -> None:
    if name:
        return
    op.create_table(
        'nb_t_top_u_cfg',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('compare_delta', sa.Interval(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_nb_t_top_u_cfg')),
        info={'bind_key': 'nonebot_plugin_tetris_stats'},
    )
    op.create_table(
        'nb_t_tos_u_cfg',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('compare_delta', sa.Interval(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_nb_t_tos_u_cfg')),
        info={'bind_key': 'nonebot_plugin_tetris_stats'},
    )
    with op.batch_alter_table('nb_t_io_u_cfg', schema=None) as batch_op:
        batch_op.add_column(sa.Column('compare_delta', sa.Interval(), nullable=True))


def downgrade(name: str = '') -> None:
    if name:
        return
    with op.batch_alter_table('nb_t_io_u_cfg', schema=None) as batch_op:
        batch_op.drop_column('compare_delta')

    op.drop_table('nb_t_tos_u_cfg')
    op.drop_table('nb_t_top_u_cfg')
