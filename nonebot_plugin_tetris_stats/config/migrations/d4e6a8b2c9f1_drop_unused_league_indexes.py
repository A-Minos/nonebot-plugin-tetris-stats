"""drop unused TETR.IO league indexes

迁移 ID: d4e6a8b2c9f1
父迁移: b3f7c2a91d4e

"""

from alembic import op

revision: str = 'd4e6a8b2c9f1'
down_revision: str = 'b3f7c2a91d4e'
branch_labels: None = None
depends_on: None = None


def upgrade(name: str = '') -> None:
    if name:
        return
    # uid_id 已有 uq_nb_t_io_tl_map_uid_hist 覆盖, stats_id 只写不查
    op.drop_index(op.f('ix_nb_t_io_tl_map_uid_id'), table_name='nb_t_io_tl_map')
    op.drop_index(op.f('ix_nb_t_io_tl_map_stats_id'), table_name='nb_t_io_tl_map')
    op.drop_index(op.f('ix_nb_t_io_tl_hist_request_id'), table_name='nb_t_io_tl_hist')
    op.drop_index(op.f('ix_nb_t_io_tl_stats_field_rank'), table_name='nb_t_io_tl_stats_field')


def downgrade(name: str = '') -> None:
    if name:
        return
    op.create_index(op.f('ix_nb_t_io_tl_stats_field_rank'), 'nb_t_io_tl_stats_field', ['rank'])
    op.create_index(op.f('ix_nb_t_io_tl_hist_request_id'), 'nb_t_io_tl_hist', ['request_id'])
    op.create_index(op.f('ix_nb_t_io_tl_map_stats_id'), 'nb_t_io_tl_map', ['stats_id'])
    op.create_index(op.f('ix_nb_t_io_tl_map_uid_id'), 'nb_t_io_tl_map', ['uid_id'])
