import os
import json
import importlib.util

import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from users.decorators import role_required
from products.models import Product

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_OUTPUT_PATH = os.path.join(BASE_DIR, "hybrid_recommendations.csv")
RECOMMENDER_PATH = os.path.join(BASE_DIR, "hybrid_recommender.py")
SUMMARY_PATH = os.path.join(BASE_DIR, "hybrid_model_summary.json")
BESTSELLER_PATH = os.path.join(BASE_DIR, "bestseller_recommendations.csv")


def _load_recommender():
    """Dynamically load hybrid_recommender.py from project root."""
    spec = importlib.util.spec_from_file_location("hybrid_recommender", RECOMMENDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@role_required("ai_engineer")
def ai_engineer_dashboard(request):
    model_exists = os.path.exists(MODEL_OUTPUT_PATH)
    summary = {}

    if os.path.exists(SUMMARY_PATH):
        with open(SUMMARY_PATH, encoding="utf-8") as f:
            summary = json.load(f)

    return render(request, "ai_engineer/dashboard.html", {
        "model_exists": model_exists,
        "summary": summary,
    })


@role_required("ai_engineer")
def train_model(request):
    if request.method != "POST":
        return redirect("ai_engineer_dashboard")

    try:
        recommender = _load_recommender()
        artifacts = recommender.train_hybrid_model()
        all_recs = recommender.recommend_for_all_users(artifacts, top_n=5)

        all_recs.to_csv(MODEL_OUTPUT_PATH, index=False)

        summary = {
            "orders_rows": int(len(artifacts.orders)),
            "users": int(artifacts.orders["user_key"].nunique()),
            "products": int(artifacts.orders["product_name"].nunique()),
            "alpha": recommender.ALPHA,
            "beta": recommender.BETA,
            "top_n": recommender.TOP_N,
        }

        with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)

        messages.success(
            request,
            f"✅ Model trained successfully! {summary['users']} users, {summary['products']} products."
        )
    except FileNotFoundError as e:
        messages.error(request, f"❌ Missing data file: {e}")
    except Exception as e:
        messages.error(request, f"Training failed: {e}")

    return redirect("ai_engineer_dashboard")


@role_required("ai_engineer")
def view_recommendations(request):
    recs = []

    if not os.path.exists(MODEL_OUTPUT_PATH):
        messages.warning(request, "No recommendations found. Please train the model first.")
        return redirect("ai_engineer_dashboard")

    df = pd.read_csv(MODEL_OUTPUT_PATH)
    recs = df.to_dict("records")

    return render(request, "ai_engineer/recommendations_table.html", {
        "recommendations": recs,
        "total": len(recs),
    })


@login_required
def customer_recommendations(request):
    """Show personalised recommendations for the logged-in customer."""
    username = request.user.username
    recs = []
    error = None

    if not os.path.exists(MODEL_OUTPUT_PATH):
        error = "Recommendations are not available yet. Please check back later."
    else:
        try:
            df = pd.read_csv(MODEL_OUTPUT_PATH)
            user_recs = df[df["user_key"] == username]

            if user_recs.empty:
                if os.path.exists(BESTSELLER_PATH):
                    fallback = pd.read_csv(BESTSELLER_PATH).head(5)
                    recs = fallback.to_dict("records")
                    for r in recs:
                        r["note"] = "Popular with all customers"
                else:
                    error = "No recommendations available for your account yet."
            else:
                recs = user_recs.to_dict("records")

            for r in recs:
                product = Product.objects.filter(
                    name__iexact=str(r.get("product_name", "")).strip(),
                    producer__display_name__iexact=str(r.get("producer_name", "")).strip(),
                ).select_related("producer").first()
                r["product"] = product

        except Exception as e:
            error = str(e)

    return render(request, "ai_engineer/customer_recommendations.html", {
        "recommendations": recs,
        "error": error,
        "username": username,
    })


@login_required
@require_GET
def recommendations_api(request):
    username = request.user.username

    if not os.path.exists(MODEL_OUTPUT_PATH):
        return JsonResponse({"status": "error", "message": "Model not trained yet."}, status=503)

    try:
        df = pd.read_csv(MODEL_OUTPUT_PATH)
        user_recs = df[df["user_key"] == username]

        if user_recs.empty:
            if os.path.exists(BESTSELLER_PATH):
                user_recs = pd.read_csv(BESTSELLER_PATH).head(5)
            else:
                return JsonResponse({"status": "ok", "recommendations": []})

        return JsonResponse({
            "status": "ok",
            "username": username,
            "recommendations": user_recs.to_dict("records"),
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)