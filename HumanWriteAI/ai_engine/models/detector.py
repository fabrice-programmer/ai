"""
detector.py

Loads the trained AI detection model for inference.

Model: DistilBERT fine-tuned for human vs. AI text classification.
Output: 0 = human, 1 = AI

Usage:
    from ai_engine.models.detector import load_detector
    model, tokenizer = load_detector()
"""

import os
import sys
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# Allow import from training module
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Default paths
DEFAULT_MODEL_DIR = Path(__file__).resolve().parent  # HumanWriteAI/ai_engine/models/
DEFAULT_MODEL_PATH = DEFAULT_MODEL_DIR / "humanwrite_detector.pth"

# Model configuration
MODEL_NAME = "distilbert-base-uncased"
NUM_LABELS = 2  # 0 = human, 1 = AI
MAX_LENGTH = 512


def load_detector(model_path=None, device=None):
    """
    Load the trained AI detection model and its tokenizer.

    Args:
        model_path (str or Path, optional): Path to the saved .pth checkpoint.
            Defaults to ai_engine/models/humanwrite_detector.pth.
        device (torch.device, optional): Device to load the model on.
            Defaults to CUDA if available, otherwise CPU.

    Returns:
        tuple: (model, tokenizer)
            - model (AutoModelForSequenceClassification): The trained model.
            - tokenizer (AutoTokenizer): The corresponding tokenizer.

    Raises:
        FileNotFoundError: If the model file does not exist.
    """
    if model_path is None:
        model_path = DEFAULT_MODEL_PATH
    else:
        model_path = Path(model_path)

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Check if trained model exists
    if not model_path.exists():
        raise FileNotFoundError(
            f"Trained model not found at: {model_path}\n"
            f"  Train the model first with: python -m ai_engine.training.train"
        )

    print(f"Loading trained model from: {model_path}")
    checkpoint = torch.load(model_path, map_location=device)

    # Get saved config or use defaults
    saved_config = checkpoint.get("config", {})
    model_name = saved_config.get("model_name", MODEL_NAME)
    num_labels = saved_config.get("num_labels", NUM_LABELS)

    # Load model architecture and weights
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=num_labels,
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    # Load tokenizer (prefer saved local copy, fall back to pretrained)
    if (model_path.parent / "tokenizer_config.json").exists():
        tokenizer = AutoTokenizer.from_pretrained(str(model_path.parent))
    else:
        tokenizer = AutoTokenizer.from_pretrained(model_name)

    # Store metadata
    metadata = checkpoint.get("metadata", {})
    is_best = metadata.get("is_best", False)

    print(f"  Model:     {model_name}")
    print(f"  Labels:    {num_labels} (0=human, 1=AI)")
    print(f"  Device:    {device}")
    print(f"  Best:      {is_best}")

    return model, tokenizer


def load_detector_safe(model_path=None, device=None):
    """
    Load the trained model, returning None if not found (no exception).

    Args:
        model_path (str or Path, optional): Path to the .pth checkpoint.
        device (torch.device, optional): Device to load the model on.

    Returns:
        tuple: (model, tokenizer) or (None, None) if model not found.
    """
    try:
        return load_detector(model_path=model_path, device=device)
    except FileNotFoundError as e:
        print(f"Warning: {e}")
        return None, None
    except Exception as e:
        print(f"Error loading detector: {e}")
        return None, None


if __name__ == "__main__":
    # Quick test
    try:
        model, tokenizer = load_detector()
        print(f"\nModel loaded successfully!")
        print(f"  Parameters: {sum(p.numel() for p in model.parameters()):,}")

        # Test with a sample text
        test_text = "This is a test sentence to verify the model works."
        inputs = tokenizer(
            test_text,
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
        )
        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)
            pred = torch.argmax(outputs.logits, dim=-1).item()

        label = "human" if pred == 0 else "AI"
        confidence = probs[0][pred].item()
        print(f"  Test prediction: {label} (confidence: {confidence:.4f})")

    except FileNotFoundError:
        print("Model not trained yet. Run training first.")
    except Exception as e:
        print(f"Error: {e}")
