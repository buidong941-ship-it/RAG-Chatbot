import json
from pathlib import Path


NOTEBOOK_PATH = Path(r"C:\Users\admin\Downloads\pshr2.ipynb")
START_MARKER = "## Preprocessing cho LightGBM"


def markdown_cell(source):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def code_cell(source):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


new_cells = [
    markdown_cell(
        """## Preprocessing cho LightGBM

Pipeline này điền khuyết dữ liệu, tạo feature mới, xử lý outlier cho ratio feature, giữ biến phân loại ở dạng `category` và tách train/validation để dùng với LightGBM."""
    ),
    code_cell(
        r'''# Preprocessing cho LightGBM
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

TARGET = "health_condition"
ID_COL = "id"

base_numeric_cols = [
    "sleep_duration",
    "heart_rate",
    "bmi",
    "calorie_expenditure",
    "step_count",
    "exercise_duration",
    "water_intake",
]

base_categorical_cols = [
    "diet_type",
    "stress_level",
    "sleep_quality",
    "physical_activity_level",
    "smoking_alcohol",
    "gender",
]


def safe_divide(numerator, denominator):
    denominator = denominator.replace(0, np.nan)
    return numerator / denominator


def add_health_features(df):
    df = df.copy()

    df["bmi_category"] = pd.cut(
        df["bmi"],
        bins=[-np.inf, 18.5, 25, 30, np.inf],
        labels=["underweight", "normal", "overweight", "obese"]
    )

    df["sleep_deviation_from_ideal"] = (df["sleep_duration"] - 8).abs()
    df["sleep_deficit"] = (7 - df["sleep_duration"]).clip(lower=0)
    df["sleep_excess"] = (df["sleep_duration"] - 9).clip(lower=0)
    df["is_low_sleep"] = (df["sleep_duration"] < 6).astype("int8")

    df["steps_per_exercise_min"] = safe_divide(df["step_count"], df["exercise_duration"])
    df["exercise_min_per_1000_steps"] = safe_divide(df["exercise_duration"], df["step_count"]) * 1000
    df["calories_per_1000_steps"] = safe_divide(df["calorie_expenditure"], df["step_count"]) * 1000
    df["calories_per_exercise_min"] = safe_divide(df["calorie_expenditure"], df["exercise_duration"])

    df["hydration_gap_from_2l"] = df["water_intake"] - 2.0
    df["hydration_per_bmi"] = safe_divide(df["water_intake"], df["bmi"])
    df["is_low_water"] = (df["water_intake"] < 1.5).astype("int8")

    stress_map = {"low": 0, "medium": 1, "high": 2, "unknown": -1}
    sleep_quality_map = {"poor": 0, "average": 1, "good": 2, "unknown": -1}
    activity_map = {"sedentary": 0, "moderate": 1, "active": 2, "unknown": -1}
    smoking_map = {"no": 0, "occasional": 1, "yes": 2, "unknown": -1}

    df["stress_score"] = df["stress_level"].map(stress_map).astype("int8")
    df["sleep_quality_score"] = df["sleep_quality"].map(sleep_quality_map).astype("int8")
    df["activity_score"] = df["physical_activity_level"].map(activity_map).astype("int8")
    df["smoking_alcohol_score"] = df["smoking_alcohol"].map(smoking_map).astype("int8")

    df["is_high_stress"] = (df["stress_level"] == "high").astype("int8")
    df["is_poor_sleep_quality"] = (df["sleep_quality"] == "poor").astype("int8")
    df["is_sedentary"] = (df["physical_activity_level"] == "sedentary").astype("int8")
    df["uses_smoking_alcohol"] = df["smoking_alcohol"].isin(["yes", "occasional"]).astype("int8")

    df["lifestyle_risk_score"] = (
        df["is_low_sleep"]
        + df["is_low_water"]
        + df["is_high_stress"]
        + df["is_poor_sleep_quality"]
        + df["is_sedentary"]
        + df["uses_smoking_alcohol"]
    ).astype("int8")

    return df


def preprocess_for_lgbm(df, numeric_fill_values=None, category_levels=None, clip_values=None, is_train=True):
    df = df.copy()

    # 1. Missing indicators: giúp model học pattern bị thiếu dữ liệu.
    for col in base_numeric_cols + base_categorical_cols:
        df[f"{col}_was_missing"] = df[col].isna().astype("int8")

    # 2. Điền khuyết numeric bằng median lấy từ train.
    if is_train:
        numeric_fill_values = df[base_numeric_cols].median()

    for col in base_numeric_cols:
        df[col] = df[col].fillna(numeric_fill_values[col])

    # 3. Điền khuyết categorical bằng unknown.
    for col in base_categorical_cols:
        df[col] = df[col].fillna("unknown")

    # 4. Feature engineering sau khi đã xử lý missing ở feature gốc.
    df = add_health_features(df)

    categorical_cols = base_categorical_cols + ["bmi_category"]

    # 5. Đồng bộ category giữa train/test để LightGBM đọc ổn định.
    if is_train:
        category_levels = {}
        for col in categorical_cols:
            df[col] = df[col].astype("category")
            if "unknown" not in df[col].cat.categories:
                df[col] = df[col].cat.add_categories(["unknown"])
            df[col] = df[col].fillna("unknown")
            category_levels[col] = list(df[col].cat.categories)
    else:
        for col in categorical_cols:
            if col == "bmi_category":
                df[col] = df[col].astype("object").fillna("unknown")
            df[col] = pd.Categorical(df[col], categories=category_levels[col])

    # 6. Ratio features có outlier lớn, clip theo percentile 99 của train.
    ratio_cols = [
        "steps_per_exercise_min",
        "exercise_min_per_1000_steps",
        "calories_per_1000_steps",
        "calories_per_exercise_min",
        "hydration_per_bmi",
    ]

    if is_train:
        clip_values = df[ratio_cols].quantile(0.99)

    for col in ratio_cols:
        df[col] = df[col].clip(upper=clip_values[col])

    return df, numeric_fill_values, category_levels, clip_values


df_lgbm, numeric_fill_values, category_levels, clip_values = preprocess_for_lgbm(
    train_df,
    is_train=True
)

feature_cols = [
    col for col in df_lgbm.columns
    if col not in [ID_COL, TARGET]
]

categorical_features = [
    col for col in base_categorical_cols + ["bmi_category"]
    if col in feature_cols
]

label_encoder = LabelEncoder()
y = label_encoder.fit_transform(df_lgbm[TARGET])
X = df_lgbm[feature_cols]

X_train, X_valid, y_train, y_valid = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print("Shape X_train:", X_train.shape)
print("Shape X_valid:", X_valid.shape)
print("Categorical features:", categorical_features)
print("Target mapping:", dict(zip(label_encoder.classes_, label_encoder.transform(label_encoder.classes_))))

display(X_train.head())'''
    ),
    code_cell(
        r'''# Kiểm tra sau preprocessing
missing_after_preprocessing = X_train.isna().sum().sort_values(ascending=False)

print("--- Cột còn thiếu sau preprocessing ---")
display(missing_after_preprocessing[missing_after_preprocessing > 0])

print("--- Kiểu dữ liệu sau preprocessing ---")
display(X_train.dtypes.value_counts())

print("--- Phân bố target trong train/valid ---")
display(pd.Series(label_encoder.inverse_transform(y_train)).value_counts(normalize=True).mul(100).round(2))
display(pd.Series(label_encoder.inverse_transform(y_valid)).value_counts(normalize=True).mul(100).round(2))'''
    ),
    code_cell(
        r'''# Nếu có test.csv, dùng lại các giá trị preprocessing đã fit từ train.
# test_df = pd.read_csv("/kaggle/input/datasets/midzed/predicting-student-health-risk-data/test.csv")
#
# test_lgbm, _, _, _ = preprocess_for_lgbm(
#     test_df,
#     numeric_fill_values=numeric_fill_values,
#     category_levels=category_levels,
#     clip_values=clip_values,
#     is_train=False
# )
#
# X_test = test_lgbm[feature_cols]
# display(X_test.head())'''
    ),
]


nb = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))

first_added_cell = None
for index, cell in enumerate(nb["cells"]):
    source = "".join(cell.get("source", []))
    if source.startswith(START_MARKER):
        first_added_cell = index
        break

if first_added_cell is not None:
    nb["cells"] = nb["cells"][:first_added_cell]

nb["cells"].extend(new_cells)
NOTEBOOK_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")

print(f"Added {len(new_cells)} LightGBM preprocessing cells to {NOTEBOOK_PATH}")
