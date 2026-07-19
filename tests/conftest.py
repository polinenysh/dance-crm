from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.modules.auth.security import hash_password
from app.modules.branches.model import Branch
from app.modules.parents.model import Parent
from app.modules.students.model import Student
from app.modules.users.model import User
from app.modules.dance_styles.model import DanceStyle
from app.modules.teachers.model import Teacher
from app.modules.groups.model import Group, GroupMembership
from app.shared.enums import StudentStatus, UserRole
from app.modules.halls.model import Hall
from app.modules.schedule.model import Lesson, ScheduleSlot
from app.modules.subscription_plans.model import SubscriptionPlan
from app.modules.subscriptions.model import StudentSubscription
from app.modules.attendance.model import Attendance
from app.shared.enums import LessonStatus, Weekday

TEST_DATABASE_URL = (
    "postgresql+asyncpg://"
    "postgres:postgres@localhost:5433/dance_crm_test"
)

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
)

test_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_test_database() -> AsyncGenerator[None, None]:
    """Создаёт таблицы перед тестами и удаляет их после завершения."""

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
    """Возвращает сессию тестовой базы данных для FastAPI."""

    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="session", autouse=True)
async def override_dependencies(
    prepare_test_database: None,
) -> AsyncGenerator[None, None]:
    """Подменяет рабочую сессию приложения на тестовую."""

    app.dependency_overrides[get_session] = override_get_session

    yield

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
async def clean_database(
    prepare_test_database: None,
) -> AsyncGenerator[None, None]:
    """Удаляет данные из всех таблиц после каждого теста."""

    yield

    async with test_engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            await connection.execute(table.delete())


@pytest_asyncio.fixture
async def session(
    prepare_test_database: None,
) -> AsyncGenerator[AsyncSession, None]:
    """Возвращает прямую сессию тестовой базы данных."""

    async with test_session_factory() as database_session:
        yield database_session


@pytest_asyncio.fixture
async def client(
    override_dependencies: None,
) -> AsyncGenerator[AsyncClient, None]:
    """Возвращает асинхронный HTTP-клиент для тестирования API."""

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as async_client:
        yield async_client


@pytest_asyncio.fixture
async def branch(
    session: AsyncSession,
) -> Branch:
    """Создаёт активный филиал для тестов."""

    branch = Branch(
        name="Центральный",
        address="ул. Центральная, 10",
        phone="+79991234567",
        is_active=True,
    )

    session.add(branch)
    await session.commit()
    await session.refresh(branch)

    return branch


@pytest_asyncio.fixture
async def second_branch(
    session: AsyncSession,
) -> Branch:
    """Создаёт второй активный филиал для тестов."""

    branch = Branch(
        name="Северный",
        address="ул. Северная, 15",
        phone="+79991234568",
        is_active=True,
    )

    session.add(branch)
    await session.commit()
    await session.refresh(branch)

    return branch


