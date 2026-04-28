import os
import json
import warnings
from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd

from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "DATA")

ORDERS_FILE = os.path.join(DATA_DIR, "orders_dataset.csv")
CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers_dataset.csv")
PRODUCERS_FILE = os.path.join(DATA_DIR, "producers_dataset.csv")

ALPHA = 0.6   # weight for SVD score
BETA = 0.4    # weight for RF probability
TOP_N = 5
RANDOM_STATE = 42


# ============================================================
# DATA CONTAINER
# ============================================================

@dataclass
class HybridArtifacts:
    orders: pd.DataFrame
    user_item_matrix: pd.DataFrame
    svd_model: TruncatedSVD
    user_factors: np.ndarray
    item_factors: np.ndarray
    rf_model: RandomForestClassifier
    rf_predictions: pd.DataFrame
    product_popularity: pd.Series
    bestseller_baseline: pd.DataFrame


# ============================================================
# LOAD + CLEAN
# ============================================================

def check_files():
    required = [ORDERS_FILE, CUSTOMERS_FILE, PRODUCERS_FILE]
    missing = [f for f in required if not os.path.exists(f)]
    if missing:
        raise FileNotFoundError(
            "Missing required file(s):\n" + "\n".join(missing)
        )


def load_orders() -> pd.DataFrame:
    df = pd.read_csv(ORDERS_FILE)

    required_cols = [
        "order_id",
        "order_date",
        "product_name",
        "quantity",
        "producer_name",
        "price_per_unit",
        "line_total",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"orders_dataset.csv is missing columns: {missing}")

    if "user_id" in df.columns:
        user_col = "user_id"
    elif "username" in df.columns:
        user_col = "username"
    else:
        raise ValueError("orders_dataset.csv must contain either 'user_id' or 'username'.")

    df = df.copy()
    df["user_key"] = df[user_col].astype(str)
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df["product_name"] = df["product_name"].astype(str).str.strip()
    df["producer_name"] = df["producer_name"].fillna("unknown").astype(str).str.strip()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df["price_per_unit"] = pd.to_numeric(df["price_per_unit"], errors="coerce").fillna(0.0)
    df["line_total"] = pd.to_numeric(df["line_total"], errors="coerce").fillna(0.0)

    if "category" not in df.columns:
        df["category"] = "unknown"
    else:
        df["category"] = df["category"].fillna("unknown").astype(str)

    if "order_status" in df.columns:
        df = df[df["order_status"].astype(str).str.lower() == "fulfilled"].copy()

    df = df.dropna(subset=["user_key", "product_name", "order_date"])
    df = df[df["quantity"] > 0].copy()

    return df


# ============================================================
# SVD PART
# ============================================================

def build_user_item_matrix(orders: pd.DataFrame) -> pd.DataFrame:
    matrix = orders.pivot_table(
        index="user_key",
        columns="product_name",
        values="quantity",
        aggfunc="sum",
        fill_value=0
    )
    return matrix


def fit_svd(user_item_matrix: pd.DataFrame) -> Tuple[TruncatedSVD, np.ndarray, np.ndarray]:
    matrix = user_item_matrix.values
    n_users, n_items = matrix.shape

    if n_users < 2 or n_items < 2:
        raise ValueError("Not enough users/items to run SVD.")

    n_components = min(20, n_users - 1, n_items - 1)
    n_components = max(2, n_components)

    svd = TruncatedSVD(n_components=n_components, random_state=RANDOM_STATE)
    user_factors = svd.fit_transform(matrix)
    item_factors = svd.components_.T

    return svd, user_factors, item_factors


def get_svd_score(
    user_key: str,
    product_name: str,
    user_item_matrix: pd.DataFrame,
    user_factors: np.ndarray,
    item_factors: np.ndarray
) -> float:
    if user_key not in user_item_matrix.index:
        return 0.0
    if product_name not in user_item_matrix.columns:
        return 0.0

    user_idx = user_item_matrix.index.get_loc(user_key)
    item_idx = user_item_matrix.columns.get_loc(product_name)
    return float(np.dot(user_factors[user_idx], item_factors[item_idx]))


