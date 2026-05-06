# Bristol Regional Food Network — Intelligent Ordering System

## Overview

This project is the AI/ML component of a coursework assignment for the **Advanced AI** module (Case Study 2025–26). The task was to design and implement an AI-based solution for a fictional digital marketplace called the **Bristol Regional Food Network** — a platform connecting local food producers with consumers, schools, restaurants, and community groups within 20 miles of Bristol city centre.

The specific component built here is the **Intelligent Ordering System**: a machine learning model that analyses customer purchase history and predicts which product a user is most likely to order next, enabling quick re-order suggestions and a personalised shopping experience.

---

## What Was Built

### 1. Dataset (`orders_dataset.csv`)
A synthetic dataset of approximately **3,000 order line items** from the Bristol food platform. Each record contains:
- Order identifiers: `order_id`, `user_id`, `username`
- Order logistics: `order_date`, `delivery_date`, `order_status`
- Product details: `product_name`, `category`, `section`
- Transaction data: `quantity`, `unit`, `price_per_unit`, `line_total`
- Metadata: `is_organic`, `producer_name`, `city`, `postcode`

---

### 2. Jupyter Notebook (`intelligent_ordering_ml.ipynb`)
The notebook is the main exploratory and evaluation environment. It walks through the full ML pipeline across 8 sections:

| Section | Description |
|---|---|
| 1 | Library imports and setup |
| 2 | Data loading and exploration |
| 3 | Exploratory Data Analysis (EDA) with 6 visualisation charts |
| 4 | Feature engineering (temporal, user-level, encoded categoricals) |
| 5 | Training data preparation — filtered to top 15 products |
| 6 | Training three models: SVM, Random Forest, XGBoost |
| 7 | Evaluation and comparison of all three models |
| 8 | Visualisations: bar charts, confusion matrices, feature importance, radar chart |

**Three models were trained and compared:**

| Model | Key Strength |
|---|---|
| **SVM** (RBF kernel) | Works well in high-dimensional spaces |
| **Random Forest** (200 trees) | Robust, handles non-linearity, interpretable |
| **XGBoost** (gradient boosting) | High accuracy, handles imbalanced data |

**Random Forest was selected as the best model**, achieving ~99% accuracy across all metrics (accuracy, precision, recall, F1 score).

---

### 3. Production Model Script (`random_forest_model.py`)
A standalone Python script that trains the final production-grade Random Forest model. It uses the full dataset (not just top 15 products) and includes:

- **Feature engineering**: temporal features (month, day of week, delivery duration), user-level behavioural aggregates (total orders, average spend, favourite category, organic purchase rate), and label-encoded categoricals.
- **Model training**: Random Forest with 500 estimators, tuned hyperparameters, and `stratify` split for balanced evaluation.
- **Evaluation**: Prints test accuracy and a full classification report.
- **Feature importance**: Ranks all 15 input features by their contribution to predictions.
- **Saved artefacts**: Exports `rf_model.pkl`, `target_encoder.pkl`, and `feature_encoders.pkl` for use in a deployed application.
- **Prediction function** (`recommend_for_user`): Given a `user_id`, returns the top N predicted next products with confidence scores, alongside the user's most historically purchased items.

---

### 4. Saved Model Files
| File | Description |
|---|---|
| `rf_model.pkl` | Trained Random Forest classifier (~78MB) |
| `target_encoder.pkl` | LabelEncoder for product names (target variable) |
| `feature_encoders.pkl` | LabelEncoders for all categorical input features |

These `.pkl` files are loaded at inference time by the application, meaning the model does not need to be retrained on every run.

---

## Feature Engineering Summary

The following features were engineered from the raw dataset and used to train the model:

| Feature | Type | Description |
|---|---|---|
| `price_per_unit` | Numeric | Cost of individual item |
| `quantity` | Numeric | Units ordered |
| `line_total` | Numeric | Total spend on that line |
| `is_organic` | Binary | Whether product is organic (1/0) |
| `delivery_days` | Numeric | Days between order and delivery |
| `month` | Numeric | Month of order (seasonality signal) |
| `dayofweek` | Numeric | Day of week order was placed |
| `total_orders` | Numeric | Total orders this user has made |
| `avg_spend` | Numeric | User's average spend per line item |
| `organic_rate` | Numeric | Proportion of user's orders that are organic |
| `category_enc` | Encoded | Product category |
| `section_enc` | Encoded | Store section |
| `unit_enc` | Encoded | Unit of measurement (kg, each, etc.) |
| `fav_category_enc` | Encoded | User's most frequently ordered category |
| `order_status_enc` | Encoded | Delivery/order status |

---

## How to Run

### Prerequisites
```bash
pip install pandas numpy scikit-learn xgboost joblib matplotlib seaborn
```

### Train and save the production model
```bash
python random_forest_model.py
```

This will:
1. Load `orders_dataset.csv`
2. Engineer all features
3. Train the Random Forest model
4. Print evaluation metrics and feature importances
5. Save `rf_model.pkl`, `target_encoder.pkl`, `feature_encoders.pkl`
6. Output top-3 product recommendations for the first 5 users

### Run the notebook
Open `intelligent_ordering_ml.ipynb` in Jupyter Notebook or JupyterLab and run all cells sequentially to reproduce the full model comparison and visualisations.

---

## Assignment Context

This work addresses the **Customer (End-User)** component of the Bristol Regional Food Network case study, specifically:

> *"The platform should include an intelligent ordering system that streamlines the entire process. This system can analyse purchase history, predict frequently ordered items, and provide quick re-order options to enhance the customer experience."*

The module also required consideration of scalability, explainability, fairness, and monitoring strategy — the feature importance outputs and confidence scores from the model support transparency in how recommendations are derived.

---

## Project Structure

```
AAI---Bristol-Regional-Food-Network/
│
├── intelligent_ordering_ml.ipynb   # Full ML pipeline & model comparison notebook
├── random_forest_model.py          # Production training script
├── orders_dataset.csv              # Synthetic orders dataset (~3,000 records)
├── rf_model.pkl                    # Saved Random Forest model
├── target_encoder.pkl              # Saved product name encoder
└── feature_encoders.pkl            # Saved categorical feature encoders
```
