import torch

def mean_pooling(model_output, attention_mask):
    """
    Perform mean pooling on token embeddings to extract document-level vectors.
    Uses the attention mask to exclude padding tokens from calculation.
    """
    token_embeddings = model_output[0] # First element containing hidden-states
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    return sum_embeddings / sum_mask