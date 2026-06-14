"""
train.py

Full training pipeline for AI/Human text detection using DistilBERT.

Steps:
  1. Load dataset from human/ and ai_generated/ directories
  2. Clean and deduplicate text
  3. Stratified train/test split (80/20)
  4. Tokenize with DistilBERT tokenizer
  5. Create PyTorch DataLoaders
  6. Train DistilBERT sequence classifier
  7. Evaluate accuracy on test set
  8. Save model to models/humanwrite_detector.pth

Output:
  0 = human
  1 = AI
"""

import os
import sys
import json
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup,
)
from sklearn.metrics import accuracy_score, classification_report

# Allow imports from sibling modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai_engine.dataset.dataset_loader import load_combined_dataset
from ai_engine.dataset.dataset_cleaner import clean_and_deduplicate
from ai_engine.dataset.dataset_splitter import split_dataset, to_transformers_format

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class Config:
    # Paths
    DATASET_DIR = "HumanWriteAI/ai_engine/dataset"
    MODEL_SAVE_DIR = "HumanWriteAI/ai_engine/models"
    MODEL_SAVE_PATH = os.path.join(MODEL_SAVE_DIR, "humanwrite_detector.pth")
    LOG_DIR = "HumanWriteAI/ai_engine/training/logs"

    # Model
    MODEL_NAME = "distilbert-base-uncased"
    MAX_LENGTH = 512
    NUM_LABELS = 2  # 0 = human, 1 = AI

    # Training hyperparameters
    BATCH_SIZE = 16
    LEARNING_RATE = 2e-5
    NUM_EPOCHS = 3
    WARMUP_STEPS = 0
    WEIGHT_DECAY = 0.01

    # Dataset
    TEST_SIZE = 0.2
    MIN_TEXT_LENGTH = 20
    RANDOM_SEED = 42

    # Device
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ---------------------------------------------------------------------------
# Custom PyTorch Dataset
# ---------------------------------------------------------------------------

class TextClassificationDataset(Dataset):
    """PyTorch Dataset for tokenized text classification."""

    def __init__(self, encodings, labels):
        """
        Args:
            encodings (dict): Tokenizer output with 'input_ids', 'attention_mask'.
            labels (list of int): Ground-truth labels (0 = human, 1 = AI).
        """
        self.input_ids = encodings["input_ids"]
        self.attention_mask = encodings["attention_mask"]
        self.labels = labels

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "input_ids": self.input_ids[idx],
            "attention_mask": self.attention_mask[idx],
            "labels": torch.tensor(self.labels[idx], dtype=torch.long),
        }


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------

def tokenize_texts(texts, tokenizer, max_length=512):
    """
    Tokenize a list of texts using the provided tokenizer.

    Args:
        texts (list of str): Input texts.
        tokenizer (AutoTokenizer): Hugging Face tokenizer.
        max_length (int): Maximum token length (truncate/pad).

    Returns:
        dict: 'input_ids' and 'attention_mask' as PyTorch tensors.
    """
    return tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )


# ---------------------------------------------------------------------------
# Data preparation pipeline
# ---------------------------------------------------------------------------

