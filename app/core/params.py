from typing import Annotated

from fastapi import Path, Query

# Верхняя граница BIGINT в Postgres: значения больше не влезают в int64 и
# роняли asyncpg с DataError (голый 500 вместо 422).
PG_BIGINT_MAX = 2**63 - 1

PathId = Annotated[int, Path(ge=1, le=PG_BIGINT_MAX)]
QueryId = Annotated[int, Query(ge=1, le=PG_BIGINT_MAX)]