@pytest_asyncio.fixture
async def owner(
    session: AsyncSession,
) -> User:
    """Создаёт руководителя для тестов."""

    user = User(
        email="owner@example.com",
        hashed_password=hash_password("owner-password"),
        first_name="Полина",
        last_name="Хохлова",
        phone="+79991234567",
        role=UserRole.OWNER,
        branch_id=None,
        is_active=True,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


@pytest_asyncio.fixture
async def branch_admin(
    session: AsyncSession,
    branch: Branch,
) -> User:
    """Создаёт администратора первого филиала."""

    user = User(
        email="admin@example.com",
        hashed_password=hash_password("admin-password"),
        first_name="Анна",
        last_name="Администратор",
        phone="+79991234569",
        role=UserRole.BRANCH_ADMIN,
        branch_id=branch.id,
        is_active=True,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


@pytest_asyncio.fixture
async def second_branch_admin(
    session: AsyncSession,
    second_branch: Branch,
) -> User:
    """Создаёт администратора второго филиала."""

    user = User(
        email="second-admin@example.com",
        hashed_password=hash_password("second-admin-password"),
        first_name="Мария",
        last_name="Администратор",
        phone="+79991234570",
        role=UserRole.BRANCH_ADMIN,
        branch_id=second_branch.id,
        is_active=True,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


async def get_authorization_headers(
    client: AsyncClient,
    email: str,
    password: str,
) -> dict[str, str]:
    """Авторизует пользователя и возвращает Bearer-заголовок."""

    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    access_token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {access_token}",
    }


@pytest_asyncio.fixture
async def owner_headers(
    client: AsyncClient,
    owner: User,
) -> dict[str, str]:
    """Возвращает заголовок авторизации руководителя."""

    return await get_authorization_headers(
        client,
        owner.email,
        "owner-password",
    )


@pytest_asyncio.fixture
async def branch_admin_headers(
    client: AsyncClient,
    branch_admin: User,
) -> dict[str, str]:
    """Возвращает заголовок авторизации администратора."""

    return await get_authorization_headers(
        client,
        branch_admin.email,
        "admin-password",
    )


@pytest_asyncio.fixture
async def second_branch_admin_headers(
    client: AsyncClient,
    second_branch_admin: User,
) -> dict[str, str]:
    """Возвращает заголовок авторизации второго администратора."""

    return await get_authorization_headers(
        client,
        second_branch_admin.email,
        "second-admin-password",
    )


@pytest_asyncio.fixture
async def parent(
    session: AsyncSession,
) -> Parent:
    """Создаёт родителя для тестов."""

    parent = Parent(
        first_name="Анна",
        last_name="Иванова",
        phone="+79990000001",
        comment=None,
    )

    session.add(parent)
    await session.commit()
    await session.refresh(parent)

    return parent


@pytest_asyncio.fixture
async def second_parent(
    session: AsyncSession,
) -> Parent:
    """Создаёт второго родителя для тестов."""

    parent = Parent(
        first_name="Елена",
        last_name="Петрова",
        phone="+79990000002",
        comment="Второй родитель",
    )

    session.add(parent)
    await session.commit()
    await session.refresh(parent)

    return parent


@pytest_asyncio.fixture
async def student(
    session: AsyncSession,
    branch: Branch,
    parent: Parent,
    owner: User,
) -> Student:
    """Создаёт активного ученика для тестов."""

    student = Student(
        parent_id=parent.id,
        branch_id=branch.id,
        first_name="Мария",
        last_name="Иванова",
        birth_date=date(2017, 5, 12),
        status=StudentStatus.ACTIVE,
        comment=None,
        created_by=owner.id,
    )

    session.add(student)
    await session.commit()
    await session.refresh(student)

    return student


@pytest.fixture
def branch_payload() -> dict[str, Any]:
    """Возвращает корректные данные филиала."""

    return {
        "name": "Западный",
        "address": "ул. Западная, 20",
        "phone": "+79991112233",
    }


@pytest.fixture
def parent_payload() -> dict[str, Any]:
    """Возвращает корректные данные родителя."""

    return {
        "first_name": "Ольга",
        "last_name": "Смирнова",
        "phone": "+79990000003",
        "comment": None,
    }


@pytest.fixture
def student_payload(
    parent: Parent,
    branch: Branch,
) -> dict[str, Any]:
    """Возвращает корректные данные ученика."""

    return {
        "parent_id": parent.id,
        "branch_id": branch.id,
        "first_name": "Алексей",
        "last_name": "Иванов",
        "birth_date": "2018-08-10",
        "comment": None,
    }

@pytest_asyncio.fixture
async def dance_style(
    session: AsyncSession,
) -> DanceStyle:
    """Создаёт активное танцевальное направление."""

    dance_style = DanceStyle(
        name="Dancehall",
        description="Современное танцевальное направление",
        is_active=True,
    )

    session.add(dance_style)
    await session.commit()
    await session.refresh(dance_style)

    return dance_style


@pytest_asyncio.fixture
async def second_dance_style(
    session: AsyncSession,
) -> DanceStyle:
    """Создаёт второе активное танцевальное направление."""

    dance_style = DanceStyle(
        name="Hip-Hop",
        description="Хип-хоп направление",
        is_active=True,
    )

    session.add(dance_style)
    await session.commit()
    await session.refresh(dance_style)

    return dance_style


@pytest_asyncio.fixture
async def inactive_dance_style(
    session: AsyncSession,
) -> DanceStyle:
    """Создаёт неактивное танцевальное направление."""

    dance_style = DanceStyle(
        name="Contemporary",
        description=None,
        is_active=False,
    )

    session.add(dance_style)
    await session.commit()
    await session.refresh(dance_style)

    return dance_style


@pytest_asyncio.fixture
async def teacher_profile(
    session: AsyncSession,
    dance_style: DanceStyle,
) -> Teacher:
    """Создаёт преподавателя как самостоятельную сущность."""

    teacher_profile = Teacher(
        first_name="Мария",
        last_name="Иванова",
        phone="+79997654321",
        email="teacher@example.com",
        is_active=True,
        dance_styles=[dance_style],
    )

    session.add(teacher_profile)
    await session.commit()
    await session.refresh(teacher_profile)

    return teacher_profile


@pytest.fixture
def dance_style_payload() -> dict[str, Any]:
    """Возвращает данные для создания направления."""

    return {
        "name": "Jazz Funk",
        "description": "Современное танцевальное направление",
    }


@pytest_asyncio.fixture
async def group(
    session: AsyncSession,
    branch: Branch,
    teacher_profile: Teacher,
    dance_style: DanceStyle,
) -> Group:
    """Создаёт активную учебную группу."""

    group = Group(
        branch_id=branch.id,
        dance_style_id=dance_style.id,
        teacher_id=teacher_profile.id,
        name="Dancehall Kids",
        max_students=25,
        is_active=True,
    )

    session.add(group)
    await session.commit()
    await session.refresh(group)

    return group


@pytest_asyncio.fixture
async def second_student(
    session: AsyncSession,
    branch: Branch,
    second_parent: Parent,
    owner: User,
) -> Student:
    """Создаёт второго активного ученика."""

    student = Student(
        parent_id=second_parent.id,
        branch_id=branch.id,
        first_name="Алексей",
        last_name="Петров",
        birth_date=date(2018, 4, 15),
        status=StudentStatus.ACTIVE,
        comment=None,
        created_by=owner.id,
    )

    session.add(student)
    await session.commit()
    await session.refresh(student)

    return student


@pytest_asyncio.fixture
async def other_branch_student(
    session: AsyncSession,
    second_branch: Branch,
    second_parent: Parent,
    owner: User,
) -> Student:
    """Создаёт ученика другого филиала."""

    student = Student(
        parent_id=second_parent.id,
        branch_id=second_branch.id,
        first_name="Иван",
        last_name="Смирнов",
        birth_date=date(2017, 7, 20),
        status=StudentStatus.ACTIVE,
        comment=None,
        created_by=owner.id,
    )

    session.add(student)
    await session.commit()
    await session.refresh(student)

    return student


@pytest_asyncio.fixture
async def inactive_student(
    session: AsyncSession,
    branch: Branch,
    second_parent: Parent,
    owner: User,
) -> Student:
    """Создаёт неактивного ученика."""

    student = Student(
        parent_id=second_parent.id,
        branch_id=branch.id,
        first_name="Неактивный",
        last_name="Ученик",
        birth_date=None,
        status=StudentStatus.INACTIVE,
        comment=None,
        created_by=owner.id,
    )

    session.add(student)
    await session.commit()
    await session.refresh(student)

    return student


@pytest_asyncio.fixture
async def group_membership(
    session: AsyncSession,
    group: Group,
    student: Student,
) -> GroupMembership:
    """Добавляет ученика в группу."""

    membership = GroupMembership(
        group_id=group.id,
        student_id=student.id,
        is_active=True,
        left_at=None,
    )

    session.add(membership)
    await session.commit()
    await session.refresh(membership)

    return membership


@pytest.fixture
def group_payload(
    branch: Branch,
    teacher_profile: Teacher,
    dance_style: DanceStyle,
) -> dict[str, Any]:
    """Возвращает корректные данные учебной группы."""

    return {
        "branch_id": branch.id,
        "dance_style_id": dance_style.id,
        "teacher_id": teacher_profile.id,
        "name": "Hip-Hop Kids",
        "max_students": 20,
    }

@pytest_asyncio.fixture
async def hall(
    session: AsyncSession,
    branch: Branch,
) -> Hall:
    """Создаёт активный зал первого филиала."""

    hall = Hall(
        branch_id=branch.id,
        name="Большой зал",
        capacity=30,
        is_active=True,
    )

    session.add(hall)
    await session.commit()
    await session.refresh(hall)

    return hall


@pytest_asyncio.fixture
async def second_hall(
    session: AsyncSession,
    branch: Branch,
) -> Hall:
    """Создаёт второй активный зал первого филиала."""

    hall = Hall(
        branch_id=branch.id,
        name="Малый зал",
        capacity=25,
        is_active=True,
    )

    session.add(hall)
    await session.commit()
    await session.refresh(hall)

    return hall


@pytest_asyncio.fixture
async def other_branch_hall(
    session: AsyncSession,
    second_branch: Branch,
) -> Hall:
    """Создаёт активный зал второго филиала."""

    hall = Hall(
        branch_id=second_branch.id,
        name="Зал второго филиала",
        capacity=30,
        is_active=True,
    )

    session.add(hall)
    await session.commit()
    await session.refresh(hall)

    return hall


@pytest_asyncio.fixture
async def inactive_hall(
    session: AsyncSession,
    branch: Branch,
) -> Hall:
    """Создаёт неактивный зал."""

    hall = Hall(
        branch_id=branch.id,
        name="Неактивный зал",
        capacity=30,
        is_active=False,
    )

    session.add(hall)
    await session.commit()
    await session.refresh(hall)

    return hall


@pytest_asyncio.fixture
async def schedule_slot(
    session: AsyncSession,
    group: Group,
    hall: Hall,
) -> ScheduleSlot:
    """Создаёт активный шаблон расписания по понедельникам."""

    slot = ScheduleSlot(
        group_id=group.id,
        hall_id=hall.id,
        weekday=Weekday.MONDAY,
        start_time=time(18, 0),
        end_time=time(19, 0),
        is_active=True,
    )

    session.add(slot)
    await session.commit()
    await session.refresh(slot)

    return slot


@pytest_asyncio.fixture
async def lesson(
    session: AsyncSession,
    schedule_slot: ScheduleSlot,
    group: Group,
    hall: Hall,
    teacher_profile: Teacher,
) -> Lesson:
    """Создаёт запланированное конкретное занятие."""

    lesson = Lesson(
        schedule_slot_id=schedule_slot.id,
        group_id=group.id,
        hall_id=hall.id,
        teacher_id=teacher_profile.id,
        starts_at=datetime(
            2026,
            7,
            20,
            18,
            0,
            tzinfo=UTC,
        ),
        ends_at=datetime(
            2026,
            7,
            20,
            19,
            0,
            tzinfo=UTC,
        ),
        status=LessonStatus.PLANNED,
        cancellation_reason=None,
        cancelled_by_studio=False,
        cancelled_by=None,
    )

    session.add(lesson)
    await session.commit()
    await session.refresh(lesson)

    return lesson


@pytest.fixture
def schedule_slot_payload(
    group: Group,
    hall: Hall,
) -> dict[str, Any]:
    """Возвращает корректные данные шаблона расписания."""

    return {
        "group_id": group.id,
        "hall_id": hall.id,
        "weekday": Weekday.TUESDAY,
        "start_time": "18:00:00",
        "end_time": "19:00:00",
    }

@pytest_asyncio.fixture
async def subscription_plan(
    session: AsyncSession,
    branch: Branch,
) -> SubscriptionPlan:
    """Создаёт активный тип абонемента первого филиала."""

    plan = SubscriptionPlan(
        branch_id=branch.id,
        name="8 занятий",
        lessons_count=8,
        price=7000,
        is_active=True,
    )

    session.add(plan)
    await session.commit()
    await session.refresh(plan)

    return plan


@pytest_asyncio.fixture
async def second_subscription_plan(
    session: AsyncSession,
    branch: Branch,
) -> SubscriptionPlan:
    """Создаёт второй активный тип абонемента первого филиала."""

    plan = SubscriptionPlan(
        branch_id=branch.id,
        name="12 занятий",
        lessons_count=12,
        price=9000,
        is_active=True,
    )

    session.add(plan)
    await session.commit()
    await session.refresh(plan)

    return plan


@pytest_asyncio.fixture
async def inactive_subscription_plan(
    session: AsyncSession,
    branch: Branch,
) -> SubscriptionPlan:
    """Создаёт неактивный тип абонемента."""

    plan = SubscriptionPlan(
        branch_id=branch.id,
        name="4 занятия",
        lessons_count=4,
        price=4000,
        is_active=False,
    )

    session.add(plan)
    await session.commit()
    await session.refresh(plan)

    return plan


@pytest_asyncio.fixture
async def other_branch_subscription_plan(
    session: AsyncSession,
    second_branch: Branch,
) -> SubscriptionPlan:
    """Создаёт тип абонемента второго филиала."""

    plan = SubscriptionPlan(
        branch_id=second_branch.id,
        name="8 занятий",
        lessons_count=8,
        price=7500,
        is_active=True,
    )

    session.add(plan)
    await session.commit()
    await session.refresh(plan)

    return plan


@pytest.fixture
def subscription_plan_payload(
    branch: Branch,
) -> dict[str, Any]:
    """Возвращает корректные данные типа абонемента."""

    return {
        "branch_id": branch.id,
        "name": "16 занятий",
        "lessons_count": 16,
        "price": 11000,
    }

@pytest_asyncio.fixture
async def student_subscription(
    session: AsyncSession,
    student: Student,
    subscription_plan: SubscriptionPlan,
    branch: Branch,
    owner: User,
) -> StudentSubscription:
    """Создаёт действующий абонемент ученика."""

    starts_on = date.today() - timedelta(days=5)

    subscription = StudentSubscription(
        student_id=student.id,
        plan_id=subscription_plan.id,
        branch_id=branch.id,
        starts_on=starts_on,
        expires_on=starts_on + timedelta(days=29),
        lessons_count=subscription_plan.lessons_count,
        price=subscription_plan.price,
        extension_days=0,
        comment="Тестовый абонемент",
        created_by=owner.id,
    )

    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)

    return subscription


@pytest_asyncio.fixture
async def upcoming_student_subscription(
    session: AsyncSession,
    second_student: Student,
    subscription_plan: SubscriptionPlan,
    branch: Branch,
    owner: User,
) -> StudentSubscription:
    """Создаёт будущий абонемент ученика."""

    starts_on = date.today() + timedelta(days=10)

    subscription = StudentSubscription(
        student_id=second_student.id,
        plan_id=subscription_plan.id,
        branch_id=branch.id,
        starts_on=starts_on,
        expires_on=starts_on + timedelta(days=29),
        lessons_count=subscription_plan.lessons_count,
        price=subscription_plan.price,
        extension_days=0,
        comment=None,
        created_by=owner.id,
    )

    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)

    return subscription


