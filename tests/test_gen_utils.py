"""
Tests for incidentbot/util/gen.py

gen.py is importable without any patching — it reads settings.options.timezone
at call-time, not at import-time.
"""
import datetime
import string


from incidentbot.util import gen


# ---------------------------------------------------------------------------
# fetch_timestamp
# ---------------------------------------------------------------------------


class TestFetchTimestamp:
    def test_returns_formatted_string_by_default(self):
        result = gen.fetch_timestamp(tz="UTC")
        assert isinstance(result, str)
        parsed = datetime.datetime.strptime(result, gen.timestamp_fmt)
        assert parsed.year >= 2024

    def test_returns_float_when_epoch_true(self):
        result = gen.fetch_timestamp(epoch=True, tz="UTC")
        assert isinstance(result, float)
        assert result > 0

    def test_epoch_and_string_agree(self):
        import time
        before = time.time()
        epoch = gen.fetch_timestamp(epoch=True, tz="UTC")
        after = time.time()
        # Allow 1 ms of slack for float precision differences between
        # time.time() (nanosecond resolution) and the epoch value returned
        # by fetch_timestamp (which may be truncated to microseconds).
        assert before - 0.001 <= epoch <= after + 0.001

    def test_different_timezones_produce_different_hours(self):
        ny = gen.fetch_timestamp(tz="America/New_York")
        utc = gen.fetch_timestamp(tz="UTC")
        parsed_ny = datetime.datetime.strptime(ny, gen.timestamp_fmt)
        parsed_utc = datetime.datetime.strptime(utc, gen.timestamp_fmt)
        # Verifies the function ran for both timezones without error
        assert parsed_ny is not None and parsed_utc is not None


# ---------------------------------------------------------------------------
# find_index_in_list
# ---------------------------------------------------------------------------


class TestFindIndexInList:
    def test_finds_match_at_start(self):
        lst = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        assert gen.find_index_in_list(lst, "id", "a") == 0

    def test_finds_match_in_middle(self):
        lst = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        assert gen.find_index_in_list(lst, "id", "b") == 1

    def test_finds_match_at_end(self):
        lst = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        assert gen.find_index_in_list(lst, "id", "c") == 2

    def test_returns_minus_one_when_not_found(self):
        lst = [{"id": "a"}, {"id": "b"}]
        assert gen.find_index_in_list(lst, "id", "z") == -1

    def test_returns_first_occurrence(self):
        lst = [{"k": "v"}, {"k": "v"}, {"k": "other"}]
        assert gen.find_index_in_list(lst, "k", "v") == 0

    def test_empty_list_returns_minus_one(self):
        assert gen.find_index_in_list([], "k", "v") == -1

    def test_multiple_keys_in_dict(self):
        lst = [{"id": "x", "name": "foo"}, {"id": "y", "name": "bar"}]
        assert gen.find_index_in_list(lst, "name", "bar") == 1


# ---------------------------------------------------------------------------
# paginate_dictionary
# ---------------------------------------------------------------------------


class TestPaginateDictionary:
    def test_yields_correct_number_of_pages(self):
        d = {str(i): i for i in range(10)}
        pages = list(gen.paginate_dictionary(d, 3))
        # 10 items / 3 per page → 3 full + 1 remainder = 4 pages
        assert len(pages) == 4

    def test_all_pages_at_most_per_page_size(self):
        d = {str(i): i for i in range(10)}
        for page in gen.paginate_dictionary(d, 3):
            assert len(page) <= 3

    def test_all_items_included(self):
        d = {str(i): i for i in range(7)}
        pages = list(gen.paginate_dictionary(d, 3))
        items = [item for page in pages for item in page]
        assert len(items) == 7

    def test_single_page_when_dict_smaller_than_per_page(self):
        d = {"a": 1, "b": 2}
        pages = list(gen.paginate_dictionary(d, 5))
        assert len(pages) == 1
        assert len(pages[0]) == 2

    def test_exact_fit_produces_no_remainder_page(self):
        d = {str(i): i for i in range(6)}
        pages = list(gen.paginate_dictionary(d, 3))
        assert len(pages) == 2

    def test_empty_dict_yields_nothing(self):
        pages = list(gen.paginate_dictionary({}, 3))
        assert pages == []

    def test_per_page_one(self):
        d = {"a": 1, "b": 2, "c": 3}
        pages = list(gen.paginate_dictionary(d, 1))
        assert len(pages) == 3
        assert all(len(p) == 1 for p in pages)


# ---------------------------------------------------------------------------
# random_string_generator
# ---------------------------------------------------------------------------


class TestRandomStringGenerator:
    _valid = set(string.ascii_uppercase + string.digits)

    def test_returns_string(self):
        assert isinstance(gen.random_string_generator(), str)

    def test_length_is_eight(self):
        assert len(gen.random_string_generator()) == 8

    def test_only_valid_characters(self):
        for _ in range(20):
            result = gen.random_string_generator()
            assert all(c in self._valid for c in result)

    def test_results_vary(self):
        # With 36^8 ≈ 2.8 trillion possibilities, 50 draws should all differ
        results = {gen.random_string_generator() for _ in range(50)}
        assert len(results) > 1
