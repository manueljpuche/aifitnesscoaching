"""API v1 router — aggregates all domain routers."""

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.tracking.router import router as tracking_router
from app.modules.nutrition.router import router as nutrition_router
from app.modules.workouts.router import router as workouts_router
from app.modules.exercises.router import router as exercises_router
from app.modules.wellness.router import router as wellness_router
from app.modules.body.router import router as body_router
from app.modules.pantry.router import router as pantry_router
from app.modules.shopping.router import router as shopping_router
from app.modules.food.router import router as food_router
from app.modules.supplements.router import router as supplements_router
from app.modules.gamification.router import router as gamification_router
from app.modules.checkins.router import router as checkins_router
from app.modules.challenges.router import router as challenges_router
from app.modules.notifications.router import router as notifications_router
from app.modules.versioning.router import router as versioning_router
from app.modules.gdpr.router import router as gdpr_router
from app.modules.ai.router import router as ai_router
from app.modules.admin.router import router as admin_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(tracking_router, prefix="/tracking", tags=["tracking"])
api_router.include_router(nutrition_router, prefix="/nutrition", tags=["nutrition"])
api_router.include_router(workouts_router, prefix="/workouts", tags=["workouts"])
api_router.include_router(exercises_router, prefix="/exercises", tags=["exercises"])
api_router.include_router(wellness_router, prefix="/wellness", tags=["wellness"])
api_router.include_router(body_router, prefix="/body", tags=["body"])
api_router.include_router(pantry_router, prefix="/pantry", tags=["pantry"])
api_router.include_router(shopping_router, prefix="/shopping", tags=["shopping"])
api_router.include_router(food_router, prefix="/food", tags=["food"])
api_router.include_router(supplements_router, prefix="/supplements", tags=["supplements"])
api_router.include_router(gamification_router, prefix="/gamification", tags=["gamification"])
api_router.include_router(checkins_router, prefix="/checkins", tags=["checkins"])
api_router.include_router(challenges_router, prefix="/challenges", tags=["challenges"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
api_router.include_router(versioning_router, prefix="/versioning", tags=["versioning"])
api_router.include_router(gdpr_router, prefix="/gdpr", tags=["gdpr"])
api_router.include_router(ai_router, prefix="/ai", tags=["ai"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
