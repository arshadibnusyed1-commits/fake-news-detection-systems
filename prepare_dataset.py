import pandas as pd

# Load WELFake dataset
df = pd.read_csv("dataset/WELFake_Dataset.csv")

# Remove rows without news text
df = df.dropna(subset=["text"])

# Convert labels
df["label"] = df["label"].map({
    0: "FAKE",
    1: "REAL"
})

# Keep only required columns
df = df[["text", "label"]]

# Remove empty articles
df["text"] = df["text"].astype(str).str.strip()
df = df[df["text"] != ""]

# Save cleaned dataset
df.to_csv("dataset/final_news.csv", index=False)

print("Dataset prepared successfully!")
print("Total articles:", len(df))
print("\nLabel distribution:")
print(df["label"].value_counts())

print("\nSaved as:")
print("dataset/final_news.csv")