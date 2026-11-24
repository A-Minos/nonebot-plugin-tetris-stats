"""add TETR.IO league snapshot lookup indexes

迁移 ID: b3f7c2a91d4e
父迁移: a6e4ef2c74bd

"""

from alembic import op

revision: str = 'b3f7c2a91d4e'
down_revision: str = 'a6e4ef2c74bd'
branch_labels: None = None
depends_on: None = None


def upgrade(name: str = '') -> None:
    if name:
        return
    op.create_index(op.f('ix_nb_t_io_tl_hist_stats_id'), 'nb_t_io_tl_hist', ['stats_id'])
    op.create_index(op.f('ix_nb_t_io_tl_hist_id_update_time'), 'nb_t_io_tl_hist', ['id', 'update_time'])
    op.create_index(op.f('ix_nb_t_io_tl_stats_field_stats_id'), 'nb_t_io_tl_stats_field', ['stats_id'])


def downgrade(name: str = '') -> None:
    if name:
        return
    op.drop_index(op.f('ix_nb_t_io_tl_stats_field_stats_id'), table_name='nb_t_io_tl_stats_field')
    op.drop_index(op.f('ix_nb_t_io_tl_hist_id_update_time'), table_name='nb_t_io_tl_hist')
    op.drop_index(op.f('ix_nb_t_io_tl_hist_stats_id'), table_name='nb_t_io_tl_hist')
