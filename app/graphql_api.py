from collections.abc import Awaitable
from typing import Annotated

import strawberry
from fastapi import Depends
from graphql import GraphQLError
from strawberry.fastapi import BaseContext, GraphQLRouter
from strawberry.types import Info
from strawberry.types.unset import UnsetType

from app.core.errors import ApiError
from app.integrations.supabase import AuthContext, get_resource_auth_context
from app.schemas import (
    BookmarkCreate,
    BookmarkOut,
    BookmarkUpdate,
    FolderCreate,
    FolderOut,
    FolderUpdate,
    PositionUpdate,
    SectionCreate,
    SectionOut,
    SectionUpdate,
)
from app.services import bookmarks


class GraphQLContext(BaseContext):
    def __init__(self, auth: AuthContext) -> None:
        super().__init__()
        self.auth = auth


async def get_graphql_context(
    auth: Annotated[AuthContext, Depends(get_resource_auth_context)],
) -> GraphQLContext:
    return GraphQLContext(auth=auth)


@strawberry.type(name="Bookmark")
class Bookmark:
    id: strawberry.ID
    title: str
    url: str
    description: str | None
    is_favorite: bool
    folder_id: strawberry.ID | None
    section_id: strawberry.ID | None
    position: int

    @classmethod
    def from_model(cls, model: BookmarkOut) -> "Bookmark":
        return cls(
            id=strawberry.ID(model.id),
            title=model.title,
            url=model.url,
            description=model.description,
            is_favorite=model.is_favorite,
            folder_id=(
                strawberry.ID(model.folder_id) if model.folder_id is not None else None
            ),
            section_id=(
                strawberry.ID(model.section_id)
                if model.section_id is not None
                else None
            ),
            position=model.position,
        )


@strawberry.type(name="Folder")
class Folder:
    id: strawberry.ID
    name: str
    color: str | None
    position: int

    @classmethod
    def from_model(cls, model: FolderOut) -> "Folder":
        return cls(
            id=strawberry.ID(model.id),
            name=model.name,
            color=model.color,
            position=model.position,
        )


@strawberry.type(name="Section")
class Section:
    id: strawberry.ID
    name: str
    folder_id: strawberry.ID
    position: int

    @classmethod
    def from_model(cls, model: SectionOut) -> "Section":
        return cls(
            id=strawberry.ID(model.id),
            name=model.name,
            folder_id=strawberry.ID(model.folder_id),
            position=model.position,
        )


@strawberry.input
class BookmarkCreateInput:
    title: str
    url: str
    description: str | None = None
    is_favorite: bool = False
    folder_id: strawberry.ID | None = None
    section_id: strawberry.ID | None = None


@strawberry.input
class BookmarkUpdateInput:
    title: str | None = strawberry.UNSET
    url: str | None = strawberry.UNSET
    description: str | None = strawberry.UNSET
    is_favorite: bool | None = strawberry.UNSET
    folder_id: strawberry.ID | None = strawberry.UNSET
    section_id: strawberry.ID | None = strawberry.UNSET


@strawberry.input
class FolderCreateInput:
    name: str
    color: str | None = None


@strawberry.input
class FolderUpdateInput:
    name: str | None = strawberry.UNSET
    color: str | None = strawberry.UNSET


@strawberry.input
class SectionCreateInput:
    folder_id: strawberry.ID
    name: str


@strawberry.input
class SectionUpdateInput:
    name: str | None = strawberry.UNSET


@strawberry.input
class PositionInput:
    id: strawberry.ID
    position: int


