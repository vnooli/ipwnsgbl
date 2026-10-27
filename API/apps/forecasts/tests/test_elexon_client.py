from datetime import date

import pytest
import responses

from apps.forecasts.exceptions import UpstreamDataError
from apps.forecasts.repositories.elexon_client import ElexonClient, _chunk_date_range

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"


class TestChunkDateRange:
    def test_range_within_limit_is_a_single_chunk(self):
        chunks = _chunk_date_range(date(2026, 1, 1), date(2026, 1, 5), max_days=7)
        assert chunks == [(date(2026, 1, 1), date(2026, 1, 5))]

    def test_range_exceeding_limit_is_split(self):
        # Elexon rejects a publishDateTime span over 7 days - verified against the live API.
        chunks = _chunk_date_range(date(2026, 1, 1), date(2026, 1, 20), max_days=7)
        assert chunks[0] == (date(2026, 1, 1), date(2026, 1, 7))
        assert chunks[-1][1] == date(2026, 1, 20)
        for c_start, c_end in chunks:
            assert (c_end - c_start).days <= 6

    def test_chunks_are_contiguous_with_no_gaps_or_overlap(self):
        chunks = _chunk_date_range(date(2026, 1, 1), date(2026, 1, 31), max_days=7)
        for (_, prev_end), (next_start, _) in zip(chunks, chunks[1:]):
            assert next_start == prev_end + __import__("datetime").timedelta(days=1)

    def test_empty_when_start_after_end(self):
        assert _chunk_date_range(date(2026, 1, 10), date(2026, 1, 1), max_days=7) == []


@responses.activate
def test_fetch_wind_actuals_chunks_requests_over_seven_days():
    # Two calls expected for a 10-day window split into <=7-day chunks.
    responses.add(responses.GET, f"{BASE_URL}/datasets/FUELHH", json={"data": []}, status=200)
    responses.add(responses.GET, f"{BASE_URL}/datasets/FUELHH", json={"data": []}, status=200)
    client = ElexonClient(base_url=BASE_URL)
    client.fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 10))
    assert len(responses.calls) == 2


@responses.activate
def test_fetch_wind_forecasts_uses_publish_date_time_params_not_from_to():
    responses.add(responses.GET, f"{BASE_URL}/datasets/WINDFOR", json={"data": []}, status=200)
    client = ElexonClient(base_url=BASE_URL)
    client.fetch_wind_forecasts(date(2026, 1, 1), date(2026, 1, 1))
    request_url = responses.calls[0].request.url
    assert "publishDateTimeFrom" in request_url
    assert "publishDateTimeTo" in request_url


@responses.activate
def test_fetch_wind_actuals_filters_to_wind_and_parses_fields():
    responses.add(
        responses.GET,
        f"{BASE_URL}/datasets/FUELHH",
        json={
            "data": [
                {"startTime": "2026-01-01T00:00:00Z", "fuelType": "WIND", "generation": 5123, "settlementPeriod": 1},
                {"startTime": "2026-01-01T00:00:00Z", "fuelType": "CCGT", "generation": 9000, "settlementPeriod": 1},
            ]
        },
        status=200,
    )
    client = ElexonClient(base_url=BASE_URL)
    records = client.fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 1))

    assert len(records) == 1
    assert records[0].fuel_type == "WIND"
    assert records[0].generation_mw == 5123.0


@responses.activate
def test_fetch_wind_actuals_deduplicates_same_start_time():
    responses.add(
        responses.GET,
        f"{BASE_URL}/datasets/FUELHH",
        json={
            "data": [
                {"startTime": "2026-01-01T00:00:00Z", "fuelType": "WIND", "generation": 100},
                {"startTime": "2026-01-01T00:00:00Z", "fuelType": "WIND", "generation": 120},
            ]
        },
        status=200,
    )
    client = ElexonClient(base_url=BASE_URL)
    records = client.fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 1))
    assert len(records) == 1


@responses.activate
def test_fetch_wind_forecasts_parses_publish_time():
    responses.add(
        responses.GET,
        f"{BASE_URL}/datasets/WINDFOR",
        json={
            "data": [
                {"startTime": "2026-01-02T00:00:00Z", "publishTime": "2025-12-31T11:00:00Z", "generation": 4000},
            ]
        },
        status=200,
    )
    client = ElexonClient(base_url=BASE_URL)
    records = client.fetch_wind_forecasts(date(2026, 1, 2), date(2026, 1, 2))
    assert len(records) == 1
    assert records[0].publish_time == "2025-12-31T11:00:00Z"


@responses.activate
def test_malformed_response_raises_upstream_data_error():
    responses.add(responses.GET, f"{BASE_URL}/datasets/FUELHH", json={"unexpected": "shape"}, status=200)
    client = ElexonClient(base_url=BASE_URL)
    with pytest.raises(UpstreamDataError):
        client.fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 1))


@responses.activate
def test_server_error_raises_upstream_data_error_after_retries():
    responses.add(responses.GET, f"{BASE_URL}/datasets/FUELHH", status=500)
    responses.add(responses.GET, f"{BASE_URL}/datasets/FUELHH", status=500)
    responses.add(responses.GET, f"{BASE_URL}/datasets/FUELHH", status=500)
    client = ElexonClient(base_url=BASE_URL)
    with pytest.raises(UpstreamDataError):
        client.fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 1))


@responses.activate
def test_rows_missing_required_fields_are_skipped():
    responses.add(
        responses.GET,
        f"{BASE_URL}/datasets/WINDFOR",
        json={"data": [{"startTime": "2026-01-01T00:00:00Z", "generation": 100}]},  # missing publishTime
        status=200,
    )
    client = ElexonClient(base_url=BASE_URL)
    records = client.fetch_wind_forecasts(date(2026, 1, 1), date(2026, 1, 1))
    assert records == []
