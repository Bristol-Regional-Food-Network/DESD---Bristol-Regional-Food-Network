import requests

AI_SERVICE_URL = "http://ai_service:5001/predict"


def inspect_product_image(image_path):
    with open(image_path, "rb") as img:
        response = requests.post(
            AI_SERVICE_URL,
            files={"image": img},
            timeout=60,
        )

    response.raise_for_status()
    return response.json()