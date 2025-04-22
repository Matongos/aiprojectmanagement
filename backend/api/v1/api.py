from fastapi import APIRouter

from api.v1.endpoints import users, roles

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"]) 