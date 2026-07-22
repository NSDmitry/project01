from tests.support.assertions import assert_status_code
from tests.support.flows import AuthFlow

OVER_INT64_ID = 99999999999999999999999


class TestPathIdBounds:
    def test_get_bookclub_with_id_over_int64_returns_422(self, api):
        auth = AuthFlow.register(api)
        assert_status_code(api.bookclub(OVER_INT64_ID, headers=auth.headers), 422)

    def test_get_bookclub_with_zero_id_returns_422(self, api):
        auth = AuthFlow.register(api)
        assert_status_code(api.bookclub(0, headers=auth.headers), 422)

    def test_get_threads_with_id_over_int64_returns_422(self, api):
        auth = AuthFlow.register(api)
        assert_status_code(api.threads(OVER_INT64_ID, headers=auth.headers), 422)

    def test_get_comment_likers_with_id_over_int64_returns_422(self, api):
        auth = AuthFlow.register(api)
        assert_status_code(api.comment_likers(OVER_INT64_ID, headers=auth.headers), 422)
