from app.similarbooks.main.utils import get_filter_dict


def test_get_filter_dict():
    assert get_filter_dict(
        "https://www.similarbooks.net/wohnung/kaufen/?spider=immowelt&pma=1000000&pmi=20000&psqmi=1000&psqma=20000&ami=10&ama=100&price_has_changed=true&bl=bl-bayern&is_foreclosure=false&is_erbbaurecht=false&ymi=1992&yma=2024&pbmv=true&cma=123&cmi=50&roimi=0.02&roima=0.1"
    ) == {
        "immo_id_in": None,
        "action": "kaufen",
        "zipcode_in": None,
        "location": "bl-bayern",
        "title_contains": None,
        "square_meter_gt": 10,
        "square_meter_lt": 100,
        "price_lt": 1000000,
        "price_gt": 20000,
        "cashflow_gt": 50,
        "cashflow_lt": 123,
        "roi_gt": 0.02,
        "roi_lt": 0.1,
        "price_per_square_meter_lt": 20000,
        "price_per_square_meter_gt": 1000,
        "rent_price_lt": None,
        "rent_price_gt": None,
        "rent_per_square_meter_lt": None,
        "rent_per_square_meter_gt": None,
        "year_of_construction_gt": "1992-01-01T00:00:00.000000",
        "year_of_construction_lt": "2024-01-01T00:00:00.000000",
        "uptime_date_gt": None,
        "date_gt": None,
        "is_active": True,
        "price_has_changed": True,
        "price_has_increased": None,
        "price_below_market_value": True,
        "spider": "immowelt",
        "is_foreclosure": False,
        "is_erbbaurecht": False,
    }
