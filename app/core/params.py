from typing import Annotated

from fastapi import Path, Query

# Верхняя граница BIGINT в Postgres: значения больше не влезают в int64 и
# роняли asyncpg с DataError (голый 500 вместо 422).
PG_BIGINT_MAX = 2**63 - 1

PathId = Annotated[int, Path(ge=1, le=PG_BIGINT_MAX)]
QueryId = Annotated[int, Query(ge=1, le=PG_BIGINT_MAX)]

# Глубокий OFFSET дорог независимо от индексов: БД обязана прочитать и отсортировать
# всё, что идёт до страницы, и выбросить. На ленте из 100k комментариев offset 90000
# стоит ~130 мс против долей миллисекунды на первой странице. Живому пользователю
# такие страницы недостижимы, а обходчику - дешёвый способ нагрузить БД.
# Снять потолок можно только вместе с переходом на курсорную пагинацию.
MAX_OFFSET = 10_000

PageOffset = Annotated[int, Query(ge=0, le=MAX_OFFSET)]
