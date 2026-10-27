import pandas as pd
import joblib

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    classification_report
)

print("Loading model and test dataset...")

model = joblib.load("model/fake_news_model.pkl")

data = pd.read_csv("dataset/final_news.csv")
data = data.dropna(subset=["text", "label"])

X = data["text"].astype(str)
y = data["label"].astype(str)

# Use the same test split as training
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("Testing model...")

predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)
cm = confusion_matrix(y_test, predictions, labels=["FAKE", "REAL"])

print("\n===================================")
print("MODEL EVALUATION")
print("===================================")

print("Accuracy:", f"{accuracy * 100:.2f}%")

print("\nConfusion Matrix:")
print("                 Predicted")
print("                 FAKE    REAL")
print(f"Actual FAKE      {cm[0][0]:5d}   {cm[0][1]:5d}")
print(f"Actual REAL      {cm[1][0]:5d}   {cm[1][1]:5d}")

print("\nClassification Report:")
print(
    classification_report(
        y_test,
        predictions,
        labels=["FAKE", "REAL"],
        zero_division=0
    )
)

print("===================================")