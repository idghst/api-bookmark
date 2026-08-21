from fastapi import APIRouter

from app.api.routes.bookmarks import router as bookmarks_router
from app.api.routes.folder_sections import router as folder_sections_router
from app.api.routes.folders import router as folders_router
from app.api.routes.sections import router as sections_router

router = APIRouter(prefix="/api", tags=["bookmarks"])
router.include_router(bookmarks_router)
router.include_router(folders_router)
router.include_router(folder_sections_router)
router.include_router(sections_router)
