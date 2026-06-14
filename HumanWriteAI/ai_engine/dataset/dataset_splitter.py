"""
dataset_splitter.py

Splits cleaned dataset into:
  - 80% training
  - 20% testing

Outputs data in a format ready for Hugging Face Transformers
(list of dicts with 'text' and 'label') and optionally
writes to disk as CSV or JSON.
"""

import random
import csv
import json
from pathlib import Path
from collections import Counter


def stratified_split(data, test_size=0.2, shuffle=True, seed=42):
    """
    Perform a stratified train/test split, preserving label proportions.

    Args:
        data (list of dict): Each entry must contain 'label' ('human' or 'ai').
        test_size (float): Fraction of data to reserve for testing (default 0.2).
        shuffle (bool): Whether to shuffle before splitting.
        seed (int): Random seed for reproducibility.

    Returns:
        tuple: (train_data, test_data)
    """
    if shuffle:
        random.seed(seed)
        random.shuffle(data)

    # Group by label
    groups = {}
    for item in data:
        label = item.get("label", "unknown")
        groups.setdefault(label, []).append(item)

    train = []
    test = []
    for label, items in groups.items():
        n_total = len(items)
        n_test = max(1, round(n_total * test_size))
        n_train = n_total - n_test

        train.extend(items[:n_train])
        test.extend(items[n_train:])

    if shuffle:
        random.seed(seed)
        random.shuffle(train)
        random.shuffle(test)

    print(f"Train size: {len(train)} | Test size: {len(test)}")
    print(f"Train distribution: {dict(Counter(item['label'] for item in train))}")
    print(f"Test distribution:  {dict(Counter(item['label'] for item in test))}")

    return train, test


def split_dataset(data, test_size=0.2, shuffle=True, seed=42):
    """
    High-level split function (alias for stratified_split).

    Args:
        data (list of dict): Cleaned dataset.
        test_size (float): Proportion for testing (default 0.2 = 20%).
        shuffle (bool): Whether to shuffle.
        seed (int): Random seed.

    Returns:
        tuple: (train_data, test_data)
    """
    return stratified_split(data, test_size=test_size, shuffle=shuffle, seed=seed)


# ---------------------------------------------------------------------------
# Format converters for Transformers
# ---------------------------------------------------------------------------

def to_transformers_format(data, text_key="text", label_key="label"):
    """
    Convert dataset list to the format expected by Hugging Face Transformers:

        {
            "text": ["sentence1", "sentence2", ...],
            "label": [0, 1, ...]   # 0 = human, 1 = ai
        }

    Args:
        data (list of dict): Dataset entries.
        text_key (str): Key for text.
        label_key (str): Key for label ('human' or 'ai').

    Returns:
        dict: With keys 'text' (list of str) and 'label' (list of int).
    """
    label_map = {"human": 0, "ai": 1}
    texts = []
    labels = []

    for item in data:
        texts.append(item.get(text_key, ""))
        raw_label = item.get(label_key, "human")
        labels.append(label_map.get(raw_label, 0))

    return {"text": texts, "label": labels}


def to_hf_dataset_dict(data, text_key="text", label_key="label"):
    """
    Alias for to_transformers_format — returns a dict ready for
    `datasets.Dataset.from_dict()`.

    Returns:
        dict: With 'text' (list[str]) and 'label' (list[int]).
    """
    return to_transformers_format(data, text_key=text_key, label_key=label_key)


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def save_to_csv(data, output_path, text_key="text", label_key="label"):
    """
    Save dataset to a CSV file.

    Args:
        data (list of dict): Dataset entries.
        output_path (str or Path): Destination CSV path.
        text_key (str): Key for text.
        label_key (str): Key for label.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[text_key, label_key])
        writer.writeheader()
        for item in data:
            writer.writerow({text_key: item.get(text_key, ""), label_key: item.get(label_key, "")})

    print(f"Saved {len(data)} rows to {path}")


def save_to_json(data, output_path, text_key="text", label_key="label"):
    """
    Save dataset to a JSON file (list of objects).

    Args:
        data (list of dict): Dataset entries.
        output_path (str or Path): Destination JSON path.
        text_key (str): Key for text.
        label_key (str): Key for label.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    simplified = [
        {text_key: item.get(text_key, ""), label_key: item.get(label_key, "")}
        for item in data
    ]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(simplified, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(simplified)} entries to {path}")


def save_splits(train_data, test_data, output_dir="ai_engine/dataset/splits"):
    """
    Save train/test splits as both CSV and JSON, plus a transformers-ready JSON.

    Args:
        train_data (list of dict): Training set.
        test_data (list of dict): Testing set.
        output_dir (str): Directory to write split files.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Raw splits
    save_to_csv(train_data, out / "train.csv")
    save_to_csv(test_data, out / "test.csv")
    save_to_json(train_data, out / "train.json")
    save_to_json(test_data, out / "test.json")

    # Transformers-ready format
    train_tf = to_transformers_format(train_data)
    test_tf = to_transformers_format(test_data)

    with open(out / "train_transformers.json", "w", encoding="utf-8") as f:
        json.dump(train_tf, f, ensure_ascii=False, indent=2)
    with open(out / "test_transformers.json", "w", encoding="utf-8") as f:
        json.dump(test_tf, f, ensure_ascii=False, indent=2)

    print(f"\nAll splits saved to {out}/")
    print(f"  train_transformers.json: {len(train_tf['text'])} samples")
    print(f"  test_transformers.json:  {len(test_tf['text'])} samples")


if __name__ == "__main__":
    # Quick test with synthetic data
    sample = [
        {"text": f"Human document {i}", "label": "human"} for i in range(20)
    ] + [
        {"text": f"AI generated doc {i}", "label": "ai"} for i in range(20)
    ]

    train, test = split_dataset(sample, test_size=0.2)
    print(f"\nTrain count: {len(train)}, Test count: {len(test)}")

    # Show transformers-ready format
    hf_dict = to_transformers_format(train)
    print(f"\nTransformers train keys: {list(hf_dict.keys())}")
    print(f"First label: {hf_dict['label'][0]} (0=human, 1=ai)")