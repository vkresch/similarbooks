import requests
from utils import load_file, model_dict, get_price_per_square_meter
import pandas as pd


# TODO: Add model tests so that they make sense
def main():
    flat_dict = {
        "immo_id": "2dfmv55",
        "lat": 53.564,
        "lon": 9.8798,
        "square_meter": 175.5,
        "rooms": 5,
        "age": "1960",
    }

    print("------------")
    rent_price_per_square_meter, price_per_square_meter, similar_properties = (
        get_price_per_square_meter("all_appartments", flat_dict, "2dfmv55")
    )

    print(
        "Wohnungsmiete: %.2f € (%.2f €/m²)"
        % (
            rent_price_per_square_meter * flat_dict["square_meter"],
            rent_price_per_square_meter,
        )
    )
    print(
        "Wohnungspreis: %.2f € (%.2f €/m²)"
        % (
            price_per_square_meter * flat_dict["square_meter"],
            price_per_square_meter,
        )
    )
    print("------------")
    rent_price_per_square_meter, price_per_square_meter, similar_properties = (
        get_price_per_square_meter("all_houses", flat_dict, "2dfmv55")
    )
    print(
        "Hausmiete: %.2f € (%.2f €/m²)"
        % (
            rent_price_per_square_meter * flat_dict["square_meter"],
            rent_price_per_square_meter,
        )
    )
    print(
        "Hauspreis: %.2f € (%.2f €/m²)"
        % (
            price_per_square_meter * flat_dict["square_meter"],
            price_per_square_meter,
        )
    )


if __name__ == "__main__":
    main()
