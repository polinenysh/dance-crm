from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dance_styles.model import DanceStyle
from app.modules.dance_styles.repository import dance_style_repository
from app.modules.teachers.model import Teacher
from app.modules.teachers.repository import teacher_repository
from app.modules.teachers.schemas import TeacherCreate, TeacherUpdate


class TeacherService:
    """Сервис бизнес-логики преподавателей."""

    async def get_all(
        self,
        session: AsyncSession,
        dance_style_id: int | None = None,
        active_only: bool = False,
        search: str | None = None,
    ) -> list[Teacher]:
        """Возвращает список преподавателей."""
        return await teacher_repository.get_all(session, dance_style_id, active_only, search)

    async def get_by_id(self, session: AsyncSession, teacher_id: int) -> Teacher:
        """Возвращает преподавателя или ошибку 404."""
        teacher = await teacher_repository.get_by_id(session, teacher_id)
        if teacher is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Преподаватель не найден")
        return teacher

    async def get_dance_styles(self, session: AsyncSession, ids: list[int]) -> list[DanceStyle]:
        """Проверяет и возвращает выбранные направления."""
        unique_ids = list(dict.fromkeys(ids))
        styles = await dance_style_repository.get_by_ids(session, unique_ids)
        found = {style.id for style in styles}
        missing = set(unique_ids) - found
        if missing:
            raise HTTPException(status_code=404, detail=f"Не найдены направления: {sorted(missing)}")
        inactive = [style.name for style in styles if not style.is_active]
        if inactive:
            raise HTTPException(status_code=409, detail=f"Нельзя назначить неактивные направления: {inactive}")
        return styles

    async def create(self, session: AsyncSession, data: TeacherCreate) -> Teacher:
        """Создаёт преподавателя как самостоятельную сущность."""
        styles = await self.get_dance_styles(session, data.dance_style_ids)
        teacher = Teacher(
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            email=str(data.email) if data.email is not None else None,
            is_active=True,
            dance_styles=styles,
        )
        session.add(teacher)
        await session.commit()
        created = await teacher_repository.get_by_id(session, teacher.id)
        if created is None:
            raise HTTPException(status_code=500, detail="Не удалось получить созданного преподавателя")
        return created

    async def update(self, session: AsyncSession, teacher_id: int, data: TeacherUpdate) -> Teacher:
        """Обновляет преподавателя."""
        teacher = await self.get_by_id(session, teacher_id)
        update_data = data.model_dump(exclude_unset=True, exclude={"dance_style_ids"})
        if "email" in update_data and update_data["email"] is not None:
            update_data["email"] = str(update_data["email"])
        for field, value in update_data.items():
            setattr(teacher, field, value)
        if data.dance_style_ids is not None:
            teacher.dance_styles = await self.get_dance_styles(session, data.dance_style_ids)
        await session.commit()
        updated = await teacher_repository.get_by_id(session, teacher.id)
        if updated is None:
            raise HTTPException(status_code=500, detail="Не удалось получить обновлённого преподавателя")
        return updated


teacher_service = TeacherService()
