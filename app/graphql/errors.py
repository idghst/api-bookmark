from collections.abc import Awaitable

from graphql import GraphQLError
from strawberry.types.unset import UnsetType

from app.core.errors import ApiError
from app.graphql.inputs import PositionInput
from app.schemas import PositionUpdate


def update_values(input: object) -> dict[str, object]:
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


def positions(input: list[PositionInput]) -> list[PositionUpdate]:
    ids: set[str] = set()
    result: list[PositionUpdate] = []
    for item in input:
        if not item.id.strip() or item.id in ids or item.position < 0:
            raise GraphQLError(
                "Invalid position input",
                extensions={"code": "BAD_USER_INPUT"},
            )
        ids.add(item.id)
        result.append(PositionUpdate(id=item.id, position=item.position))
    return result


async def resolve[T](awaitable: Awaitable[T]) -> T:
    try:
        return await awaitable
    except ApiError as error:
        codes = {
            400: "BAD_USER_INPUT",
            401: "UNAUTHENTICATED",
            422: "BAD_USER_INPUT",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
        }
        raise GraphQLError(
            error.message,
            extensions={"code": codes.get(error.status_code, "INTERNAL_SERVER_ERROR")},
        ) from error
