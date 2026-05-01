import os
import subprocess
import sys

import joblib
import numpy as np
import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from products.models import Product
from users.decorators import role_required

APP_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.join(APP_DIR, "task")

DATA_PATH = os.path.join(TASK_DIR, "orders_dataset.csv")
MODEL_PATH = os.path.join(TASK_DIR, "rf_model.pkl")
TARGET_ENCODER_PATH = os.path.join(TASK_DIR, "target_encoder.pkl")
FEATURE_ENCODERS_PATH = os.path.join(TASK_DIR, "feature_encoders.pkl")
TRAINING_SCRIPT_PATH = os.path.join(TASK_DIR, "random_forest_model.py")

FEATURES = [
    "price_per_unit",
    "category_enc",
    "unit_enc",
    "is_organic",
    "line_total",
    "section_enc",
    "quantity",
    "avg_spend",
    "organic_rate",
    "fav_category_enc",
    "total_orders",
    "month",
    "delivery_days",
    "dayofweek",
    "order_status_enc",
]


def _task_files_exist():
    return all(os.path.exists(path) for path in [
        DATA_PATH,
        MODEL_PATH,
        TARGET_ENCODER_PATH,
        FEATURE_ENCODERS_PATH,
    ])


def _prepare_dataset():
    df = pd.read_csv(DATA_PATH)

    df["delivery_days"] = (
        pd.to_datetime(df["delivery_date"]) - pd.to_datetime(df["order_date"])
    ).dt.days
    df["month"] = pd.to_datetime(df["order_date"]).dt.month
    df["dayofweek"] = pd.to_datetime(df["order_date"]).dt.dayofweek

    df["is_organic"] = (
        df["is_organic"].astype(str).str.lower().map({"true": 1, "false": 0})
    )

    user_stats = df.groupby("user_id").agg(
        total_orders=("order_id", "nunique"),
        avg_spend=("line_total", "mean"),
        organic_rate=("is_organic", "mean"),
    ).reset_index()
    df = df.merge(user_stats, on="user_id", how="left")

    fav_cat = (
        df.groupby(["user_id", "category"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .drop_duplicates("user_id")
        .rename(columns={"category": "fav_category"})[["user_id", "fav_category"]]
    )
    df = df.merge(fav_cat, on="user_id", how="left")

    encoders = joblib.load(FEATURE_ENCODERS_PATH)
    for col in ["section", "unit", "category", "fav_category", "order_status"]:
        df[col + "_enc"] = encoders[col].transform(df[col].astype(str))

    return df


def _recommend_for_user(user_id, top_n=5):
    if not _task_files_exist():
        raise FileNotFoundError("Task 1 model files are missing.")

    df = _prepare_dataset()
    model = joblib.load(MODEL_PATH)
    target_encoder = joblib.load(TARGET_ENCODER_PATH)

    user_rows = df[df["user_id"] == int(user_id)]

    if user_rows.empty:
        return [], []

    latest = user_rows.sort_values("order_date").iloc[[-1]]
    x_user = latest[FEATURES]

    probs = model.predict_proba(x_user)[0]
    top_indices = np.argsort(probs)[::-1][:top_n]
    top_products = target_encoder.inverse_transform(top_indices)
    top_scores = probs[top_indices]

    most_purchased = (
        user_rows["product_name"]
        .value_counts()
        .head(5)
        .index
        .tolist()
    )

    recommendations = []
    for product_name, score in zip(top_products, top_scores):
        product = Product.objects.filter(name__iexact=str(product_name)).first()
        recommendations.append({
            "user_id": user_id,
            "product_name": product_name,
            "confidence": round(float(score) * 100, 1),
            "product": product,
        })

    return recommendations, most_purchased


@role_required("ai_engineer")
def ai_engineer_dashboard(request):
    summary = {}

    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        summary = {
            "orders_rows": len(df),
            "users": df["user_id"].nunique(),
            "products": df["product_name"].nunique(),
            "model": "Random Forest",
        }

    return render(request, "ai_engineer/dashboard.html", {
        "model_exists": _task_files_exist(),
        "summary": summary,
    })


@role_required("ai_engineer")
def train_model(request):
    if request.method != "POST":
        return redirect("ai_engineer_dashboard")

    try:
        subprocess.run(
            [sys.executable, TRAINING_SCRIPT_PATH],
            cwd=TASK_DIR,
            check=True,
        )
        messages.success(request, "Task 1 Random Forest model trained successfully.")
    except Exception as e:
        messages.error(request, f"Training failed: {e}")

    return redirect("ai_engineer_dashboard")


@role_required("ai_engineer")
def view_recommendations(request):
    user_id = request.GET.get("user_id", "1")

    try:
        recommendations, most_purchased = _recommend_for_user(user_id, top_n=5)
    except Exception as e:
        messages.error(request, str(e))
        recommendations, most_purchased = [], []

    return render(request, "ai_engineer/recommendations_table.html", {
        "recommendations": recommendations,
        "most_purchased": most_purchased,
        "total": len(recommendations),
        "user_id": user_id,
    })


@login_required
def customer_recommendations(request):
    user_id = request.GET.get("user_id", request.user.id)

    try:
        recommendations, most_purchased = _recommend_for_user(user_id, top_n=5)
        error = None
    except Exception as e:
        recommendations, most_purchased = [], []
        error = str(e)

    return render(request, "ai_engineer/customer_recommendations.html", {
        "recommendations": recommendations,
        "most_purchased": most_purchased,
        "error": error,
        "username": request.user.username,
        "user_id": user_id,
    })


@login_required
@require_GET
def recommendations_api(request):
    user_id = request.GET.get("user_id", request.user.id)

    try:
        recommendations, most_purchased = _recommend_for_user(user_id, top_n=5)
        return JsonResponse({
            "status": "ok",
            "user_id": user_id,
            "most_purchased": most_purchased,
            "recommendations": [
                {
                    "product_name": r["product_name"],
                    "confidence": r["confidence"],
                }
                for r in recommendations
            ],
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)