import numpy as np
from sklearn.linear_model import LogisticRegression
import pickle
import os

MODEL_PATH = "model.pkl"

def train_model():
    """Обучает простую модель на синтетических данных."""
    np.random.seed(42)
    # Признаки: [is_verified_seller, images_qty, description_length, category]
    X = np.random.rand(1000, 4)
    # Целевая переменная: 1 = нарушение, 0 = нет нарушения
    y = (X[:, 0] < 0.3) & (X[:, 1] < 0.2)
    y = y.astype(int)

    model = LogisticRegression()
    model.fit(X, y)
    return model

def save_model(model, path=MODEL_PATH):
    with open(path, "wb") as f:
        pickle.dump(model, f)

def load_model(path=MODEL_PATH):
    with open(path, "rb") as f:
        return pickle.load(f)

def get_or_create_model(path=MODEL_PATH):
    if os.path.exists(path):
        try:
            return load_model(path)
        except Exception:
            pass

    model = train_model()
    save_model(model, path)
    return model
