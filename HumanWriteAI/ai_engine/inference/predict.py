"""
predict.py

Inference module for AI text detection.

Uses the trained DistilBERT model to classify text as human-written or AI-generated.
Optimized for API usage with lazy model loading and global caching.

Output classes:
    0 = human
    1 = AI

Return format:
    {
        "ai_probability": float,
        "human_probability": float,
        "classification": "human" | "AI",
        "confidence": float
    }

Usage:
    from ai_engine.inference.predict import predict_text

    result = predict_text("Your text here")
    print(result["classification"])  # "human" or "AI"
    print(result["confidence"])      # e.g. 0.9876
"""

import os
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

# Allow imports from sibling modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai_engine.models.detector import load_detector_safe, MAX_LENGTH

# ---------------------------------------------------------------------------
# Global model cache (load once, reuse across API calls)
# ---------------------------------------------------------------------------
_model = None
_tokenizer = None


def _ensure_model_loaded():
    """
    Lazy-load the trained model and cache it globally.

    The model is loaded once on the first call and reused for all subsequent
    predictions, which is optimal for API usage where multiple requests
    share the same process.

    Raises:
        RuntimeError: If the trained model file is not found.
    """
    global _model, _tokenizer

    if _model is not None and _tokenizer is not None:
        return  # Already loaded

    _model, _tokenizer = load_detector_safe()

    if _model is None:
        raise RuntimeError(
            "Trained model not found. Train the model first:\n"
            "  python -m ai_engine.training.train"
        )


def predict_text(text):
    """
    Predict whether a given text is human-written or AI-generated.

    Automatically loads the saved trained model on first call (lazy loading)
    and caches it for subsequent calls, making it optimal for API usage.

    Args:
        text (str): The input text to classify.

    Returns:
        dict: Result with keys:
            - "ai_probability" (float): Probability that text is AI-generated (0-1).
            - "human_probability" (float): Probability that text is human-written (0-1).
            - "classification" (str): "human" or "AI".
            - "confidence" (float): Confidence score of the predicted class (0-1).
    """
    # Ensure model is loaded (lazy load on first call)
    _ensure_model_loaded()

    # Validate input
    if not text or not isinstance(text, str):
        return _error_result("Invalid input: text must be a non-empty string")

    # Preprocess: strip whitespace
    text = text.strip()
    if len(text) == 0:
        return _error_result("Invalid input: text is empty after stripping")

    # Tokenize and predict
    with torch.no_grad():
        inputs = _tokenizer(
            [text],
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
        )
        inputs = {k: v.to(_model.device) for k, v in inputs.items()}

        outputs = _model(**inputs)
        logits = outputs.logits
        probs = F.softmax(logits, dim=-1)

        # probs[0][0] = human probability, probs[0][1] = AI probability
        human_prob = probs[0][0].item()
        ai_prob = probs[0][1].item()

        pred = torch.argmax(logits, dim=-1).item()
        confidence = probs[0][pred].item()

    # Build result in the exact required format
    label_map = {0: "human", 1: "AI"}
    result = {
        "ai_probability": round(ai_prob, 6),
        "human_probability": round(human_prob, 6),
        "classification": label_map[pred],
        "confidence": round(confidence, 6),
    }

    return result


def _error_result(error_message):
    """Return a standardized error result."""
    return {
        "ai_probability": 0.0,
        "human_probability": 0.0,
        "classification": "error",
        "confidence": 0.0,
    }


def predict_batch(texts):
    """
    Predict labels for a batch of texts. Optimized for API batch endpoints.

    Args:
        texts (list of str): List of input texts.

    Returns:
        list of dict: Prediction results for each text, each in the same
                      format as predict_text().
    """
    _ensure_model_loaded()

    if not texts:
        return []

    valid_texts = []
    valid_indices = []

    for i, text in enumerate(texts):
        if text and isinstance(text, str) and text.strip():
            valid_texts.append(text.strip())
            valid_indices.append(i)

    if not valid_texts:
        return []

    results = [None] * len(texts)

    with torch.no_grad():
        inputs = _tokenizer(
            valid_texts,
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
        )
        inputs = {k: v.to(_model.device) for k, v in inputs.items()}

        outputs = _model(**inputs)
        logits = outputs.logits
        probs = F.softmax(logits, dim=-1)
        preds = torch.argmax(logits, dim=-1)

    label_map = {0: "human", 1: "AI"}

    for idx, i in enumerate(valid_indices):
        pred = preds[idx].item()
        results[i] = {
            "ai_probability": round(probs[idx][1].item(), 6),
            "human_probability": round(probs[idx][0].item(), 6),
            "classification": label_map[pred],
            "confidence": round(probs[idx][pred].item(), 6),
        }

    # Fill in invalid inputs with error results
    for i in range(len(texts)):
        if results[i] is None:
            results[i] = _error_result("Invalid input")

    return results


def unload_model():
    """
    Unload the model from memory to free GPU/CPU resources.
    Call this when the API server shuts down.
    """
    global _model, _tokenizer
    _model = None
    _tokenizer = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def model_status():
    """
    Check whether the model is loaded and ready for inference.

    Returns:
        dict: Status information including loaded state and device.
    """
    global _model, _tokenizer

    if _model is None:
        return {
            "loaded": False,
            "device": None,
            "message": "Model not loaded. Call predict_text() first.",
        }

    return {
        "loaded": True,
        "device": str(_model.device),
        "parameters": sum(p.numel() for p in _model.parameters()),
    }


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Test with sample texts
    test_texts = [
        "The quick brown fox jumps over the lazy dog near the riverbank.",
        "In accordance with regulatory guidelines, the following procedures must be implemented.",
        "I went to the store and bought some milk and bread for breakfast.",
        "Optimization of algorithmic parameters is essential for maximizing efficiency.",
    ]

    print("=" * 60)
    print("AI DETECTION INFERENCE TEST")
    print("=" * 60)

    for text in test_texts:
        try:
            result = predict_text(text)
            print(f"\n  Text: {text[:80]}...")
            print(f"  Classification: {result['classification'].upper()}")
            print(f"  Confidence:     {result['confidence']:.4f}")
            print(f"  Human Prob:     {result['human_probability']:.4f}")
            print(f"  AI Prob:        {result['ai_probability']:.4f}")
        except RuntimeError as e:
            print(f"\n  Model not trained: {e}")
            break
        except Exception as e:
            print(f"\n  Error: {e}")
            break

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)