def prepare_data(config):
    """
    Load, clean, split, and tokenize the full dataset.

    Args:
        config (Config): Configuration object.

    Returns:
        tuple: (train_loader, test_loader, tokenizer)
    """
    print("=" * 60)
    print("DATA PREPARATION")
    print("=" * 60)

    # 1. Load dataset
    print("\n[1/5] Loading dataset...")
    raw_data = load_combined_dataset(config.DATASET_DIR)
    print(f"  Loaded {len(raw_data)} raw documents")

    if len(raw_data) == 0:
        print("\n⚠  WARNING: No data found!")
        print(f"  Ensure text files exist in {config.DATASET_DIR}/human/ and {config.DATASET_DIR}/ai_generated/")
        print("  Creating synthetic sample data for demonstration...\n")
        raw_data = _create_sample_data()

    # 2. Clean and deduplicate
    print("\n[2/5] Cleaning and deduplicating...")
    cleaned_data = clean_and_deduplicate(
        raw_data,
        min_length=config.MIN_TEXT_LENGTH,
        near_threshold=0.85,
    )
    print(f"  Cleaned dataset: {len(cleaned_data)} documents")

    # 3. Stratified split (80% train, 20% test)
    print("\n[3/5] Splitting dataset...")
    train_data, test_data = split_dataset(
        cleaned_data,
        test_size=config.TEST_SIZE,
        shuffle=True,
        seed=config.RANDOM_SEED,
    )
    print(f"  Train: {len(train_data)} | Test: {len(test_data)}")

    # 4. Convert to Transformers format
    print("\n[4/5] Converting to Transformers format...")
    train_dict = to_transformers_format(train_data)
    test_dict = to_transformers_format(test_data)

    # 5. Tokenize
    print(f"\n[5/5] Tokenizing with {config.MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
    train_encodings = tokenize_texts(train_dict["text"], tokenizer, config.MAX_LENGTH)
    test_encodings = tokenize_texts(test_dict["text"], tokenizer, config.MAX_LENGTH)

    # Create PyTorch Datasets
    train_dataset = TextClassificationDataset(train_encodings, train_dict["label"])
    test_dataset = TextClassificationDataset(test_encodings, test_dict["label"])

    # Create DataLoaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=config.BATCH_SIZE,
        shuffle=True,
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=config.BATCH_SIZE,
        shuffle=False,
    )

    print(f"\n  Train batches: {len(train_loader)} | Test batches: {len(test_loader)}")
    print(f"  Batch size: {config.BATCH_SIZE}")
    print("=" * 60)

    return train_loader, test_loader, tokenizer


