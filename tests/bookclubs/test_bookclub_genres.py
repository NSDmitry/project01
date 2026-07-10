from tests.support.assertions import assert_status_code
from tests.support.factories import BookclubFactory
from tests.support.flows import AuthFlow, BookclubFlow


class TestBookclubGenresCatalog:
    def test_catalog_returns_seeded_genres(self, api):
        auth = AuthFlow.register(api)
        response = api.genres(headers=auth.headers)
        data = response.json()["data"]

        assert_status_code(response, 200)
        codes = [genre["code"] for genre in data]
        assert len(data) == 23
        assert "fiction" in codes
        assert "sci-fi" in codes
        assert "dystopia" in codes
        assert all(genre["code"] and genre["name"] for genre in data)

    def test_catalog_is_sorted_by_sort_order(self, api):
        auth = AuthFlow.register(api)
        data = api.genres(headers=auth.headers).json()["data"]

        # fiction (10) сеется раньше sci-fi (40) - каталог отдаётся по sort_order
        codes = [genre["code"] for genre in data]
        assert codes.index("fiction") < codes.index("sci-fi")

    def test_catalog_requires_auth(self, api):
        assert_status_code(api.genres(), 401)


class TestBookclubCreateGenres:
    def test_create_returns_selected_genres(self, api):
        payload = BookclubFactory.payload(genres=["sci-fi", "fantasy"])
        response = BookclubFlow.create(api, payload=payload)
        data = response.json()["data"]

        assert_status_code(response, 201)
        assert {genre["code"] for genre in data["genres"]} == {"sci-fi", "fantasy"}

    def test_create_rejects_unknown_genre(self, api):
        payload = BookclubFactory.payload(genres=["definitely-not-a-genre"])
        assert_status_code(BookclubFlow.create(api, payload=payload), 422)

    def test_create_requires_at_least_one_genre(self, api):
        payload = BookclubFactory.payload(genres=[])
        assert_status_code(BookclubFlow.create(api, payload=payload), 422)

    def test_create_rejects_more_than_five_genres(self, api):
        payload = BookclubFactory.payload(
            genres=["fiction", "non-fiction", "classics", "sci-fi", "fantasy", "detective"],
        )
        assert_status_code(BookclubFlow.create(api, payload=payload), 422)

    def test_create_deduplicates_repeated_genres(self, api):
        payload = BookclubFactory.payload(genres=["sci-fi", "sci-fi"])
        response = BookclubFlow.create(api, payload=payload)
        data = response.json()["data"]

        assert_status_code(response, 201)
        assert [genre["code"] for genre in data["genres"]] == ["sci-fi"]


class TestBookclubUpdateGenres:
    @staticmethod
    def _create_club(api, auth, genres=None):
        payload = BookclubFactory.payload(genres=genres or ["fiction"])
        return BookclubFlow.create(api, auth=auth, payload=payload).json()["data"]["id"]

    def test_owner_replaces_whole_genre_set(self, api):
        auth = AuthFlow.register(api)
        club_id = self._create_club(api, auth, genres=["fiction"])

        response = api.set_bookclub_genres(club_id, {"genres": ["sci-fi", "fantasy"]}, headers=auth.headers)
        data = response.json()["data"]

        assert_status_code(response, 200)
        # старый жанр fiction ушёл - это замена набора, а не слияние
        assert {genre["code"] for genre in data["genres"]} == {"sci-fi", "fantasy"}

    def test_returns_genres_sorted_by_sort_order(self, api):
        auth = AuthFlow.register(api)
        club_id = self._create_club(api, auth)

        data = api.set_bookclub_genres(club_id, {"genres": ["sci-fi", "fiction"]}, headers=auth.headers).json()["data"]

        codes = [genre["code"] for genre in data["genres"]]
        assert codes == ["fiction", "sci-fi"]

    def test_rejects_unknown_genre(self, api):
        auth = AuthFlow.register(api)
        club_id = self._create_club(api, auth)

        response = api.set_bookclub_genres(club_id, {"genres": ["definitely-not-a-genre"]}, headers=auth.headers)
        assert_status_code(response, 422)

    def test_requires_at_least_one_genre(self, api):
        auth = AuthFlow.register(api)
        club_id = self._create_club(api, auth)

        response = api.set_bookclub_genres(club_id, {"genres": []}, headers=auth.headers)
        assert_status_code(response, 422)

    def test_rejects_more_than_five_genres(self, api):
        auth = AuthFlow.register(api)
        club_id = self._create_club(api, auth)

        response = api.set_bookclub_genres(
            club_id,
            {"genres": ["fiction", "non-fiction", "classics", "sci-fi", "fantasy", "detective"]},
            headers=auth.headers,
        )
        assert_status_code(response, 422)

    def test_deduplicates_repeated_genres(self, api):
        auth = AuthFlow.register(api)
        club_id = self._create_club(api, auth)

        data = api.set_bookclub_genres(
            club_id, {"genres": ["sci-fi", "sci-fi"]}, headers=auth.headers
        ).json()["data"]

        assert [genre["code"] for genre in data["genres"]] == ["sci-fi"]

    def test_only_owner_can_update(self, api):
        owner = AuthFlow.register(api)
        club_id = self._create_club(api, owner)
        stranger = AuthFlow.register(api)

        response = api.set_bookclub_genres(club_id, {"genres": ["sci-fi"]}, headers=stranger.headers)
        assert_status_code(response, 403)

    def test_unknown_club_returns_404(self, api):
        auth = AuthFlow.register(api)

        response = api.set_bookclub_genres(999999, {"genres": ["fiction"]}, headers=auth.headers)
        assert_status_code(response, 404)

    def test_requires_auth(self, api):
        auth = AuthFlow.register(api)
        club_id = self._create_club(api, auth)

        assert_status_code(api.set_bookclub_genres(club_id, {"genres": ["fiction"]}), 401)
