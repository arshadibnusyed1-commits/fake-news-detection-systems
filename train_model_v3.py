import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

print("===================================")
print("   FAKE NEWS DETECTOR - MODEL V3")
print("===================================")

print("\nLoading dataset...")

data = pd.read_csv("dataset/final_news.csv")

data = data.dropna(subset=["text", "label"])

data["text"] = data["text"].astype(str)
data["label"] = data["label"].astype(str).str.upper().str.strip()

print("Dataset loaded successfully!")
print("Total articles:", len(data))

print("\nLabel distribution:")
print(data["label"].value_counts())

X = data["text"]
y = data["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("\nTraining articles:", len(X_train))
print("Testing articles:", len(X_test))

model = Pipeline([
    (
        "tfidf",
        TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            max_features=50000,
            sublinear_tf=True,
            min_df=1
        )
    ),
    (
        "classifier",
        LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            C=1.5
        )
    )
])

print("\nTraining Model V3...")
model.fit(X_train, y_train)

print("Training completed!")

print("\nTesting model...")

predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print("\n===================================")
print("       MODEL V3 EVALUATION")
print("===================================")

print("Accuracy:", f"{accuracy * 100:.2f}%")

print("\nConfusion Matrix:")

cm = confusion_matrix(
    y_test,
    predictions,
    labels=["FAKE", "REAL"]
)

print("             Predicted")
print("             FAKE    REAL")
print(f"Actual FAKE  {cm[0][0]:5d}  {cm[0][1]:5d}")
print(f"Actual REAL  {cm[1][0]:5d}  {cm[1][1]:5d}")

print("\nClassification Report:")

print(
    classification_report(
        y_test,
        predictions,
        labels=["FAKE", "REAL"],
        zero_division=0
    )
)

joblib.dump(
    model,
    "model/fake_news_model_v3.pkl"
)

print("===================================")
print("MODEL V3 SAVED SUCCESSFULLY!")
print("Location: model/fake_news_model_v3.pkl")
print("===================================")