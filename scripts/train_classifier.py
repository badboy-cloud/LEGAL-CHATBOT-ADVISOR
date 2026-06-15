import os
import sys
import json
import torch
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics import f1_score, precision_recall_fscore_support
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    Trainer, 
    TrainingArguments, 
    EvalPrediction
)

# Set base import paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import DEVICE, MODEL_NAME, RAW_DATA_PATH, MODEL_SAVE_PATH
from src.ml.classifier import LegalDataset

def compute_metrics(eval_pred: EvalPrediction):
    predictions, labels = eval_pred
    # Sigmoid activation to convert logits to probability vectors
    probs = 1 / (1 + np.exp(-predictions))
    preds = (probs >= 0.5).astype(int)
    
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average='macro', zero_division=0
    )
    return {
        'f1_macro': f1,
        'precision_macro': precision,
        'recall_macro': recall
    }

def main():
    if not os.path.exists(RAW_DATA_PATH):
        print(f"Error: Dataset not found at '{RAW_DATA_PATH}'. Place your real CSV there first.")
        return

    print("Loading raw case file data for classification...")
    df = pd.read_csv(RAW_DATA_PATH)
    
    # Verify standard training target columns
    text_col = "case_facts" if "case_facts" in df.columns else df.columns[1]
    label_col = "applicable_sections" if "applicable_sections" in df.columns else df.columns[2]

    # Preprocess labels: Split comma-separated sections into python lists of strings
    print("Preprocessing multiclass labels...")
    df[label_col] = df[label_col].apply(
        lambda x: [s.strip() for s in str(x).split(',') if s.strip()] if pd.notnull(x) else []
    )
    
    # Apply Multi-Label Binarization (converts text list labels to binary arrays)
    mlb = MultiLabelBinarizer()
    binary_labels = mlb.fit_transform(df[label_col])
    num_classes = len(mlb.classes_)
    
    # Save the label categories dictionary so the API can decode them during runtime
    os.makedirs(MODEL_SAVE_PATH, exist_ok=True)
    label_mapping = {int(idx): str(label) for idx, label in enumerate(mlb.classes_)}
    labels_metadata_path = os.path.join(MODEL_SAVE_PATH, "labels.json")
    with open(labels_metadata_path, "w") as f:
        json.dump(label_mapping, f, indent=4)
    print(f"Label indexing mapped and saved to: {labels_metadata_path}")
    print(f"Total Unique Statutory Categories to Classify: {num_classes}")

    # Split dataset into training and validation folds
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        df[text_col].values, binary_labels, test_size=0.2, random_state=42
    )

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    # Build Custom datasets
    train_dataset = LegalDataset(train_texts, train_labels, tokenizer)
    val_dataset = LegalDataset(val_texts, val_labels, tokenizer)

    print(f"Initializing {MODEL_NAME} Classifier...")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=num_classes,
        problem_type="multi_label_classification"
    )
    model.to(DEVICE)

    # Training Configuration Options
    training_args = TrainingArguments(
        output_dir=os.path.join(MODEL_SAVE_PATH, "checkpoints"),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=3e-5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=3, # Standard baseline run
        weight_decay=0.01,
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        greater_is_better=True,
        logging_steps=10,
        disable_tqdm=False,
        report_to="none" # Disable external logging wrappers
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )

    print("Executing Model Fine-Tuning...")
    trainer.train()

    print(f"Saving fine-tuned weights and model parameters to {MODEL_SAVE_PATH}...")
    model.save_pretrained(MODEL_SAVE_PATH)
    tokenizer.save_pretrained(MODEL_SAVE_PATH)
    print("Fine-Tuning complete.")

if __name__ == "__main__":
    main()