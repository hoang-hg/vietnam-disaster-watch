"""
Train a lightweight second-pass classifier (TF-IDF + LogisticRegression)
Usage:
  python train_light_classifier.py --input logs/labeled_samples.csv --output backend/models/light_classifier.joblib

Input CSV should have columns: text,label (label 1 == disaster, 0 == not disaster)
This is a scaffolding script; install scikit-learn and joblib to run:
  pip install scikit-learn joblib pandas
"""
import argparse
import os
import sys

try:
    import pandas as pd
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report
    import joblib
except Exception as e:
    print("Missing dependencies; install scikit-learn, pandas, joblib: pip install scikit-learn pandas joblib")
    sys.exit(1)


def load_data(path):
    df = pd.read_csv(path)
    if 'text' not in df.columns or 'label' not in df.columns:
        raise ValueError('CSV must include text,label columns')
    return df['text'].astype(str).tolist(), df['label'].astype(int).tolist()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True, help='CSV input with text,label')
    p.add_argument('--output', required=True, help='Output model path (.joblib)')
    args = p.parse_args()

    X, y = load_data(args.input)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    pipe = Pipeline([
        ('tfidf', TfidfVectorizer(max_features=30000, ngram_range=(1,2))),
        ('clf', LogisticRegression(max_iter=1000))
    ])

    pipe.fit(X_train, y_train)

    preds = pipe.predict(X_test)
    print(classification_report(y_test, preds))

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    joblib.dump(pipe, args.output)
    print('Saved model to', args.output)


if __name__ == '__main__':
    main()
