"""
S6's parser exit proofs.

  · parsed + rejected + duplicate sum exactly to the row count, for every fixture
  · an unrecognised format is an error, not an empty structure
  · a malformed sheet fails loudly, naming the row and the field
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.ingest.detect import detect, normalise_header, read_rows
from app.services.ingest.propertyDataParser import parse_property_data
from app.services.ingest.result import (
    MalformedInputError,
    ParseStatus,
    UnrecognisedFormatError,
)

COMPARABLES = """address,area_sqft,sale_price,sale_date,property_type,floor
Tower A Unit 604,1420,10650000,2025-11-14,residential apartment,6
Tower B Unit 1102,1510,11780000,2025-10-02,residential apartment,11
Tower C Unit 302,1385,9970000,2025-09-19,residential apartment,3
"""

LEASES = """unit,tenant,area_sqft,monthly_rent,security_deposit,status
G-01,Nilaya Cafe LLP,1240,223200,1339200,occupied
G-02,,1105,0,0,vacant
1-01,Kestrel Analytics,3400,595000,3570000,occupied
"""


def test_a_clean_sheet_parses_every_row():
    result = parse_property_data(COMPARABLES)
    assert result.source_format == "comparables"
    assert result.counts == {"input": 3, "parsed": 3, "rejected": 0, "duplicate": 0}
    result.assert_reconciles()


@pytest.mark.parametrize("payload", [COMPARABLES, LEASES])
def test_counts_reconcile_for_every_fixture(payload):
    """The rule: nothing is dropped silently."""
    result = parse_property_data(payload)
    c = result.counts
    assert c["parsed"] + c["rejected"] + c["duplicate"] == c["input"]


def test_a_vacant_unit_is_data_not_a_rejection():
    """A vacancy has no tenant and no rent, and is still a row of the rent roll."""
    result = parse_property_data(LEASES)
    assert result.counts["parsed"] == 3
    vacant = [r for r in result.parsed if r["status"] == "vacant"]
    assert len(vacant) == 1
    assert vacant[0]["monthly_rent"] == 0


# ── failing loudly ────────────────────────────────────────────────────────────


def test_a_malformed_figure_rejects_the_row_naming_the_field():
    """
    S6's exit proof. The prototype's `_num` turned "on request" into 0.0 and the
    comparable joined the set at ₹0 per sq ft.
    """
    sheet = COMPARABLES + "Tower D Unit 205,1360,on request,2025-08-27,residential apartment,2\n"
    result = parse_property_data(sheet)

    assert result.counts == {"input": 4, "parsed": 3, "rejected": 1, "duplicate": 0}
    rejected = result.rejected[0]
    assert rejected.row_number == 5  # header is row 1
    assert "sale_price" in rejected.reason
    assert "on request" in rejected.reason
    assert rejected.raw is not None


def test_a_missing_required_field_names_the_column_and_its_aliases():
    sheet = COMPARABLES + "Tower E Unit 1802,,13770000,2026-02-03,residential apartment,18\n"
    result = parse_property_data(sheet)

    reason = result.rejected[0].reason
    assert "area is required" in reason
    assert "empty" in reason


def test_a_missing_column_is_named_as_missing_not_empty():
    sheet = "address,area_sqft,sale_price,property_type\nA,1000,5000000,flat\n"
    result = parse_property_data(sheet, source_format="comparables")
    reason = result.rejected[0].reason
    assert "sale_date is required" in reason
    assert "column is missing" in reason


def test_an_unparseable_date_is_rejected_rather_than_guessed():
    sheet = COMPARABLES + "Tower F,1200,9000000,sometime last year,flat,4\n"
    result = parse_property_data(sheet)
    assert "sale_date is not a recognisable date" in result.rejected[0].reason


def test_dates_are_read_day_first():
    """
    `03/04/2025` is 3 April in every Indian land record. Reading it as 3 March
    would age the comparable by a month, which changes its time adjustment.
    """
    sheet = "address,area_sqft,sale_price,sale_date\nA,1000,5000000,03/04/2025\n"
    result = parse_property_data(sheet, source_format="comparables")
    assert result.parsed[0]["sale_date"].month == 4
    assert result.parsed[0]["sale_date"].day == 3


# ── duplicates ────────────────────────────────────────────────────────────────


def test_a_repeated_comparable_is_a_duplicate_not_a_second_data_point():
    sheet = COMPARABLES + "Tower A Unit 604,1420,10650000,2025-11-14,residential apartment,6\n"
    result = parse_property_data(sheet)

    assert result.counts == {"input": 4, "parsed": 3, "rejected": 0, "duplicate": 1}
    reason = result.duplicates[0].reason
    assert "duplicates row 2" in reason
    assert "weight the same evidence twice" in reason


def test_an_empty_row_is_counted_and_explained():
    result = parse_property_data(COMPARABLES + ",,,,,\n")
    assert result.counts["input"] == 4
    assert result.rejected[0].reason == "the row is empty"


# ── detection ─────────────────────────────────────────────────────────────────


def test_an_unrecognised_format_is_an_error_not_an_empty_structure():
    """
    The prototype fell through to `generic_csv` and let a valuation over zero
    usable comparables render successfully.
    """
    with pytest.raises(UnrecognisedFormatError) as excinfo:
        parse_property_data("colour,shape,mood\nred,round,calm\n")
    assert "no known format matches" in str(excinfo.value)
    assert "comparables" in str(excinfo.value)
    assert "explicit `source_format`" in str(excinfo.value)


def test_detection_is_overridable_by_the_caller():
    """Detection is a convenience, never an authority."""
    detection = detect(["anything", "at", "all"], source_format="comparables")
    assert detection.schema.key == "comparables"
    assert detection.explicit is True


def test_formats_that_share_a_column_are_still_told_apart():
    """Comparables and portfolio both have `area`. Only one has `sale_price`."""
    assert detect(list(COMPARABLES.splitlines()[0].split(","))).schema.key == "comparables"

    portfolio = "property_name,area_sqft,current_value,purchase_price"
    assert detect(portfolio.split(",")).schema.key == "portfolio"


def test_headers_normalise_past_punctuation_and_units():
    assert normalise_header("Sale Price (₹)") == "sale_price"
    assert normalise_header("Completion %") == "completion_%"
    assert normalise_header("  Area_SqFt  ") == "area_sqft"


def test_an_empty_payload_is_an_error():
    with pytest.raises(MalformedInputError, match="empty"):
        parse_property_data("   ")


def test_a_header_with_no_rows_is_an_error():
    with pytest.raises(MalformedInputError, match="no data rows"):
        parse_property_data("address,area_sqft,sale_price,sale_date\n")


def test_broken_json_says_so():
    with pytest.raises(MalformedInputError, match="not valid"):
        parse_property_data('[{"address": "A", }]')


def test_json_input_works():
    payload = (
        '[{"address":"A","area_sqft":"1000","sale_price":"5000000","sale_date":"2025-01-01"}]'
    )
    result = parse_property_data(payload)
    assert result.counts["parsed"] == 1
    assert result.parsed[0]["sale_price"] == Decimal("5000000")


def test_semicolon_and_tab_delimited_sheets_are_read():
    for delimiter in (";", "\t"):
        sheet = COMPARABLES.replace(",", delimiter)
        assert parse_property_data(sheet).counts["parsed"] == 3


# ── land records and the state-aware conversion ───────────────────────────────


LAND = """survey_no,owner_name,area,area_unit,state
118/2,A Sharma,2,bigha,UP
119/1,B Sharma,3,guntha,MH
"""


def test_a_land_parcel_in_a_state_dependent_unit_is_rejected_without_verification():
    """
    The factor is commonly cited, not notified. Converting on it silently would
    put an unverifiable area into a valuation.
    """
    result = parse_property_data(LAND)
    assert result.counts["parsed"] == 1          # the guntha parcel
    assert result.counts["rejected"] == 1        # the bigha parcel
    assert "not verified" in result.rejected[0].reason


def test_with_the_opt_in_the_bigha_converts_for_its_state():
    result = parse_property_data(LAND, allow_unverified_units=True)
    assert result.counts["parsed"] == 2

    bigha = next(r for r in result.parsed if r["survey_no"] == "118/2")
    assert bigha["area_sqft"] == Decimal("54000")     # 2 × 27,000 for UP
    assert bigha["area_original_unit"] == "bigha"

    guntha = next(r for r in result.parsed if r["survey_no"] == "119/1")
    assert guntha["area_sqft"] == Decimal("3267")     # 3 × 1,089


def test_a_land_parcel_with_no_state_is_rejected_naming_why():
    sheet = "survey_no,area,area_unit,state\n118/2,2,bigha,\n"
    result = parse_property_data(sheet, source_format="land_records")
    assert result.counts["rejected"] == 1
    assert "state is required" in result.rejected[0].reason


def test_read_rows_reports_the_headers_it_found():
    headers, rows = read_rows(COMPARABLES)
    assert headers[0] == "address"
    assert len(rows) == 3


def test_every_parsed_row_keeps_its_spreadsheet_row_number():
    """So a rejected list and a parsed list refer to the same rows a human sees."""
    result = parse_property_data(COMPARABLES)
    assert [r["_row"] for r in result.parsed] == [2, 3, 4]


def test_the_result_dict_carries_counts_and_rejections_to_the_console():
    sheet = COMPARABLES + "bad,notanumber,alsobad,nope,x,y\n"
    payload = parse_property_data(sheet).to_dict()
    assert payload["counts"]["rejected"] == 1
    assert payload["rejected"][0]["row"] == 5
    assert payload["rejected"][0]["reason"]
    assert payload["schema_version"] == "2.0"


def test_row_statuses_are_the_three_the_console_shows():
    assert {s.value for s in ParseStatus} == {"parsed", "rejected", "duplicate"}
