"""
evaluate.py

Evaluation script for the trained AI detection model.

Loads a trained DistilBERT model and evaluates it on test data.
Can also be used to evaluate a single piece of text.

Usage:
    python evaluate.py                          # Evaluate on test split
    python evaluate.py --text "Your text here"   # Evaluate a single text
    python evaluate.py --model path/to/model.pth # Use custom model path

Output:
    0 = human
    1 = AI
"""

import os
import sys
import argparse
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from transformers import AutoTokenizer
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

# Allow imports from sibling modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai_engine.training.train import (
    Config,
    TextClassificationDataset,
    tokenize_texts,
    prepare_data,
)
from ai_engine.dataset.dataset_loader import load_combined_dataset
from ai_engine.dataset.dataset_cleaner import clean_and_deduplicate
from ai_engine.dataset.dataset_splitter import split_dataset, to_transformers_format


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_trained_model(model_path=None, device=None):
    """
    Load a trained model from a saved .pth checkpoint.

    Args:
        model_path (str, optional): Path to the .pth file.
            Defaults to Config.MODEL_SAVE_PATH.
        device (torch.device, optional): Device to load the model onto.

    Returns:
        tuple: (model, config_dict, tokenizer)
    """
    if model_path is None:
        model_path = Config.MODEL_SAVE_PATH
    if device is None:
        device = Config.DEVICE

    if not os.path.exists(model_path):
        print(f"❌ Model not found at: {model_path}")
        print("   Train the model first with: python -m ai_engine.training.train")
        return None, None, None

    print(f"Loading model from: {model_path}")
    checkpoint = torch.load(model_path, map_location=device)

    model_config = checkpoint.get("config", {})
    model_name = model_config.get("model_name", Config.MODEL_NAME)
    num_labels = model_config.get("num_labels", Config.NUM_LABELS)

    # Load model architecture
    from transformers import AutoModelForSequenceClassification
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=num_labels,
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    # Load tokenizer (from saved dir or pretrained)
    tokenizer_dir = Path(model_path).parent
    if (tokenizer_dir / "tokenizer_config.json").exists():
        tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_dir))
    else:
        tokenizer = AutoTokenizer.from_pretrained(model_name)

    metadata = checkpoint.get("metadata", {})
    print(f"  Model:     {model_name}")
    print(f"  Labels:    {num_labels} (0=human, 1=AI)")
    print(f"  Device:    {device}")
    print(f"  Best:      {metadata.get('is_best', False)}")

    return model, model_config, tokenizer


# ---------------------------------------------------------------------------
# Evaluation on test dataset
# ---------------------------------------------------------------------------

def evaluate_on_test_set(model, tokenizer, config=None, verbose=True):
    """
    Evaluate the model on the full test set.

    Args:
        model (nn.Module): The trained model.
        tokenizer (AutoTokenizer): The tokenizer.
        config (Config, optional): Configuration object.
        verbose (bool): Whether to print detailed results.

    Returns:
        dict: Dictionary of evaluation metrics.
    """
    if config is None:
        config = Config

    # Prepare test data (reuse the data preparation pipeline)
    _, test_loader, _ = prepare_data(config)

    if len(test_loader) == 0:
        print("❌ Test set is empty. Cannot evaluate.")
        return {}

    model.eval()
    all_preds = []
    all_labels = []
    all_probs = []

    print(f"\n{'=' * 60}")
    print("EVALUATION ON TEST SET")
    print(f"{'=' * 60}")

    with torch.no_grad():
        for batch_idx, batch in enumerate(test_loader):
            input_ids = batch["input_ids"].to(config.DEVICE)
            attention_mask = batch["attention_mask"].to(config.DEVICE)
            labels = batch["labels"].to(config.DEVICE)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
            )
            logits = outputs.logits
            probs = F.softmax(logits, dim=-1)
            preds = torch.argmax(logits, dim=-1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())

            if verbose and (batch_idx + 1) % 10 == 0:
                print(f"  Processed batch {batch_idx + 1}/{len(test_loader)}")

    # Calculate metrics
    accuracy = accuracy_score(all_labels, all_preds)
    precision = precision_score(all_labels, all_preds, average="binary")
    recall = recall_score(all_labels, all_preds, average="binary")
    f1 = f1_score(all_labels, all_preds, average="binary")
    cm = confusion_matrix(all_labels, all_preds)

    if verbose:
        print(f"\n{'─' * 40}")
        print("RESULTS")
        print(f"{'─' * 40}")
        print(f"  Samples evaluated: {len(all_labels)}")
        print(f"  Accuracy:          {accuracy:.4f} ({accuracy * 100:.2f}%)")
        print(f"  Precision:         {precision:.4f} ({precision * 100:.2f}%)")
        print(f"  Recall:            {recall:.4f} ({recall * 100:.2f}%)")
        print(f"  F1 Score:          {f1:.4f} ({f1 * 100:.2f}%)")
        print()
        print("  Confusion Matrix:")
        print(f"                  Predicted")
        print(f"                  Human   AI")
        print(f"  Actual  Human  {cm[0][0]:5d}  {cm[0][1]:5d}")
        print(f"          AI     {cm[1][0]:5d}  {cm[1][1]:5d}")
        print()
        print("  Classification Report:")
        report = classification_report(
            all_labels,
            all_preds,
            target_names=["human (0)", "AI (1)"],
            digits=4,
        )
        print(report)

    # Summary line
    summary = (
        f"Accuracy={accuracy:.4f}, Precision={precision:.4f}, "
        f"Recall={recall:.4f}, F1={f1:.4f}, Samples={len(all_labels)}"
    )
    print(f"  Summary: {summary}")

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "confusion_matrix": cm.tolist(),
        "samples": len(all_labels),
        "predictions": all_preds,
        "true_labels": all_labels,
        "probabilities": all_probs,
    }


