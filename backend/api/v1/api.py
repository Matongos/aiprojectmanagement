from fastapi import APIRouter

from api.v1.endpoints import users, roles, tasks

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"]) 