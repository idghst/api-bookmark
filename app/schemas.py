from pydantic import BaseModel, ConfigDict, Field, model_validator


class BookmarkOut(BaseModel):
    id: str
    title: str
    url: str
    description: str | None
    is_favorite: bool = Field(serialization_alias="isFavorite")
    created_at: str = Field(serialization_alias="createdAt")
    updated_at: str = Field(serialization_alias="updatedAt")
    user_id: str = Field(serialization_alias="userId")
    folder_id: str | None = Field(default=None, serialization_alias="folderId")
    section_id: str | None = Field(default=None, serialization_alias="sectionId")
    position: int = 0

    model_config = ConfigDict(populate_by_name=True)


class BookmarkCreate(BaseModel):
    title: str
    url: str
    description: str | None = None
    is_favorite: bool = Field(default=False, alias="isFavorite")
    folder_id: str | None = Field(default=None, alias="folderId")
    section_id: str | None = Field(default=None, alias="sectionId")

    model_config = ConfigDict(populate_by_name=True)


class BookmarkUpdate(BaseModel):
    title: str | None = None
    url: str | None = None
    description: str | None = None
    is_favorite: bool | None = Field(default=None, alias="isFavorite")
    folder_id: str | None = Field(default=None, alias="folderId")
    section_id: str | None = Field(default=None, alias="sectionId")

    model_config = ConfigDict(populate_by_name=True)


class FolderOut(BaseModel):
    id: str
    name: str
    color: str | None = None
    parent_id: str | None = Field(default=None, serialization_alias="parentId")
    position: int = 0
    user_id: str = Field(serialization_alias="userId")

    model_config = ConfigDict(populate_by_name=True)


class FolderCreate(BaseModel):
    name: str
    color: str | None = None
    parent_id: str | None = Field(default=None, alias="parentId")

    model_config = ConfigDict(populate_by_name=True)


class FolderUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    parent_id: str | None = Field(default=None, alias="parentId")
    position: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def position_cannot_be_null(self) -> "FolderUpdate":
        if "position" in self.model_fields_set and self.position is None:
            raise ValueError("position cannot be null")
        return self


class FolderTreeOut(FolderOut):
    children: list["FolderTreeOut"] = Field(default_factory=list)


class SectionOut(BaseModel):
    id: str
    name: str
    color: str | None = None
    folder_id: str = Field(serialization_alias="folderId")
    position: int = 0
    user_id: str = Field(serialization_alias="userId")

    model_config = ConfigDict(populate_by_name=True)


class SectionCreate(BaseModel):
    name: str
    color: str | None = None
    folder_id: str = Field(alias="folderId")

    model_config = ConfigDict(populate_by_name=True)


class SectionUpdate(BaseModel):
    name: str | None = None
    color: str | None = None


class PositionUpdate(BaseModel):
    id: str
    position: int


class HealthOut(BaseModel):
    status: str
