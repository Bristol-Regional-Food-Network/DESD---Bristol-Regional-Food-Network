# Philip Thompson 22024226

# These lines suppress TensorFlow warnings and logs for cleaner output during training.
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import warnings
warnings.filterwarnings("ignore")

import sys
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image as keras_image

import json
import h5py

from grading import (
    load_image,
    calculate_colour_score,
    calculate_size_score,
    calculate_ripeness_score,
    assign_grade,
    recommend_action,
    explain_grade,
    explain_rotten_decision,
)

from logging_utils import log_prediction


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "fruit_model.h5")


def preprocess_for_model(image_path):
    img = keras_image.load_img(image_path, target_size=(224, 224))
    img_array = keras_image.img_to_array(img)
    img_array = img_array / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    return img_array


def remove_quantization_config(config):
    if isinstance(config, dict):
        config.pop("quantization_config", None)

        for value in config.values():
            remove_quantization_config(value)

    elif isinstance(config, list):
        for item in config:
            remove_quantization_config(item)


def clean_h5_model_config(model_path):
    with h5py.File(model_path, "r+") as file:
        model_config = file.attrs.get("model_config")

        if model_config is None:
            return

        if isinstance(model_config, bytes):
            model_config = model_config.decode("utf-8")

        config = json.loads(model_config)
        remove_quantization_config(config)

        file.attrs.modify("model_config", json.dumps(config).encode("utf-8"))


def load_trained_model(model_path=MODEL_PATH):
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model not found at {model_path}. Train the model first."
        )

    clean_h5_model_config(model_path)
    return load_model(model_path, compile=False)

def predict_freshness(model, image_path):
    processed = preprocess_for_model(image_path)
    rotten_probability = float(model.predict(processed, verbose=0)[0][0])

    # Dataset labels: fresh = 0, rotten = 1
    fresh_probability = 1.0 - rotten_probability
    predicted_label = "fresh" if fresh_probability >= 0.5 else "rotten"

    return predicted_label, fresh_probability, rotten_probability


def grade_fresh_item(image_path, fresh_probability):
    img = load_image(image_path)

    colour_score = calculate_colour_score(img)
    size_score = calculate_size_score(img)
    ripeness_score = calculate_ripeness_score(fresh_probability)

    grade = assign_grade(colour_score, size_score, ripeness_score)
    action = recommend_action("fresh", grade)
    explanation = explain_grade(
        colour_score, size_score, ripeness_score, grade
    )

    return {
        "colour_score": colour_score,
        "size_score": size_score,
        "ripeness_score": ripeness_score,
        "grade": grade,
        "action": action,
        "explanation": explanation,
    }


def run_pipeline(image_path, model=None):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at {image_path}")

    if model is None:
        model = load_trained_model()

    predicted_label, fresh_prob, rotten_prob = predict_freshness(model, image_path)

    result = {
        "image_path": image_path,
        "predicted_label": predicted_label,
        "fresh_probability": round(fresh_prob, 4),
        "rotten_probability": round(rotten_prob, 4),
        "colour_score": None,
        "size_score": None,
        "ripeness_score": None,
        "grade": None,
        "action": None,
        "explanation": [],
    }

    if predicted_label == "rotten":
        result["action"] = recommend_action("rotten")
        result["explanation"] = explain_rotten_decision(fresh_prob, rotten_prob)
        log_prediction(result)
        return result

    grading_results = grade_fresh_item(image_path, fresh_prob)

    result["colour_score"] = grading_results["colour_score"]
    result["size_score"] = grading_results["size_score"]
    result["ripeness_score"] = grading_results["ripeness_score"]
    result["grade"] = grading_results["grade"]
    result["action"] = grading_results["action"]
    result["explanation"] = grading_results["explanation"]

    log_prediction(result)
    return result


def print_result(result):
    print("\n=== Prediction Result ===")
    print(f"Image: {result['image_path']}")
    print(f"Predicted Label: {result['predicted_label']}")
    print(f"Fresh Probability: {result['fresh_probability']:.4f}")
    print(f"Rotten Probability: {result['rotten_probability']:.4f}")

    if result["predicted_label"] == "rotten":
        print("\n=== Inventory Decision ===")
        print(f"Action: {result['action']}")

        print("\n=== Explanation ===")
        for line in result["explanation"]:
            print(f"- {line}")
        return

    print("\n=== Quality Scores ===")
    print(f"Colour Score: {result['colour_score']}")
    print(f"Size Score: {result['size_score']}")
    print(f"Ripeness Score: {result['ripeness_score']}")

    print("\n=== Final Assessment ===")
    print(f"Grade: {result['grade']}")
    print(f"Action: {result['action']}")

    print("\n=== Explanation ===")
    for line in result["explanation"]:
        print(f"- {line}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/predict_and_grade.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    model = load_trained_model()
    result = run_pipeline(image_path, model=model)
    print_result(result)


if __name__ == "__main__":
    main()