@pytest_asyncio.fixture
async def expired_student_subscription(
    session: AsyncSession,
    second_student: Student,
    subscription_plan: SubscriptionPlan,
    branch: Branch,
    owner: User,
) -> StudentSubscription:
    """Создаёт завершившийся абонемент ученика."""

    starts_on = date.today() - timedelta(days=60)

    subscription = StudentSubscription(
        student_id=second_student.id,
        plan_id=subscription_plan.id,
        branch_id=branch.id,
        starts_on=starts_on,
        expires_on=starts_on + timedelta(days=29),
        lessons_count=subscription_plan.lessons_count,
        price=subscription_plan.price,
        extension_days=0,
        comment=None,
        created_by=owner.id,
    )

    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)

    return subscription


@pytest.fixture
def student_subscription_payload(
    student: Student,
    subscription_plan: SubscriptionPlan,
) -> dict[str, Any]:
    """Возвращает корректные данные абонемента ученика."""

    return {
        "student_id": student.id,
        "plan_id": subscription_plan.id,
        "starts_on": date.today().isoformat(),
        "comment": "Оплата наличными",
    }


@pytest_asyncio.fixture
async def attendance(
    session: AsyncSession,
    lesson: Lesson,
    student: Student,
    student_subscription: StudentSubscription,
    owner: User,
    group_membership: GroupMembership,
) -> Attendance:
    """Создаёт отметку посещения ученика."""

    attendance = Attendance(
        lesson_id=lesson.id,
        student_id=student.id,
        subscription_id=student_subscription.id,
        marked_by=owner.id,
    )

    session.add(attendance)
    await session.commit()
    await session.refresh(attendance)

    return attendance