# ============================================================
# RANDOM FOREST PART
# ============================================================

def build_rf_training_data(orders: pd.DataFrame) -> pd.DataFrame:
    """
    Build user-product features.
    Target = whether the user reordered the same product later.
    """
    df = orders.sort_values(["user_key", "product_name", "order_date", "order_id"]).copy()
    rows = []

    grouped = df.groupby(["user_key", "product_name"], sort=False)

    for (user_key, product_name), g in grouped:
        g = g.sort_values(["order_date", "order_id"]).reset_index(drop=True)

        for i in range(len(g)):
            current = g.iloc[i]
            history = g.iloc[:i]
            future = g.iloc[i + 1:]

            prev_count = len(history)
            prev_qty_sum = history["quantity"].sum() if prev_count > 0 else 0
            prev_avg_qty = history["quantity"].mean() if prev_count > 0 else 0
            days_since_prev = (
                (current["order_date"] - history["order_date"].max()).days
                if prev_count > 0 else 999
            )

            user_history = orders[
                (orders["user_key"] == user_key) &
                (
                    (orders["order_date"] < current["order_date"]) |
                    (
                        (orders["order_date"] == current["order_date"]) &
                        (orders["order_id"] < current["order_id"])
                    )
                )
            ]

            product_history = orders[
                (orders["product_name"] == product_name) &
                (
                    (orders["order_date"] < current["order_date"]) |
                    (
                        (orders["order_date"] == current["order_date"]) &
                        (orders["order_id"] < current["order_id"])
                    )
                )
            ]

            rows.append({
                "user_key": user_key,
                "product_name": product_name,
                "category": current["category"],
                "producer_name": current["producer_name"],
                "price_per_unit": current["price_per_unit"],
                "current_quantity": current["quantity"],
                "prev_count_same_product": prev_count,
                "prev_qty_sum_same_product": prev_qty_sum,
                "prev_avg_qty_same_product": prev_avg_qty,
                "days_since_prev_same_product": days_since_prev,
                "user_total_orders_before": user_history["order_id"].nunique(),
                "user_total_items_before": len(user_history),
                "user_total_qty_before": user_history["quantity"].sum() if len(user_history) > 0 else 0,
                "product_popularity_before": product_history["quantity"].sum() if len(product_history) > 0 else 0,
                "target_reorder_later": 1 if len(future) > 0 else 0
            })

    features = pd.DataFrame(rows)

    if features.empty:
        raise ValueError("RF training data is empty.")

    return features


def encode_rf_features(features: pd.DataFrame):
    features = features.copy()
    encoders = {}

    categorical_cols = ["user_key", "product_name", "category", "producer_name"]

    for col in categorical_cols:
        le = LabelEncoder()
        features[col] = le.fit_transform(features[col].astype(str))
        encoders[col] = le

    return features, encoders


def train_random_forest(features_raw: pd.DataFrame):
    original_pairs = features_raw[["user_key", "product_name"]].copy()

    features_encoded, _ = encode_rf_features(features_raw)

    y = features_encoded["target_reorder_later"].astype(int)
    X = features_encoded.drop(columns=["target_reorder_later"])

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y if y.nunique() > 1 else None
    )

    model = RandomForestClassifier(
        n_estimators=250,
        max_depth=12,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=RANDOM_STATE
    )
    model.fit(X_train, y_train)

    print("\n=== Random Forest Evaluation ===")
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred, digits=4))

    if len(np.unique(y_test)) > 1:
        y_prob = model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, y_prob)
        print(f"ROC-AUC: {auc:.4f}")

    full_prob = model.predict_proba(X)[:, 1]

    prediction_df = original_pairs.copy()
    prediction_df["rf_probability"] = full_prob
    prediction_df["target_reorder_later"] = features_raw["target_reorder_later"].values

    return model, prediction_df


# ============================================================
# BASELINE: BEST-SELLERS / MOST FREQUENTLY ORDERED ITEMS
# ============================================================

