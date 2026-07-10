from tests.support.assertions import assert_status_code
from tests.support.factories import BookclubFactory
from tests.support.flows import AuthFlow, BookclubFlow


def _create(api, auth, name, description=None, genres=None):
    payload = BookclubFactory.payload(name=name, description=description, genres=genres)
    return BookclubFlow.create(api, auth=auth, payload=payload).json()["data"]["id"]


def _ids(response):
    return {club["id"] for club in response.json()["data"]["items"]}


class TestBookclubSearch:
    def test_requires_authorization(self, api):
        assert_status_code(api.search_bookclubs(query="что угодно"), 401)

    def test_partial_name_matches(self, api):
        auth = AuthFlow.register(api)
        target = _create(api, auth, "Клуб любителей фантастики")
        _create(api, auth, "Поэтический кружок")

        response = api.search_bookclubs(headers=auth.headers, query="фантаст")

        assert_status_code(response, 200)
        assert _ids(response) == {target}

    def test_search_is_case_insensitive(self, api):
        auth = AuthFlow.register(api)
        target = _create(api, auth, "Detective Stories")

        response = api.search_bookclubs(headers=auth.headers, query="DETECTIVE")

        assert_status_code(response, 200)
        assert target in _ids(response)

    def test_matches_description(self, api):
        auth = AuthFlow.register(api)
        target = _create(api, auth, "Первый клуб", description="Обсуждаем скандинавский нуар и триллеры")
        _create(api, auth, "Второй клуб", description="Читаем детские сказки")

        response = api.search_bookclubs(headers=auth.headers, query="скандинавский")

        assert_status_code(response, 200)
        assert _ids(response) == {target}

    def test_matches_genre_by_code(self, api):
        auth = AuthFlow.register(api)
        target = _create(api, auth, "Тайный клуб", description="Без ключевых слов", genres=["fantasy"])
        _create(api, auth, "Другой клуб", description="Ничего общего", genres=["poetry"])

        response = api.search_bookclubs(headers=auth.headers, query="fantasy")

        assert_status_code(response, 200)
        assert _ids(response) == {target}

    def test_matches_genre_by_name(self, api):
        auth = AuthFlow.register(api)
        target = _create(api, auth, "Тайный клуб", description="Без ключевых слов", genres=["fantasy"])
        _create(api, auth, "Другой клуб", description="Ничего общего", genres=["poetry"])

        response = api.search_bookclubs(headers=auth.headers, query="Фэнтези")

        assert_status_code(response, 200)
        assert _ids(response) == {target}

    def test_no_match_returns_empty(self, api):
        auth = AuthFlow.register(api)
        _create(api, auth, "Клуб путешественников", description="Про походы", genres=["poetry"])

        response = api.search_bookclubs(headers=auth.headers, query="кулинария")

        assert_status_code(response, 200)
        assert response.json()["data"]["items"] == []
        assert response.json()["data"]["total"] == 0

    def test_wildcard_is_treated_literally(self, api):
        auth = AuthFlow.register(api)
        literal = _create(api, auth, "Скидка 50% на книги")
        _create(api, auth, "Обычный клуб")

        # '%' в запросе не должен превращаться в LIKE-джокер и матчить всё подряд
        response = api.search_bookclubs(headers=auth.headers, query="50%")

        assert_status_code(response, 200)
        assert _ids(response) == {literal}

    def test_empty_body_returns_all(self, api):
        auth = AuthFlow.register(api)
        first = _create(api, auth, "Первый клуб")
        second = _create(api, auth, "Второй клуб")

        response = api.search_bookclubs(headers=auth.headers)

        assert_status_code(response, 200)
        assert {first, second} <= _ids(response)

    def test_paginates(self, api):
        auth = AuthFlow.register(api)
        for i in range(3):
            _create(api, auth, f"Клуб фантастики {i}")

        response = api.search_bookclubs(headers=auth.headers, query="фантастики", limit=2, offset=0)

        assert_status_code(response, 200)
        data = response.json()["data"]
        assert data["total"] == 3
        assert len(data["items"]) == 2


class TestBookclubSearchRelation:
    def test_relation_owner_returns_only_owned_clubs(self, api):
        auth = AuthFlow.register(api)
        BookclubFlow.create(api, auth=auth)
        BookclubFlow.create(api)

        response = api.search_bookclubs(headers=auth.headers, relation="owner")

        assert_status_code(response, 200)
        items = response.json()["data"]["items"]
        assert len(items) == 1
        assert all(club["owner"]["id"] == auth.user_id for club in items)

    def test_relation_member_returns_joined_clubs(self, api):
        owner_auth = AuthFlow.register(api)
        own_club_id = BookclubFlow.create(api, auth=owner_auth).json()["data"]["id"]

        member_auth = AuthFlow.register(api)
        joined_club_id = BookclubFlow.create(api).json()["data"]["id"]
        api.join_bookclub(joined_club_id, headers=member_auth.headers)

        response = api.search_bookclubs(headers=member_auth.headers, relation="member")

        assert_status_code(response, 200)
        club_ids = _ids(response)
        assert club_ids == {joined_club_id}
        assert own_club_id not in club_ids

    def test_relation_member_includes_owned_clubs(self, api):
        auth = AuthFlow.register(api)
        own_club_id = BookclubFlow.create(api, auth=auth).json()["data"]["id"]

        response = api.search_bookclubs(headers=auth.headers, relation="member")

        assert_status_code(response, 200)
        assert own_club_id in _ids(response)

    def test_relation_and_query_combine(self, api):
        auth = AuthFlow.register(api)
        target = _create(api, auth, "Мой клуб фантастики")
        _create(api, auth, "Мой поэтический клуб")
        _create(api, None, "Чужой клуб фантастики")  # другой владелец

        response = api.search_bookclubs(headers=auth.headers, relation="owner", query="фантастики")

        assert_status_code(response, 200)
        assert _ids(response) == {target}

    def test_rejects_invalid_relation(self, api):
        auth = AuthFlow.register(api)
        response = api.search_bookclubs(headers=auth.headers, relation="stranger")

        assert_status_code(response, 422)
