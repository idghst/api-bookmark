import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info

from app.graphql.context import GraphQLContext, get_graphql_context
from app.graphql.errors import positions, resolve, update_values
from app.graphql.inputs import (
    BookmarkCreateInput,
    BookmarkUpdateInput,
    FolderCreateInput,
    FolderUpdateInput,
    PositionInput,
    SectionCreateInput,
    SectionUpdateInput,
)
from app.graphql.types import Bookmark, Folder, Section
from app.schemas import (
    BookmarkCreate,
    BookmarkUpdate,
    FolderCreate,
    FolderUpdate,
    SectionCreate,
    SectionUpdate,
)
from app.services import bookmarks, folders, sections


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
        rows = await resolve(folders.list_folders(info.context.auth))
        return [Folder.from_model(row) for row in rows]

    @strawberry.field
    async def sections(self, info: Info[GraphQLContext, None]) -> list[Section]:
        rows = await resolve(sections.list_sections(info.context.auth))
        return [Section.from_model(row) for row in rows]


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_bookmark(
        self,
        info: Info[GraphQLContext, None],
        input: BookmarkCreateInput,
    ) -> Bookmark:
        row = await resolve(
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
        row = await resolve(
            bookmarks.update_bookmark(
                id,
                BookmarkUpdate.model_validate(update_values(input)),
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
        await resolve(bookmarks.delete_bookmark(id, info.context.auth))
        return True

    @strawberry.mutation
    async def reorder_bookmarks(
        self,
        info: Info[GraphQLContext, None],
        input: list[PositionInput],
    ) -> bool:
        await resolve(bookmarks.reorder_bookmarks(positions(input), info.context.auth))
        return True

    @strawberry.mutation
    async def create_folder(
        self,
        info: Info[GraphQLContext, None],
        input: FolderCreateInput,
    ) -> Folder:
        row = await resolve(
            folders.create_folder(
                FolderCreate(
                    name=input.name,
                    color=input.color,
                    parentId=input.parent_id,
                ),
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
        row = await resolve(
            folders.update_folder(
                id,
                FolderUpdate.model_validate(update_values(input)),
                info.context.auth,
            )
        )
        return Folder.from_model(row)

    @strawberry.mutation
    async def delete_folder(
        self,
        info: Info[GraphQLContext, None],
        id: strawberry.ID,
        destination_folder_id: strawberry.ID | None = None,
    ) -> bool:
        await resolve(
            folders.delete_folder(id, info.context.auth, destination_folder_id)
        )
        return True

    @strawberry.mutation
    async def reorder_folders(
        self,
        info: Info[GraphQLContext, None],
        input: list[PositionInput],
    ) -> bool:
        await resolve(folders.reorder_folders(positions(input), info.context.auth))
        return True

    @strawberry.mutation
    async def create_section(
        self,
        info: Info[GraphQLContext, None],
        input: SectionCreateInput,
    ) -> Section:
        row = await resolve(
            sections.create_section(
                SectionCreate(
                    folderId=input.folder_id,
                    name=input.name,
                    color=input.color,
                ),
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
        row = await resolve(
            sections.update_section(
                id,
                SectionUpdate.model_validate(update_values(input)),
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
        await resolve(sections.delete_section(id, info.context.auth))
        return True

    @strawberry.mutation
    async def reorder_sections(
        self,
        info: Info[GraphQLContext, None],
        input: list[PositionInput],
    ) -> bool:
        await resolve(sections.reorder_sections(positions(input), info.context.auth))
        return True


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(
    schema,
    context_getter=get_graphql_context,
    graphql_ide=None,
    allow_queries_via_get=False,
)
