from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Integer, create_engine, text
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

UTC = timezone.utc


@pytest.fixture
def session_with_model() -> Generator[tuple[Session, type]]:
    from nonebot_plugin_tetris_stats.db.types import UTCDateTime  # noqa: PLC0415

    class Base(DeclarativeBase):
        pass

    class UTCDateTimeRow(Base):
        __tablename__ = 'utc_datetime_row'

        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        happened_at: Mapped[datetime] = mapped_column(UTCDateTime())

    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session, UTCDateTimeRow
    engine.dispose()


def test_utc_datetime_round_trips_aware_utc(session_with_model: tuple[Session, type]) -> None:
    session, utc_datetime_row = session_with_model
    expected = datetime(2026, 3, 8, 15, 30, 42, 248129, tzinfo=UTC)

    session.add(utc_datetime_row(id=1, happened_at=expected))
    session.commit()
    session.expire_all()

    row = session.get(utc_datetime_row, 1)

    assert row is not None  # noqa: S101
    assert row.happened_at == expected  # noqa: S101
    assert row.happened_at.tzinfo is UTC  # noqa: S101


def test_utc_datetime_rejects_naive_bind(session_with_model: tuple[Session, type]) -> None:
    session, utc_datetime_row = session_with_model
    session.add(
        utc_datetime_row(id=1, happened_at=datetime(2026, 3, 8, 15, 30, 42, 248129, tzinfo=UTC).replace(tzinfo=None))
    )

    with pytest.raises(StatementError, match='aware UTC'):
        session.commit()


def test_utc_datetime_rejects_non_utc_bind(session_with_model: tuple[Session, type]) -> None:
    session, utc_datetime_row = session_with_model
    session.add(
        utc_datetime_row(
            id=1,
            happened_at=datetime(2026, 3, 8, 23, 30, 42, 248129, tzinfo=timezone(timedelta(hours=8))),
        )
    )

    with pytest.raises(StatementError, match='aware UTC'):
        session.commit()


def test_utc_datetime_reads_db_naive_as_aware_utc(session_with_model: tuple[Session, type]) -> None:
    session, utc_datetime_row = session_with_model
    expected = datetime(2026, 3, 8, 15, 30, 42, 248129, tzinfo=UTC)

    session.execute(
        text('INSERT INTO utc_datetime_row (id, happened_at) VALUES (:id, :happened_at)'),
        {'id': 1, 'happened_at': expected.replace(tzinfo=None)},
    )
    session.commit()
    session.expire_all()

    row = session.get(utc_datetime_row, 1)

    assert row is not None  # noqa: S101
    assert row.happened_at == expected  # noqa: S101
    assert row.happened_at.tzinfo is UTC  # noqa: S101
