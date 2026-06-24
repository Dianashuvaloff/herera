from handlers.user import router as user_router
from handlers.admin import router as admin_router
from handlers.matches import router as matches_router
from handlers.points import router as points_router

all_routers = [admin_router, points_router, matches_router, user_router]
