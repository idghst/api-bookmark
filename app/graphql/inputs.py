import strawberry


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
    parent_id: strawberry.ID | None = None


@strawberry.input
class FolderUpdateInput:
    name: str | None = strawberry.UNSET
    color: str | None = strawberry.UNSET
    parent_id: strawberry.ID | None = strawberry.UNSET
    position: int | None = strawberry.UNSET


@strawberry.input
class SectionCreateInput:
    folder_id: strawberry.ID
    name: str
    color: str | None = None


@strawberry.input
class SectionUpdateInput:
    name: str | None = strawberry.UNSET
    color: str | None = strawberry.UNSET
    folder_id: strawberry.ID | None = strawberry.UNSET


@strawberry.input
class PositionInput:
    id: strawberry.ID
    position: int
