import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report


print("Loading dataset...")

data = pd.read_csv("dataset/final_news.csv")

print("Dataset loaded successfully!")
print("Total articles:", len(data))


# Prepare data
data = data.dropna(subset=["text", "label"])

X = data["text"].astype(str)
y = data["label"].astype(str)


# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("\nTraining articles:", len(X_train))
print("Testing articles:", len(X_test))


# Create ML pipeline
model = Pipeline([
    (
        "tfidf",
        TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            max_features=100000
        )
    ),
    (
        "classifier",
        LogisticRegression(
            max_iter=1000
        )
    )
])


# Train model
print("\nTraining model...")
model.fit(X_train, y_train)

print("Training completed!")


# Prediction
predictions = model.predict(X_test)


# Accuracy
accuracy = accuracy_score(y_test, predictions)

print("\n===================================")
print("MODEL EVALUATION")
print("===================================")

print("Accuracy:", f"{accuracy * 100:.2f}%")

print("\nClassification Report:")
print(classification_report(
    y_test,
    predictions,
    zero_division=0
))


# Save model
joblib.dump(
    model,
    "model/fake_news_model.pkl"
)

print("===================================")
print("Model saved successfully!")
print("Location: model/fake_news_model.pkl")
print("===================================")