import strawberry

from app.schemas import BookmarkOut, FolderOut, SectionOut


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
    parent_id: strawberry.ID | None
    position: int

    @classmethod
    def from_model(cls, model: FolderOut) -> "Folder":
        return cls(
            id=strawberry.ID(model.id),
            name=model.name,
            color=model.color,
            parent_id=(
                strawberry.ID(model.parent_id) if model.parent_id is not None else None
            ),
            position=model.position,
        )


@strawberry.type(name="Section")
class Section:
    id: strawberry.ID
    name: str
    color: str | None
    folder_id: strawberry.ID
    position: int

    @classmethod
    def from_model(cls, model: SectionOut) -> "Section":
        return cls(
            id=strawberry.ID(model.id),
            name=model.name,
            color=model.color,
            folder_id=strawberry.ID(model.folder_id),
            position=model.position,
        )
