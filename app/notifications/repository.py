from typing import Sequence

from sqlalchemy import insert, literal, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.bookclubs.models import ClubMember
from app.notifications.models import Notification

# После этого числа неудачных попыток строка выпадает из выборки воркера:
# канал стабильно отвечает ошибкой (например, пользователь заблокировал бота),
# долбить его дальше бессмысленно.
MAX_ATTEMPTS = 5


class NotificationRepository:
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(self, user_id: int, type: str, text: str) -> None:
        self.db.add(Notification(user_id=user_id, type=type, text=text))
        await self.db.flush()

    async def add_for_club_members(
        self, club_id: int, exclude_user_id: int, type: str, text: str
    ) -> None:
        """Уведомление каждому участнику клуба, кроме инициатора - одним INSERT..SELECT."""
        await self.db.execute(
            insert(Notification).from_select(
                ["user_id", "type", "text"],
                select(ClubMember.user_id, literal(type), literal(text)).where(
                    ClubMember.club_id == club_id, ClubMember.user_id != exclude_user_id
                ),
            )
        )

    async def pick_pending(self, limit: int = 500) -> Sequence[Notification]:
        """Пачка недоставленных уведомлений под доставку.

        FOR UPDATE SKIP LOCKED: два одновременных прогона воркера не отправят
        одну строку дважды.
        """
        result = await self.db.execute(
            select(Notification)
            .where(Notification.processed_at.is_(None), Notification.attempts < MAX_ATTEMPTS)
            .order_by(Notification.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        return result.scalars().all()

    async def create_deadline_reminders(self) -> None:
        """Напоминания участникам клубов о завтрашних дедлайнах этапа и захода.

        Сырой SQL: INSERT..SELECT по трём таблицам с конкатенацией текста в Core
        читается хуже, чем сам SQL. dedup_key делает прогон идемпотентным, дата
        в ключе - при переносе дедлайна напоминание придёт снова.
        """
        await self.db.execute(text("""
            INSERT INTO notifications (user_id, type, text, dedup_key)
            SELECT cm.user_id, 'stage_deadline',
                   'Завтра дедлайн этапа "' || rs.title || '" в клубе "' || bc.name || '"',
                   'stage_deadline:' || rs.id || ':' || rs.due_date || ':' || cm.user_id
            FROM reading_stages rs
            JOIN readings r ON r.id = rs.reading_id AND r.finished_at IS NULL
            JOIN book_clubs bc ON bc.id = r.club_id
            JOIN club_members cm ON cm.club_id = r.club_id
            WHERE rs.due_date = CURRENT_DATE + 1
            ON CONFLICT (dedup_key) DO NOTHING
        """))
        await self.db.execute(text("""
            INSERT INTO notifications (user_id, type, text, dedup_key)
            SELECT cm.user_id, 'reading_deadline',
                   'Завтра дедлайн захода в клубе "' || bc.name || '"',
                   'reading_deadline:' || r.id || ':' || r.deadline || ':' || cm.user_id
            FROM readings r
            JOIN book_clubs bc ON bc.id = r.club_id
            JOIN club_members cm ON cm.club_id = r.club_id
            WHERE r.deadline = CURRENT_DATE + 1 AND r.finished_at IS NULL
            ON CONFLICT (dedup_key) DO NOTHING
        """))
