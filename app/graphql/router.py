import strawberry
from strawberry.fastapi import GraphQLRouter

from app.graphql.context import get_graphql_context
from app.graphql.mutation import Mutation
from app.graphql.query import Query

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(
    schema,
    context_getter=get_graphql_context,
    graphql_ide=None,
    allow_queries_via_get=False,
)