@pytest_asyncio.fixture
async def second_group_membership(
    session: AsyncSession,
    group: Group,
    second_student: Student,
) -> GroupMembership:
    """Добавляет второго ученика в группу."""

    membership = GroupMembership(
        group_id=group.id,
        student_id=second_student.id,
        is_active=True,
        left_at=None,
    )

    session.add(membership)
    await session.commit()
    await session.refresh(membership)

    return membership


@pytest_asyncio.fixture
async def second_student_subscription(
    session: AsyncSession,
    second_student: Student,
    subscription_plan: SubscriptionPlan,
    branch: Branch,
    owner: User,
    lesson: Lesson,
) -> StudentSubscription:
    """Создаёт действующий абонемент второго ученика."""

    lesson_date = lesson.starts_at.date()
    starts_on = lesson_date - timedelta(days=5)

    subscription = StudentSubscription(
        student_id=second_student.id,
        plan_id=subscription_plan.id,
        branch_id=branch.id,
        starts_on=starts_on,
        expires_on=starts_on + timedelta(days=29),
        lessons_count=subscription_plan.lessons_count,
        price=subscription_plan.price,
        extension_days=0,
        comment=None,
        created_by=owner.id,
    )

    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)

    return subscription

@pytest_asyncio.fixture
async def following_student_subscription(
    session: AsyncSession,
    student_subscription: StudentSubscription,
    owner: User,
) -> StudentSubscription:
    """Создаёт следующий абонемент ученика."""

    subscription = StudentSubscription(
        student_id=student_subscription.student_id,
        plan_id=student_subscription.plan_id,
        branch_id=student_subscription.branch_id,
        starts_on=student_subscription.expires_on + timedelta(days=1),
        expires_on=student_subscription.expires_on + timedelta(days=30),
        lessons_count=student_subscription.lessons_count,
        price=student_subscription.price,
        extension_days=0,
        comment=None,
        created_by=owner.id,
    )

    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)

    return subscription