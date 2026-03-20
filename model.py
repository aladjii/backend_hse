import os
import pickle

import numpy as np
from sklearn.linear_model import LogisticRegression

MODEL_PATH = "model.pkl"


def train_model() -> LogisticRegression:
    np.random.seed(42)
    X = np.random.rand(1000, 4)
    y = ((X[:, 0] < 0.3) & (X[:, 1] < 0.2)).astype(int)
    model = LogisticRegression()
    model.fit(X, y)
    return model


def save_model(model: LogisticRegression, path: str = MODEL_PATH) -> None:
    with open(path, "wb") as f:
        pickle.dump(model, f)


def load_model(path: str = MODEL_PATH) -> LogisticRegression:
    with open(path, "rb") as f:
        return pickle.load(f)


def get_or_create_model(path: str = MODEL_PATH) -> LogisticRegression:
    if os.path.exists(path):
        try:
            return load_model(path)
        except Exception:
            pass
    model = train_model()
    save_model(model, path)
    return model
