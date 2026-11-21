from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects import postgresql, sqlite

from .models import TETRIOPlayerAlias, TETRIOUserUniqueIdentifier

if TYPE_CHECKING:
    from collections.abc import Set as AbstractSet

    from sqlalchemy.ext.asyncio import AsyncSession

_UID_BATCH_SIZE = 500


def player_insert(
    session: 'AsyncSession', model: type[TETRIOPlayerAlias | TETRIOUserUniqueIdentifier]
) -> sqlite.Insert | postgresql.Insert:
    match session.get_bind(mapper=model).dialect.name:
        case 'sqlite':
            return sqlite.insert(model)
        case 'postgresql':
            return postgresql.insert(model)
        case dialect:
            msg = f'TETR.IO UID writes do not support the {dialect} dialect'
            raise NotImplementedError(msg)


async def ensure_uid_ids(session: 'AsyncSession', uids: 'AbstractSet[str]') -> dict[str, int]:
    """Return stable numeric IDs for TETR.IO UIDs in the caller's transaction."""
    model = TETRIOUserUniqueIdentifier
    result: dict[str, int] = {}
    ordered = sorted(uids)
    for offset in range(0, len(ordered), _UID_BATCH_SIZE):
        query = select(model.user_unique_identifier, model.id)
        chunk = ordered[offset : offset + _UID_BATCH_SIZE]
        rows = await session.execute(query.where(model.user_unique_identifier.in_(chunk)))
        result.update((uid, uid_id) for uid, uid_id in rows)
        missing = [uid for uid in chunk if uid not in result]
        if not missing:
            continue
        await session.execute(
            player_insert(session, model)
            .values([{'user_unique_identifier': uid} for uid in missing])
            .on_conflict_do_nothing(index_elements=[model.user_unique_identifier])
        )
        rows = await session.execute(query.where(model.user_unique_identifier.in_(missing)))
        result.update((uid, uid_id) for uid, uid_id in rows)
    return result
