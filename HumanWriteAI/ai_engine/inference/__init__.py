"""
Inference module for the AI text detection model.
"""

from ai_engine.inference.predict import predict_text, predict_batch, unload_model, model_status

__all__ = ["predict_text", "predict_batch", "unload_model", "model_status"]