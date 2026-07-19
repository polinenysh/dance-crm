from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.branches.router import router as branches_router
from app.modules.dance_styles.router import router as dance_styles_router
from app.modules.halls.router import router as halls_router
from app.modules.parents.router import router as parents_router
from app.modules.students.router import router as students_router
from app.modules.teachers.router import router as teachers_router
from app.modules.users.router import router as users_router
from app.modules.groups.router import router as groups_router
from app.modules.schedule.router import router as schedule_router
from app.modules.subscription_plans.router import (
    router as subscription_plans_router,
)
from app.modules.subscriptions.router import (
    router as subscriptions_router,
)
from app.modules.attendance.router import router as attendance_router
from app.modules.payments.router import router as payments_router
from app.modules.reports.router import router as reports_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(branches_router)
api_router.include_router(halls_router)
api_router.include_router(users_router)
api_router.include_router(parents_router)
api_router.include_router(students_router)
api_router.include_router(dance_styles_router)
api_router.include_router(teachers_router)
api_router.include_router(groups_router)
api_router.include_router(schedule_router)
api_router.include_router(subscription_plans_router)
api_router.include_router(subscriptions_router)
api_router.include_router(attendance_router)
api_router.include_router(payments_router)
api_router.include_router(reports_router)