def _create_sample_data():
    """
    Create synthetic sample data when no real data is found.
    This allows the training pipeline to run for demonstration purposes.
    """
    sample_data = []
    # 50 human-like samples
    human_samples = [
        "The quick brown fox jumps over the lazy dog near the riverbank.",
        "Today I went to the market and bought fresh vegetables for dinner.",
        "The teacher explained the lesson carefully so all students could understand.",
        "My grandmother used to bake the most delicious apple pie every Sunday.",
        "Scientists have discovered a new species of butterfly in the Amazon rainforest.",
        "The museum exhibit featured ancient artifacts from Egyptian civilization.",
        "Learning a new language requires practice, patience, and dedication.",
        "The football match ended in a draw after an exciting second half.",
        "She spent hours reading the novel, captivated by its intricate plot twists.",
        "The chef prepared a five-course meal using locally sourced ingredients.",
        "Walking through the park, I noticed the cherry blossoms had begun to bloom.",
        "The committee voted unanimously to approve the new community center project.",
        "His speech about climate change inspired many people to take action.",
        "The documentary explored the lives of marine animals in the Pacific Ocean.",
        "After months of training, she finally completed her first marathon.",
        "The architecture of the building reflected a blend of modern and classical styles.",
        "Parents and teachers worked together to organize the school fundraiser.",
        "The orchestra performed Beethoven's Symphony No. 5 to a standing ovation.",
        "He wrote a heartfelt letter to his childhood friend after many years apart.",
        "The garden was filled with colorful flowers that attracted butterflies and bees.",
        "Technology has transformed the way we communicate with people around the world.",
        "She practiced the piano for hours every day to prepare for the recital.",
        "The hiking trail wound through dense forest and opened up to a stunning vista.",
        "Volunteers gathered at the beach to clean up plastic waste and debris.",
        "The novel explores themes of identity, belonging, and the meaning of home.",
        "Fresh bread and coffee made the perfect start to a lazy Saturday morning.",
        "The professor's lecture on quantum physics was both challenging and fascinating.",
        "They built a treehouse in the backyard using recycled wood and materials.",
        "The sunset painted the sky in shades of orange, pink, and purple.",
        "Her painting won first place at the local art competition this year.",
        "The puppy eagerly wagged its tail as the children played in the yard.",
        "Economic policies have a direct impact on small businesses and local communities.",
        "She kept a journal to document her travels across Southeast Asia.",
        "The detective carefully examined the evidence before drawing any conclusions.",
        "Farmers in the region have adopted sustainable agricultural practices.",
        "The film received critical acclaim for its powerful storytelling and performances.",
        "Meditation and mindfulness can help reduce stress and improve focus.",
        "The historical novel transported readers back to medieval England.",
        "He spent his weekends volunteering at the animal shelter near his home.",
        "The concert featured musicians from different countries performing together.",
        "Urban gardens provide fresh produce to communities that lack grocery stores.",
        "She learned to knit from her grandmother and made scarves for the whole family.",
        "The astronomy club set up telescopes to observe the meteor shower.",
        "His research focused on renewable energy solutions for developing nations.",
        "The children built a sandcastle that resembled a medieval fortress.",
        "Nutritionists recommend a balanced diet rich in fruits and vegetables.",
        "The photography exhibition captured the beauty of everyday life in the city.",
        "He repaired the old bicycle and donated it to a local charity program.",
        "The thunderstorm rolled in suddenly, forcing everyone to seek shelter.",
        "She founded a nonprofit organization dedicated to ocean conservation efforts.",
    ]
    # 50 AI-like samples
    ai_samples = [
        "In accordance with regulatory guidelines and compliance standards, the following procedures must be implemented immediately.",
        "Optimization of algorithmic parameters is essential for maximizing efficiency and throughput in computational workflows.",
        "The implementation of strategic initiatives requires comprehensive analysis of market trends and consumer behavior patterns.",
        "Upon evaluation of the aforementioned criteria, it is recommended that all stakeholders proceed with the proposed framework.",
        "Leveraging advanced machine learning techniques enables the identification of patterns within complex datasets.",
        "The integration of cloud-based solutions facilitates seamless collaboration across geographically distributed teams.",
        "Subsequent analysis of the data reveals a statistically significant correlation between the variables under investigation.",
        "It is imperative to ensure all system components are properly configured prior to deployment in production environments.",
        "The utilization of automated processes significantly reduces manual intervention and minimizes potential human error.",
        "Following a thorough assessment of the available options, the optimal solution has been selected for implementation.",
        "Strategic alignment of organizational objectives with technological capabilities drives sustainable growth and innovation.",
        "The deployment of scalable infrastructure ensures robust performance under varying workload conditions.",
        "Comprehensive testing protocols must be adhered to in order to validate system integrity and reliability.",
        "The aforementioned methodology provides a framework for addressing complex challenges in dynamic environments.",
        "Leveraging synergies across multiple departments enhances operational efficiency and resource utilization.",
        "The implementation roadmap outlines key milestones and deliverables for the project lifecycle.",
        "A data-driven approach to decision making enables organizations to identify actionable insights and opportunities.",
        "The system architecture has been designed to support high availability and fault tolerance requirements.",
        "Continuous monitoring and evaluation of performance metrics is essential for maintaining quality standards.",
        "The proposed solution addresses the identified requirements while remaining cost-effective and scalable.",
        "Optimization of resource allocation ensures maximum return on investment across all operational areas.",
        "The framework incorporates best practices and industry standards to ensure compliance and security.",
        "Iterative refinement of the model parameters leads to improved accuracy and predictive performance.",
        "The integration of feedback mechanisms allows for continuous improvement and adaptation to changing conditions.",
        "A comprehensive risk assessment has been conducted to identify potential vulnerabilities and mitigation strategies.",
        "The implementation of robust security protocols protects sensitive data from unauthorized access.",
        "Advanced analytics capabilities enable real-time processing and analysis of streaming data sources.",
        "The standardization of procedures ensures consistency and quality across all operational processes.",
        "Scalable architecture designs accommodate future growth and expansion without significant reconfiguration.",
        "The evaluation framework assesses performance across multiple dimensions including accuracy and efficiency.",
        "Systematic analysis of user feedback informs product development and feature prioritization decisions.",
        "The deployment pipeline automates the build, test, and release processes for continuous delivery.",
        "Cross-functional collaboration between teams ensures alignment of goals and objectives across the organization.",
        "The implementation of best practices in data governance ensures data quality and regulatory compliance.",
        "A modular approach to system design facilitates maintenance, updates, and future enhancements.",
        "Performance benchmarks indicate significant improvements over previous generation systems.",
        "The methodology employs a multi-stage approach to address complexity and ensure thoroughness.",
        "Strategic partnerships with industry leaders provide access to cutting-edge technologies and expertise.",
        "The framework incorporates redundancy and failover mechanisms to ensure business continuity.",
        "Comprehensive documentation of system architecture enables efficient knowledge transfer and onboarding.",
        "The optimization algorithm converges to a global optimum through iterative refinement techniques.",
        "Implementation of the proposed changes requires careful coordination across multiple teams.",
        "The analysis reveals several opportunities for process improvement and efficiency gains.",
        "A systematic approach to problem solving ensures thorough evaluation of all possible solutions.",
        "The integration layer facilitates communication between disparate systems and data sources.",
        "Performance metrics are tracked and analyzed to identify trends and inform decision making.",
        "The deployment strategy includes phased rollout to minimize disruption and manage risk.",
        "Advanced encryption protocols ensure the confidentiality and integrity of transmitted data.",
        "The framework supports extensibility through modular design and well-defined interfaces.",
        "Continuous integration and continuous deployment practices enable rapid iteration and delivery.",
    ]

    for text in human_samples:
        sample_data.append({"text": text, "label": "human"})
    for text in ai_samples:
        sample_data.append({"text": text, "label": "ai"})

    print(f"  Created {len(sample_data)} synthetic samples ({len(human_samples)} human, {len(ai_samples)} AI)")
    return sample_data


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_model(model, train_loader, test_loader, config):
    """
    Train the DistilBERT model.

    Args:
        model (nn.Module): The DistilBERT model.
        train_loader (DataLoader): Training data loader.
        test_loader (DataLoader): Test data loader.
        config (Config): Configuration object.

    Returns:
        nn.Module: Trained model.
    """
    print("\n" + "=" * 60)
    print("TRAINING")
    print("=" * 60)

    model.to(config.DEVICE)

    # Optimizer
    optimizer = AdamW(
        model.parameters(),
        lr=config.LEARNING_RATE,
        weight_decay=config.WEIGHT_DECAY,
        correct_bias=False,
    )

    # Loss function (CrossEntropyLoss is used internally by the model,
    # but we define it explicitly for clarity)
    criterion = nn.CrossEntropyLoss()

    # Scheduler
    total_steps = len(train_loader) * config.NUM_EPOCHS
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=config.WARMUP_STEPS,
        num_training_steps=total_steps,
    )

    # Training loop
    global_step = 0
    best_accuracy = 0.0

    for epoch in range(config.NUM_EPOCHS):
        print(f"\n{'─' * 40}")
        print(f"Epoch {epoch + 1}/{config.NUM_EPOCHS}")
        print(f"{'─' * 40}")

        model.train()
        total_loss = 0
        epoch_start = time.time()

        for batch_idx, batch in enumerate(train_loader):
            # Move batch to device
            input_ids = batch["input_ids"].to(config.DEVICE)
            attention_mask = batch["attention_mask"].to(config.DEVICE)
            labels = batch["labels"].to(config.DEVICE)

            # Forward pass
            optimizer.zero_grad()
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )
            loss = outputs.loss
            total_loss += loss.item()

            # Backward pass
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()

            global_step += 1

            # Log progress
            if (batch_idx + 1) % 10 == 0 or batch_idx == len(train_loader) - 1:
                avg_loss = total_loss / (batch_idx + 1)
                lr = scheduler.get_last_lr()[0]
                print(
                    f"  Step {batch_idx + 1:3d}/{len(train_loader):3d} | "
                    f"Loss: {avg_loss:.4f} | "
                    f"LR: {lr:.2e} | "
                    f"Time: {time.time() - epoch_start:.1f}s"
                )

        avg_epoch_loss = total_loss / len(train_loader)
        epoch_time = time.time() - epoch_start

        # Evaluate after each epoch
        accuracy = evaluate_model(model, test_loader, config, verbose=False)

        print(f"\n  Epoch {epoch + 1} Summary:")
        print(f"    Avg Loss: {avg_epoch_loss:.4f}")
        print(f"    Accuracy: {accuracy:.4f} ({accuracy * 100:.2f}%)")
        print(f"    Time:     {epoch_time:.1f}s")

        # Save best model
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            _save_model(model, config, is_best=True)
            print(f"    → Best model saved (accuracy: {accuracy:.4f})")

    print(f"\n{'=' * 60}")
    print(f"TRAINING COMPLETE")
    print(f"{'=' * 60}")
    print(f"Best accuracy: {best_accuracy:.4f} ({best_accuracy * 100:.2f}%)")
    print(f"Total steps: {global_step}")

    return model


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_model(model, test_loader, config, verbose=True):
    """
    Evaluate the model on the test dataset.

    Args:
        model (nn.Module): The model to evaluate.
        test_loader (DataLoader): Test data loader.
        config (Config): Configuration object.
        verbose (bool): Whether to print detailed results.

    Returns:
        float: Accuracy score.
    """
    model.eval()
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in test_loader:
            input_ids = batch["input_ids"].to(config.DEVICE)
            attention_mask = batch["attention_mask"].to(config.DEVICE)
            labels = batch["labels"].to(config.DEVICE)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
            )
            logits = outputs.logits
            preds = torch.argmax(logits, dim=-1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    accuracy = accuracy_score(all_labels, all_preds)

    if verbose:
        print(f"\n{'=' * 60}")
        print("EVALUATION")
        print(f"{'=' * 60}")
        print(f"  Accuracy:  {accuracy:.4f} ({accuracy * 100:.2f}%)")
        print(f"  Samples:   {len(all_labels)}")
        print(f"\nClassification Report:")
        print(f"{'─' * 40}")
        report = classification_report(
            all_labels,
            all_preds,
            target_names=["human (0)", "AI (1)"],
            digits=4,
        )
        print(report)

    return accuracy


# ---------------------------------------------------------------------------
# Model persistence
# ---------------------------------------------------------------------------

def _save_model(model, config, is_best=False):
    """
    Save the model weights and configuration to disk.

    Args:
        model (nn.Module): The trained model.
        config (Config): Configuration object.
        is_best (bool): Whether this is the best model so far.
    """
    os.makedirs(config.MODEL_SAVE_DIR, exist_ok=True)

    # Save full model state
    save_dict = {
        "model_state_dict": model.state_dict(),
        "config": {
            "model_name": config.MODEL_NAME,
            "num_labels": config.NUM_LABELS,
            "max_length": config.MAX_LENGTH,
        },
        "metadata": {
            "is_best": is_best,
        },
    }

    torch.save(save_dict, config.MODEL_SAVE_PATH)
    print(f"\n  Model saved to: {config.MODEL_SAVE_PATH}")


def save_model(model, config):
    """Public function to save the model (called after training completes)."""
    _save_model(model, config, is_best=False)
    print(f"  Final model saved to: {config.MODEL_SAVE_PATH}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    """Run the full training pipeline."""
    print("\n" + "#" * 60)
    print("#")
    print("#  HumanWriteAI - AI Detection Training Pipeline")
    print("#")
    print("#" * 60)
    print(f"\nDevice: {Config.DEVICE}")
    print(f"Model:  {Config.MODEL_NAME}")
    print(f"Epochs: {Config.NUM_EPOCHS}")
    print(f"Batch:  {Config.BATCH_SIZE}")
    print(f"LR:     {Config.LEARNING_RATE}")

    start_time = time.time()

    # 1. Prepare data
    train_loader, test_loader, tokenizer = prepare_data(Config)

    # 2. Initialize model
    print("\n" + "=" * 60)
    print("MODEL INITIALIZATION")
    print("=" * 60)
    print(f"\nLoading {Config.MODEL_NAME}...")
    model = AutoModelForSequenceClassification.from_pretrained(
        Config.MODEL_NAME,
        num_labels=Config.NUM_LABELS,
    )
    print(f"  Parameters: {sum(p.numel() for p in model.parameters()):,}")
    print(f"  Trainable:  {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

    # 3. Train
    model = train_model(model, train_loader, test_loader, Config)

    # 4. Final evaluation
    print("\n" + "=" * 60)
    print("FINAL EVALUATION")
    print("=" * 60)
    final_accuracy = evaluate_model(model, test_loader, Config, verbose=True)

    # 5. Save model
    save_model(model, Config)

    # 6. Save tokenizer for inference
    tokenizer.save_pretrained(Config.MODEL_SAVE_DIR)
    print(f"  Tokenizer saved to: {Config.MODEL_SAVE_DIR}")

    total_time = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"PIPELINE COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Final accuracy: {final_accuracy:.4f} ({final_accuracy * 100:.2f}%)")
    print(f"  Total time:     {total_time:.1f}s ({total_time / 60:.1f} min)")
    print(f"  Model saved at: {Config.MODEL_SAVE_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()