# ---------------------------------------------------------------------------
# Single text prediction
# ---------------------------------------------------------------------------

def predict_text(model, tokenizer, text, config=None):
    """
    Predict whether a single text is human-written or AI-generated.

    Args:
        model (nn.Module): The trained model.
        tokenizer (AutoTokenizer): The tokenizer.
        text (str): The input text to classify.
        config (Config, optional): Configuration object.

    Returns:
        dict: Prediction result with label, confidence, and probabilities.
    """
    if config is None:
        config = Config

    model.eval()
    with torch.no_grad():
        encodings = tokenize_texts([text], tokenizer, config.MAX_LENGTH)
        input_ids = encodings["input_ids"].to(config.DEVICE)
        attention_mask = encodings["attention_mask"].to(config.DEVICE)

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
        )
        logits = outputs.logits
        probs = F.softmax(logits, dim=-1)
        pred = torch.argmax(logits, dim=-1).item()
        confidence = probs[0][pred].item()

    label_map = {0: "human", 1: "AI"}
    result = {
        "prediction": pred,
        "label": label_map[pred],
        "confidence": confidence,
        "probabilities": {
            "human": probs[0][0].item(),
            "AI": probs[0][1].item(),
        },
        "text_preview": text[:100] + ("..." if len(text) > 100 else ""),
    }

    return result


def predict_text_verbose(model, tokenizer, text, config=None):
    """Predict and print detailed results for a single text."""
    result = predict_text(model, tokenizer, text, config)

    print(f"\n{'=' * 60}")
    print("PREDICTION RESULT")
    print(f"{'=' * 60}")
    print(f"  Text:      {result['text_preview']}")
    print(f"  Prediction: {result['label'].upper()} ({result['prediction']})")
    print(f"  Confidence: {result['confidence']:.4f} ({result['confidence'] * 100:.2f}%)")
    print(f"  Probs:     Human={result['probabilities']['human']:.4f}, "
          f"AI={result['probabilities']['AI']:.4f}")

    return result


# ---------------------------------------------------------------------------
# Batch prediction on list of texts
# ---------------------------------------------------------------------------

def predict_batch(model, tokenizer, texts, config=None):
    """
    Predict labels for a batch of texts.

    Args:
        model (nn.Module): The trained model.
        tokenizer (AutoTokenizer): The tokenizer.
        texts (list of str): List of input texts.
        config (Config, optional): Configuration object.

    Returns:
        list of dict: Prediction results for each text.
    """
    if config is None:
        config = Config

    model.eval()
    results = []

    with torch.no_grad():
        encodings = tokenize_texts(texts, tokenizer, config.MAX_LENGTH)
        input_ids = encodings["input_ids"].to(config.DEVICE)
        attention_mask = encodings["attention_mask"].to(config.DEVICE)

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
        )
        logits = outputs.logits
        probs = F.softmax(logits, dim=-1)
        preds = torch.argmax(logits, dim=-1)

    label_map = {0: "human", 1: "AI"}

    for i, text in enumerate(texts):
        pred = preds[i].item()
        result = {
            "prediction": pred,
            "label": label_map[pred],
            "confidence": probs[i][pred].item(),
            "probabilities": {
                "human": probs[i][0].item(),
                "AI": probs[i][1].item(),
            },
            "text_preview": text[:80] + ("..." if len(text) > 80 else ""),
        }
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """Command-line interface for evaluation."""
    parser = argparse.ArgumentParser(
        description="Evaluate the AI detection model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python evaluate.py                         # Evaluate on test split
  python evaluate.py --text "Hello world"    # Single text prediction
  python evaluate.py --batch                 # Interactive batch mode
  python evaluate.py --model path/to/model.pth --text "Sample text"
        """,
    )

    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="Path to the model .pth file (default: models/humanwrite_detector.pth)",
    )
    parser.add_argument(
        "--text", "-t",
        type=str,
        default=None,
        help="Single text to classify",
    )
    parser.add_argument(
        "--batch", "-b",
        action="store_true",
        help="Run in batch mode (reads multiple texts from stdin)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress verbose output (only print final metrics)",
    )

    args = parser.parse_args()

    # Load model
    model, model_config, tokenizer = load_trained_model(args.model)

    if model is None:
        sys.exit(1)

    # Determine action
    if args.text:
        # Single text prediction
        predict_text_verbose(model, tokenizer, args.text)
    elif args.batch:
        # Batch mode: read texts from stdin
        print("Batch mode: Enter one text per line. Press Ctrl+D (or Ctrl+Z on Windows) to finish.")
        print("Enter texts (one per line):")
        texts = []
        try:
            while True:
                line = input()
                if line.strip():
                    texts.append(line.strip())
        except EOFError:
            pass

        if texts:
            results = predict_batch(model, tokenizer, texts)
            print(f"\n{'=' * 60}")
            print(f"BATCH PREDICTION RESULTS ({len(results)} texts)")
            print(f"{'=' * 60}")
            for i, result in enumerate(results):
                print(f"\n  [{i + 1}] {result['text_preview']}")
                print(f"      → {result['label'].upper()} "
                      f"(confidence: {result['confidence']:.4f})")
        else:
            print("No texts provided.")
    else:
        # Default: evaluate on test set
        evaluate_on_test_set(model, tokenizer, verbose=not args.quiet)


if __name__ == "__main__":
    main()