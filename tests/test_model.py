import os
import tempfile

import numpy as np

from model import get_or_create_model, load_model, save_model, train_model


class TestTrainModel:
    def test_returns_fitted_model(self):
        model = train_model()
        X = np.array([[0.1, 0.1, 0.5, 0.5]])
        proba = model.predict_proba(X)
        assert proba.shape == (1, 2)
        assert 0.0 <= proba[0][1] <= 1.0

    def test_predicts_violation_for_unverified_low_images(self):
        model = train_model()
        X_violation = np.array([[0.1, 0.1, 0.5, 0.5]])
        X_normal = np.array([[0.9, 0.9, 0.5, 0.5]])
        p_viol = model.predict_proba(X_violation)[0][1]
        p_norm = model.predict_proba(X_normal)[0][1]
        assert p_viol > p_norm

    def test_deterministic_with_same_seed(self):
        m1 = train_model()
        m2 = train_model()
        X = np.array([[0.5, 0.5, 0.5, 0.5]])
        assert m1.predict_proba(X)[0][1] == m2.predict_proba(X)[0][1]


class TestSaveLoadModel:
    def test_save_and_load_roundtrip(self):
        model = train_model()
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            path = f.name
        try:
            save_model(model, path)
            loaded = load_model(path)
            X = np.array([[0.3, 0.4, 0.5, 0.6]])
            np.testing.assert_array_equal(
                model.predict_proba(X), loaded.predict_proba(X)
            )
        finally:
            os.unlink(path)


class TestGetOrCreateModel:
    def test_creates_model_if_missing(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "model.pkl")
            model = get_or_create_model(path)
            assert os.path.exists(path)
            assert model is not None

    def test_loads_existing_model(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "model.pkl")
            m1 = get_or_create_model(path)
            m2 = get_or_create_model(path)
            X = np.array([[0.5, 0.5, 0.5, 0.5]])
            assert m1.predict_proba(X)[0][1] == m2.predict_proba(X)[0][1]
