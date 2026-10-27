import pandas as pd
import joblib

print("===================================")
print("FAKE NEWS DETECTOR - 20 ARTICLE TEST")
print("===================================")

# Load trained model
model = joblib.load("model/fake_news_model.pkl")

# Load dataset
data = pd.read_csv("dataset/final_news.csv")
data = data.dropna(subset=["text", "label"])

print("Dataset loaded successfully!")
print("Total articles:", len(data))


# ===================================
# SEPARATE FAKE AND REAL NEWS
# ===================================

fake_data = data[
    data["label"].astype(str).str.upper() == "FAKE"
]

real_data = data[
    data["label"].astype(str).str.upper() == "REAL"
]


# Take 10 articles from each class
fake_articles = fake_data.head(10)
real_articles = real_data.head(10)


# ===================================
# TEST FUNCTION
# ===================================

def test_articles(article_data, actual_label):

    correct = 0
    total = len(article_data)

    print("\n===================================")
    print("TESTING", actual_label, "NEWS")
    print("===================================")

    for i, article in enumerate(article_data["text"], start=1):

        prediction = model.predict([str(article)])[0]

        probabilities = model.predict_proba([str(article)])[0]

        confidence = max(probabilities) * 100

        if prediction == actual_label:
            correct += 1
            result = "CORRECT"
        else:
            result = "INCORRECT"

        print(
            f"Article {i:02d} | "
            f"Actual: {actual_label} | "
            f"Prediction: {prediction} | "
            f"Confidence: {confidence:.2f}% | "
            f"{result}"
        )

    accuracy = (correct / total) * 100

    print("\n-----------------------------------")
    print("Correct:", correct, "/", total)
    print("Accuracy:", f"{accuracy:.2f}%")
    print("-----------------------------------")

    return correct, total


# ===================================
# RUN FAKE TEST
# ===================================

fake_correct, fake_total = test_articles(
    fake_articles,
    "FAKE"
)


# ===================================
# RUN REAL TEST
# ===================================

real_correct, real_total = test_articles(
    real_articles,
    "REAL"
)


# ===================================
# OVERALL RESULT
# ===================================

total_correct = fake_correct + real_correct
total_articles = fake_total + real_total

overall_accuracy = (total_correct / total_articles) * 100

print("\n===================================")
print("FINAL TEST RESULT")
print("===================================")

print("Total Articles Tested:", total_articles)
print("Correct Predictions   :", total_correct)
print("Wrong Predictions     :", total_articles - total_correct)

print("Overall Accuracy      :", f"{overall_accuracy:.2f}%")

print("===================================")
print("ALL TESTS COMPLETED")
print("===================================")