from pydantic import BaseModel, ConfigDict


class ResponseSchema(BaseModel):
    """Базовый класс для внешних моделей ответа.

    from_attributes позволяет собирать модель прямо из ORM-объекта
    через Schema.model_validate(db_obj), без промежуточного to_dict().
    """
    model_config = ConfigDict(from_attributes=True)
