
import torch
from transformers import AutoModelForSequenceClassification

def load_detector():

    model=AutoModelForSequenceClassification.from_pretrained(
        "distilbert-base-uncased"
    )

    return model
