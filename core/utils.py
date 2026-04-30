import pgeocode


def calculate_postcode_distance(customer_postcode, producer_postcode):
    if not customer_postcode or not producer_postcode:
        return None

    distance = pgeocode.GeoDistance("GB").query_postal_code(
        customer_postcode,
        producer_postcode
    )

    if distance != distance:
        return None

    miles = distance * 0.621371
    return round(miles, 1)