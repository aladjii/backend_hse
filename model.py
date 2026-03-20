import logging
import os
import pickle

import numpy as np
from sklearn.linear_model import LogisticRegression

logger = logging.getLogger("model")

MODEL_PATH = "model.pkl"
MODEL_SOURCE = os.getenv("MODEL_SOURCE", "local")  # "local" or "mlflow"
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")
MLFLOW_MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "ad_moderation_model")
MLFLOW_MODEL_STAGE = os.getenv("MLFLOW_MODEL_STAGE", "Production")


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


def _load_from_mlflow() -> LogisticRegression:
    import mlflow

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    model_uri = f"models:/{MLFLOW_MODEL_NAME}/{MLFLOW_MODEL_STAGE}"
    logger.info("Loading model from MLflow: %s", model_uri)
    return mlflow.sklearn.load_model(model_uri)


def register_model_in_mlflow(model: LogisticRegression) -> None:
    """Train and register model in MLflow (called once or from a script)."""
    import mlflow
    import mlflow.sklearn

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("ad_moderation")

    with mlflow.start_run(run_name="logistic_regression"):
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name=MLFLOW_MODEL_NAME,
        )
        mlflow.log_param("solver", "lbfgs")
        mlflow.log_param("seed", 42)
    logger.info("Model registered in MLflow as '%s'", MLFLOW_MODEL_NAME)


def get_or_create_model(path: str = MODEL_PATH) -> LogisticRegression:
    if MODEL_SOURCE == "mlflow":
        try:
            return _load_from_mlflow()
        except Exception as e:
            logger.warning("MLflow load failed (%s), falling back to local", e)

    if os.path.exists(path):
        try:
            return load_model(path)
        except Exception:
            pass

    model = train_model()
    save_model(model, path)
    return model
