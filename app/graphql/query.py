import strawberry
from strawberry.types import Info

from app.graphql.context import GraphQLContext
from app.graphql.errors import resolve
from app.graphql.types import Bookmark, Folder, Section
from app.services import bookmarks


@strawberry.type
class Query:
    @strawberry.field
    def status(self) -> str:
        return "ok"

    @strawberry.field
    async def bookmarks(self, info: Info[GraphQLContext, None]) -> list[Bookmark]:
        rows = await resolve(bookmarks.list_bookmarks(info.context.auth))
        return [Bookmark.from_model(row) for row in rows]

    @strawberry.field
    async def folders(self, info: Info[GraphQLContext, None]) -> list[Folder]:
        rows = await resolve(bookmarks.list_folders(info.context.auth))
        return [Folder.from_model(row) for row in rows]

    @strawberry.field
    async def sections(self, info: Info[GraphQLContext, None]) -> list[Section]:
        rows = await resolve(bookmarks.list_sections(info.context.auth))
        return [Section.from_model(row) for row in rows]
