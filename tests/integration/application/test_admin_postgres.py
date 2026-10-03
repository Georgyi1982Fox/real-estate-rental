"""Админка (TASK-110): статистика и очередь жалоб на настоящем PostgreSQL."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.models import Complaint, Listing, User
from bina.infrastructure.db.models.users import SubscriptionTier
from bina.infrastructure.db.repositories.admin import AdminRepository
from bina.infrastructure.db.repositories.complaints import ComplaintsRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.db.repositories.payments import PaymentsRepository
from bina.infrastructure.db.repositories.users import UsersRepository, take_ai_request


def raw(source_id: str, source: str = "ss", district: str = "Ваке") -> RawListing:
    return RawListing(
        source_id=source_id,
        source_name=source,
        title=f"Квартира {source_id}",
        description="",
        price=1000,
        currency="GEL",
        rooms=2,
        area=50,
        district=district,
        url=f"https://example/{source_id}",
    )


async def test_stats_and_complaints(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    users = [await UsersRepository(session).create(700 + i, "ru") for i in range(4)]
    await session.execute(
        update(User)
        .where(User.id == users[0].id)
        .values(
            subscription_tier=SubscriptionTier.NOMAD,
            subscription_expires_at=now + timedelta(days=5),
        )
    )
    await PaymentsRepository(session).add_success(users[0].id, Decimal(250), "XTR", "c1", "m")
    listings = ListingsRepository(session)
    scam = await listings.create_or_update_from_raw(raw("scam"))
    ok = await listings.create_or_update_from_raw(raw("ok", "myhome", "Сабуртало"))
    await listings.create_or_update_from_raw(raw("v2"))
    await session.commit()
    scam_id, ok_id = scam.id, ok.id

    complaints = ComplaintsRepository(session)
    for user, reason in zip(users[1:], ("fraud", "fraud", "prepayment"), strict=True):
        await complaints.add(
            scam_id, user.id, reason, "до просмотра" if reason == "prepayment" else ""
        )
    await complaints.add(ok_id, users[1].id, "wrong_price", "")
    await session.commit()

    admin = AdminRepository(session)
    stats = await admin.stats(now)
    assert (stats.users, stats.users_week, stats.premium) == (4, 4, 1)
    assert (stats.stars_total, stats.stars_month, stats.payments_month) == (
        Decimal(250),
        Decimal(250),
        1,
    )
    assert dict(stats.sources) == {"ss": 1, "myhome": 1}, "скрытое жалобами не в поиске"
    assert (stats.hidden, stats.open_complaints) == (1, 4)
    assert stats.districts[0] == ("Ваке", 1)

    queue = await admin.complaint_queue(5)
    assert [case.listing_id for case in queue] == [scam_id, ok_id]
    first = queue[0]
    assert (first.complaints, first.hidden, first.source) == (3, True, "ss")
    assert sorted(first.reasons) == ["fraud", "fraud", "prepayment"]
    assert first.comments == ["до просмотра"]

    await admin.restore(scam_id, now)
    await admin.hide(ok_id, now)
    await session.commit()
    hidden = dict((await session.execute(select(Listing.id, Listing.hidden_at.is_not(None)))).all())
    assert (hidden[scam_id], hidden[ok_id]) == (False, True)
    open_left = (
        await session.execute(select(Complaint).where(Complaint.resolved_at.is_(None)))
    ).all()
    assert open_left == []
    assert await admin.complaint_queue(5) == []


async def test_daily_report_counts_last_day_and_is_sent_once(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    users = [await UsersRepository(session).create(800 + i, "ru") for i in range(3)]
    await session.execute(
        update(User).where(User.id == users[2].id).values(created_at=now - timedelta(days=3))
    )
    await PaymentsRepository(session).add_success(users[0].id, Decimal(150), "XTR", "d1", "m")
    await take_ai_request(session, users[0].id, now.date(), 10)
    listings = ListingsRepository(session)
    await listings.create_or_update_from_raw(raw("fresh"))
    old = await listings.create_or_update_from_raw(raw("old", "myhome"))
    await session.execute(
        update(Listing).where(Listing.id == old.id).values(created_at=now - timedelta(days=2))
    )
    await session.commit()

    admin = AdminRepository(session)
    report = await admin.daily(now)
    assert (report.users, report.users_new) == (3, 2)
    assert (report.listings, report.listings_new) == (2, 1)
    assert (report.payments, report.stars) == (1, Decimal(150))
    assert report.ai_requests == 1
    assert (report.owner_listings_new, report.agencies, report.chats_new) == (0, 0, 0)

    day = now.date()
    assert await admin.claim_daily_report(day)
    assert not await admin.claim_daily_report(day), "второй раз за день не шлём"
    assert await admin.claim_daily_report(day + timedelta(days=1))
