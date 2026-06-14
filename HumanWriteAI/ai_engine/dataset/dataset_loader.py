"""
dataset_loader.py

Loads text files from human/ and ai_generated/ directories.
Returns labelled text data ready for cleaning and splitting.
"""

import os
from pathlib import Path


def load_text_files(directory):
    """
    Load all .txt files from a directory.

    Args:
        directory (str or Path): Path to the directory containing .txt files.

    Returns:
        list of dict: Each entry has 'text' (str) and 'filename' (str).
    """
    data = []
    dir_path = Path(directory)

    if not dir_path.exists():
        print(f"Warning: Directory '{dir_path}' does not exist.")
        return data

    for file_path in sorted(dir_path.glob("*.txt")):
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
            if text:
                data.append({
                    "text": text,
                    "filename": file_path.name,
                })
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    return data


def load_dataset(base_dir="HumanWriteAI/ai_engine/dataset"):
    """
    Load full dataset from human/ and ai_generated/ subdirectories.

    Args:
        base_dir (str): Base dataset directory path.

    Returns:
        tuple: (human_texts, ai_texts)
            Each is a list of dicts with 'text', 'filename', and 'label' keys.
    """
    base = Path(base_dir)
    human_dir = base / "human"
    ai_dir = base / "ai_generated"

    human_data = load_text_files(human_dir)
    ai_data = load_text_files(ai_dir)

    # Add labels
    for item in human_data:
        item["label"] = "human"
    for item in ai_data:
        item["label"] = "ai"

    return human_data, ai_data


def load_combined_dataset(base_dir="HumanWriteAI/ai_engine/dataset"):
    """
    Load and combine human + AI texts into a single list with labels.

    Args:
        base_dir (str): Base dataset directory path.

    Returns:
        list of dict: Each entry has 'text', 'filename', and 'label'.
    """
    human_data, ai_data = load_dataset(base_dir)
    combined = human_data + ai_data
    print(f"Loaded {len(combined)} documents ({len(human_data)} human, {len(ai_data)} AI)")
    return combined


if __name__ == "__main__":
    # Quick test
    data = load_combined_dataset()
    for item in data[:3]:
        print(f"[{item['label']}] {item['filename']}: {item['text'][:80]}...")