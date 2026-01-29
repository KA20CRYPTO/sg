import pandas as pd
import numpy as np
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from pathlib import Path
import time

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
DATA_PATH = "synthetic_role_training_data_big.csv"   # your dataset path
MODEL_OUT = "role_model.pkl"
VECT_OUT = "role_vectorizer.pkl"
REPORT_OUT = "role_training_report.txt"
PRED_OUT = "role_predictions.csv"

# --------------------------------------------------
# LOAD DATASET
# --------------------------------------------------
print("Loading dataset...")
df = pd.read_csv(DATA_PATH)
df = df.dropna().reset_index(drop=True)

print(f"Loaded {len(df)} samples")
print(df.head())

# --------------------------------------------------
# TRAIN / TEST SPLIT
# --------------------------------------------------
X = df["resume_text"].astype(str)
y = df["role"].astype(str)

print("Splitting data...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

# --------------------------------------------------
# TF-IDF VECTORIZER
# --------------------------------------------------
print("Vectorizing text...")
vectorizer = TfidfVectorizer(
    stop_words="english",
    max_features=25000,
    ngram_range=(1, 2)
)

X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

print(f"Vectorized: {X_train_vec.shape[0]} samples, {X_train_vec.shape[1]} features")

# --------------------------------------------------
# TRAIN MODEL
# --------------------------------------------------
print("\nTraining Logistic Regression model...")
start = time.time()

model = LogisticRegression(
    max_iter=500,
    solver='saga',
    n_jobs=-1
)

model.fit(X_train_vec, y_train)
end = time.time()

train_time = round(end - start, 3)
print(f"Training completed in {train_time} seconds.")

# --------------------------------------------------
# EVALUATE
# --------------------------------------------------
print("\nEvaluating model...")
y_pred = model.predict(X_test_vec)
acc = accuracy_score(y_test, y_pred)
print(f"Accuracy: {acc}")

report = classification_report(y_test, y_pred, digits=4)
print(report)

# --------------------------------------------------
# SAVE MODEL & VECTORIZER
# --------------------------------------------------
print("Saving model and vectorizer...")
with open(MODEL_OUT, "wb") as f:
    pickle.dump(model, f)
with open(VECT_OUT, "wb") as f:
    pickle.dump(vectorizer, f)

# --------------------------------------------------
# SAVE REPORT
# --------------------------------------------------
with open(REPORT_OUT, "w") as f:
    f.write(f"Training Time: {train_time} seconds\n")
    f.write(f"Accuracy: {acc}\n\n")
    f.write("Classification Report:\n")
    f.write(report)

# --------------------------------------------------
# SAVE PREDICTION SAMPLES
# --------------------------------------------------
probs = model.predict_proba(X_test_vec)
confidence = probs.max(axis=1)

pred_df = pd.DataFrame({
    "resume_text": X_test.values,
    "true_role": y_test.values,
    "pred_role": y_pred,
    "confidence": confidence
})

pred_df.to_csv(PRED_OUT, index=False)

# --------------------------------------------------
# FINAL OUTPUT
# --------------------------------------------------
print("\n🎉 TRAINING COMPLETE!")
print("Model saved as:", MODEL_OUT)
print("Vectorizer saved as:", VECT_OUT)
print("Test predictions:", PRED_OUT)
print("Training report:", REPORT_OUT)