def build_bestseller_baseline(orders: pd.DataFrame) -> pd.DataFrame:
    """
    Global best-seller baseline:
    ranks products by total quantity and number of orders.
    This is NOT personalized.
    """
    baseline = (
        orders.groupby("product_name", as_index=False)
        .agg(
            total_qty=("quantity", "sum"),
            total_orders=("order_id", "nunique"),
            category=("category", "last"),
            producer_name=("producer_name", "last"),
            last_order_date=("order_date", "max")
        )
        .sort_values(["total_qty", "total_orders"], ascending=[False, False])
        .reset_index(drop=True)
    )

    baseline["bestseller_rank"] = np.arange(1, len(baseline) + 1)
    return baseline


def recommend_bestsellers_for_user(
    user_key: str,
    artifacts: HybridArtifacts,
    top_n: int = TOP_N
) -> pd.DataFrame:
    """
    Same best-seller list for every user.
    Used only as a baseline for comparison.
    """
    baseline = artifacts.bestseller_baseline.head(top_n).copy()
    baseline.insert(0, "user_key", str(user_key))
    return baseline[
        [
            "user_key",
            "product_name",
            "category",
            "producer_name",
            "total_qty",
            "total_orders",
            "last_order_date",
            "bestseller_rank"
        ]
    ]


# ============================================================
# HYBRID SCORING
# ============================================================

def min_max_scale(series: pd.Series) -> pd.Series:
    series = series.astype(float)
    min_v = series.min()
    max_v = series.max()

    if max_v - min_v == 0:
        return pd.Series(np.zeros(len(series)), index=series.index)

    return (series - min_v) / (max_v - min_v)


def build_candidate_recommendations(
    orders: pd.DataFrame,
    user_item_matrix: pd.DataFrame,
    user_factors: np.ndarray,
    item_factors: np.ndarray,
    rf_predictions: pd.DataFrame,
    alpha: float = ALPHA,
    beta: float = BETA
) -> pd.DataFrame:
    """
    Recommend from products the user has already bought.
    This matches 'quick re-order' best.
    """
    history = (
        orders.groupby(["user_key", "product_name"], as_index=False)
        .agg(
            total_qty=("quantity", "sum"),
            total_orders=("order_id", "nunique"),
            last_order_date=("order_date", "max"),
            category=("category", "last"),
            producer_name=("producer_name", "last")
        )
    )

    latest_rf = (
        rf_predictions
        .groupby(["user_key", "product_name"], as_index=False)["rf_probability"]
        .max()
    )

    merged = history.merge(
        latest_rf,
        on=["user_key", "product_name"],
        how="left"
    )
    merged["rf_probability"] = merged["rf_probability"].fillna(0.0)

    merged["svd_score_raw"] = merged.apply(
        lambda row: get_svd_score(
            row["user_key"],
            row["product_name"],
            user_item_matrix,
            user_factors,
            item_factors
        ),
        axis=1
    )

    merged["svd_score"] = min_max_scale(merged["svd_score_raw"])
    merged["rf_score"] = min_max_scale(merged["rf_probability"])

    # Explicit frequency signal for Task 1 wording
    merged["frequency_score"] = min_max_scale(merged["total_orders"])

    # Hybrid final score
    merged["final_score"] = (
        alpha * merged["svd_score"] +
        beta * merged["rf_score"]
    )

    return merged.sort_values(["user_key", "final_score"], ascending=[True, False]).reset_index(drop=True)


# ============================================================
# TRAIN PIPELINE
# ============================================================

def train_hybrid_model() -> HybridArtifacts:
    check_files()
    orders = load_orders()

    user_item_matrix = build_user_item_matrix(orders)
    svd_model, user_factors, item_factors = fit_svd(user_item_matrix)

    rf_features = build_rf_training_data(orders)
    rf_model, rf_predictions = train_random_forest(rf_features)

    product_popularity = (
        orders.groupby("product_name")["quantity"]
        .sum()
        .sort_values(ascending=False)
    )

    bestseller_baseline = build_bestseller_baseline(orders)

    return HybridArtifacts(
        orders=orders,
        user_item_matrix=user_item_matrix,
        svd_model=svd_model,
        user_factors=user_factors,
        item_factors=item_factors,
        rf_model=rf_model,
        rf_predictions=rf_predictions,
        product_popularity=product_popularity,
        bestseller_baseline=bestseller_baseline
    )


