from typing import Annotated

from fastapi import Depends
from strawberry.fastapi import BaseContext

from app.integrations.supabase import AuthContext, get_resource_auth_context


class GraphQLContext(BaseContext):
    def __init__(self, auth: AuthContext) -> None:
        super().__init__()
        self.auth = auth


async def get_graphql_context(
    auth: Annotated[AuthContext, Depends(get_resource_auth_context)],
) -> GraphQLContext:
    return GraphQLContext(auth=auth)
