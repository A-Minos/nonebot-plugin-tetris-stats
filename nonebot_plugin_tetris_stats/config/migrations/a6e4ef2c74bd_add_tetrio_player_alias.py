"""add TETR.IO player aliases"""

import sqlalchemy as sa
from alembic import op

revision: str = 'a6e4ef2c74bd'
down_revision: str = '74640f698d8b'
branch_labels: None = None
depends_on: None = None


def upgrade(name: str = '') -> None:
    if name:
        return
    op.create_table(
        'nb_t_io_player_alias',
        sa.Column('alias', sa.String(length=16), nullable=False),
        sa.Column('uid_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['uid_id'], ['nb_t_io_uid.id'], name=op.f('fk_nb_t_io_player_alias_uid_id_nb_t_io_uid')
        ),
        sa.PrimaryKeyConstraint('alias', name=op.f('pk_nb_t_io_player_alias')),
        info={'bind_key': 'nonebot_plugin_tetris_stats'},
    )
    op.create_index(op.f('ix_nb_t_io_player_alias_uid_id'), 'nb_t_io_player_alias', ['uid_id'])


def downgrade(name: str = '') -> None:
    if name:
        return
    op.drop_table('nb_t_io_player_alias')