# ============================================================
# RECOMMENDATION FUNCTIONS
# ============================================================

def recommend_for_user(
    user_key: str,
    artifacts: HybridArtifacts,
    top_n: int = TOP_N,
    alpha: float = ALPHA,
    beta: float = BETA
) -> pd.DataFrame:
    all_scores = build_candidate_recommendations(
        artifacts.orders,
        artifacts.user_item_matrix,
        artifacts.user_factors,
        artifacts.item_factors,
        artifacts.rf_predictions,
        alpha=alpha,
        beta=beta
    )

    user_scores = all_scores[all_scores["user_key"] == str(user_key)].copy()

    if user_scores.empty:
        fallback = artifacts.product_popularity.head(top_n).reset_index()
        fallback.columns = ["product_name", "total_qty"]
        fallback["note"] = "Cold-start fallback: globally popular products"
        return fallback

    return user_scores.head(top_n)[[
        "user_key",
        "product_name",
        "category",
        "producer_name",
        "total_qty",
        "total_orders",
        "last_order_date",
        "frequency_score",
        "svd_score",
        "rf_score",
        "final_score"
    ]]


def recommend_for_all_users(
    artifacts: HybridArtifacts,
    top_n: int = TOP_N,
    alpha: float = ALPHA,
    beta: float = BETA
) -> pd.DataFrame:
    all_scores = build_candidate_recommendations(
        artifacts.orders,
        artifacts.user_item_matrix,
        artifacts.user_factors,
        artifacts.item_factors,
        artifacts.rf_predictions,
        alpha=alpha,
        beta=beta
    )

    recs = (
        all_scores
        .sort_values(["user_key", "final_score"], ascending=[True, False])
        .groupby("user_key", as_index=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    return recs[[
        "user_key",
        "product_name",
        "category",
        "producer_name",
        "total_qty",
        "total_orders",
        "last_order_date",
        "frequency_score",
        "svd_score",
        "rf_score",
        "final_score"
    ]]


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("Bristol Regional Food Network — Hybrid Recommender")
    print("=" * 60)

    artifacts = train_hybrid_model()

    all_recommendations = recommend_for_all_users(artifacts, top_n=TOP_N)

    output_csv = os.path.join(BASE_DIR, "hybrid_recommendations.csv")
    output_json = os.path.join(BASE_DIR, "hybrid_model_summary.json")
    output_baseline_csv = os.path.join(BASE_DIR, "bestseller_recommendations.csv")

    all_recommendations.to_csv(output_csv, index=False)
    artifacts.bestseller_baseline.to_csv(output_baseline_csv, index=False)

    summary = {
        "orders_rows": int(len(artifacts.orders)),
        "users": int(artifacts.orders["user_key"].nunique()),
        "products": int(artifacts.orders["product_name"].nunique()),
        "alpha": ALPHA,
        "beta": BETA,
        "top_n": TOP_N,
        "data_folder": DATA_DIR
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\nSaved hybrid recommendations to: {output_csv}")
    print(f"Saved best-seller baseline to: {output_baseline_csv}")
    print(f"Saved summary to: {output_json}")

    sample_user = artifacts.orders["user_key"].iloc[0]

    print(f"\nTop HYBRID recommendations for user: {sample_user}")
    print(recommend_for_user(sample_user, artifacts, top_n=TOP_N).to_string(index=False))

    print(f"\nTop BEST-SELLER baseline for user: {sample_user}")
    print(recommend_bestsellers_for_user(sample_user, artifacts, top_n=TOP_N).to_string(index=False))

    print("\nDone.")


if __name__ == "__main__":
    main()