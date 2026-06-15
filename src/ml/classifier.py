import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from src.config import DEVICE, MODEL_NAME

class LegalDataset(torch.utils.data.Dataset):
    """Custom PyTorch dataset for tokenizing text facts to match BERT inputs."""
    def __init__(self, texts, labels=None, tokenizer=None, max_len=512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer if tokenizer else AutoTokenizer.from_pretrained(MODEL_NAME)
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            padding="max_length",
            truncation=True,
            return_attention_mask=True,
            return_tensors="pt"
        )
        
        item = {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten()
        }
        
        if self.labels is not None:
            item['labels'] = torch.tensor(self.labels[idx], dtype=torch.float)
            
        return item

class LegalClassifierPipeline:
    def __init__(self, model_path_or_name=MODEL_NAME, num_labels=None):
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        
        # Load sequence model configurations
        if num_labels is not None:
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_path_or_name, 
                num_labels=num_labels,
                problem_type="multi_label_classification"
            )
        else:
            self.model = AutoModelForSequenceClassification.from_pretrained(model_path_or_name)
            
        self.model.to(DEVICE)

    def predict(self, text: str) -> list[float]:
        """Calculates label probabilities for a raw string."""
        self.model.eval()
        inputs = self.tokenizer(
            text,
            max_length=512,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.sigmoid(logits).cpu().numpy().flatten()
            
        return probabilities.tolist()