@strawberry.type
class Query:
    @strawberry.field
    def status(self) -> str:
        return "ok"

    @strawberry.field
    async def bookmarks(self, info: Info[GraphQLContext, None]) -> list[Bookmark]:
        rows = await _resolve(bookmarks.list_bookmarks(info.context.auth))
        return [Bookmark.from_model(row) for row in rows]

    @strawberry.field
    async def folders(self, info: Info[GraphQLContext, None]) -> list[Folder]:
        rows = await _resolve(bookmarks.list_folders(info.context.auth))
        return [Folder.from_model(row) for row in rows]

    @strawberry.field
    async def sections(self, info: Info[GraphQLContext, None]) -> list[Section]:
        rows = await _resolve(bookmarks.list_sections(info.context.auth))
        return [Section.from_model(row) for row in rows]


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_bookmark(
        self,
        info: Info[GraphQLContext, None],
        input: BookmarkCreateInput,
    ) -> Bookmark:
        row = await _resolve(
            bookmarks.create_bookmark(
                BookmarkCreate(
                    title=input.title,
                    url=input.url,
                    description=input.description,
                    isFavorite=input.is_favorite,
                    folderId=input.folder_id,
                    sectionId=input.section_id,
                ),
                info.context.auth,
            )
        )
        return Bookmark.from_model(row)

    @strawberry.mutation
    async def update_bookmark(
        self,
        info: Info[GraphQLContext, None],
        id: strawberry.ID,
        input: BookmarkUpdateInput,
    ) -> Bookmark:
        row = await _resolve(
            bookmarks.update_bookmark(
                id,
                BookmarkUpdate.model_validate(_update_values(input)),
                info.context.auth,
            )
        )
        return Bookmark.from_model(row)

    @strawberry.mutation
    async def delete_bookmark(
        self,
        info: Info[GraphQLContext, None],
        id: strawberry.ID,
    ) -> bool:
        await _resolve(bookmarks.delete_bookmark(id, info.context.auth))
        return True

    @strawberry.mutation
    async def reorder_bookmarks(
        self,
        info: Info[GraphQLContext, None],
        input: list[PositionInput],
    ) -> bool:
        await _resolve(
            bookmarks.reorder_bookmarks(_positions(input), info.context.auth)
        )
        return True

    @strawberry.mutation
    async def create_folder(
        self,
        info: Info[GraphQLContext, None],
        input: FolderCreateInput,
    ) -> Folder:
        row = await _resolve(
            bookmarks.create_folder(
                FolderCreate(name=input.name, color=input.color),
                info.context.auth,
            )
        )
        return Folder.from_model(row)

    @strawberry.mutation
    async def update_folder(
        self,
        info: Info[GraphQLContext, None],
        id: strawberry.ID,
        input: FolderUpdateInput,
    ) -> Folder:
        row = await _resolve(
            bookmarks.update_folder(
                id,
                FolderUpdate.model_validate(_update_values(input)),
                info.context.auth,
            )
        )
        return Folder.from_model(row)

    @strawberry.mutation
    async def delete_folder(
        self,
        info: Info[GraphQLContext, None],
        id: strawberry.ID,
    ) -> bool:
        await _resolve(bookmarks.delete_folder(id, info.context.auth))
        return True

    @strawberry.mutation
    async def reorder_folders(
        self,
        info: Info[GraphQLContext, None],
        input: list[PositionInput],
    ) -> bool:
        await _resolve(bookmarks.reorder_folders(_positions(input), info.context.auth))
        return True

    @strawberry.mutation
    async def create_section(
        self,
        info: Info[GraphQLContext, None],
        input: SectionCreateInput,
    ) -> Section:
        row = await _resolve(
            bookmarks.create_section(
                SectionCreate(folderId=input.folder_id, name=input.name),
                info.context.auth,
            )
        )
        return Section.from_model(row)

    @strawberry.mutation
    async def update_section(
        self,
        info: Info[GraphQLContext, None],
        id: strawberry.ID,
        input: SectionUpdateInput,
    ) -> Section:
        row = await _resolve(
            bookmarks.update_section(
                id,
                SectionUpdate.model_validate(_update_values(input)),
                info.context.auth,
            )
        )
        return Section.from_model(row)

    @strawberry.mutation
    async def delete_section(
        self,
        info: Info[GraphQLContext, None],
        id: strawberry.ID,
    ) -> bool:
        await _resolve(bookmarks.delete_section(id, info.context.auth))
        return True

    @strawberry.mutation
    async def reorder_sections(
        self,
        info: Info[GraphQLContext, None],
        input: list[PositionInput],
    ) -> bool:
        await _resolve(bookmarks.reorder_sections(_positions(input), info.context.auth))
        return True


def _update_values(input: object) -> dict[str, object]:
    values: dict[str, object] = {}
    for field in vars(input):
        value = getattr(input, field)
        if not isinstance(value, UnsetType):
            values[field] = value
    if not values:
        raise GraphQLError(
            "Input must not be empty",
            extensions={"code": "BAD_USER_INPUT"},
        )
    return values


def _positions(input: list[PositionInput]) -> list[PositionUpdate]:
    ids: set[str] = set()
    positions: list[PositionUpdate] = []
    for item in input:
        if not item.id.strip() or item.id in ids or item.position < 0:
            raise GraphQLError(
                "Invalid position input",
                extensions={"code": "BAD_USER_INPUT"},
            )
        ids.add(item.id)
        positions.append(PositionUpdate(id=item.id, position=item.position))
    return positions


async def _resolve[T](awaitable: Awaitable[T]) -> T:
    try:
        return await awaitable
    except ApiError as error:
        codes = {
            400: "BAD_USER_INPUT",
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
        }
        raise GraphQLError(
            error.message,
            extensions={"code": codes.get(error.status_code, "INTERNAL_SERVER_ERROR")},
        ) from error


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(
    schema,
    context_getter=get_graphql_context,
    graphql_ide=None,
    allow_queries_via_get=False,
)
