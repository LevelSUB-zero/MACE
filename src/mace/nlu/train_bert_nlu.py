"""
MACE NLU — DistilBERT Training Script

Trains a multi-task model for intent classification + slot filling.
Runs on CPU (~15 min for 434 examples × 10 epochs).

Usage:
    python -m mace.nlu.convert_to_bio    # Step 1: Generate BIO data
    python -m mace.nlu.train_bert_nlu    # Step 2: Train model
    python -m mace.nlu.bert_nlu          # Step 3: Test inference
"""
import json
import os
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split
from typing import Dict, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data", "nlu")
MODEL_DIR = os.path.join(BASE_DIR, "models", "nlu", "bert_nlu")
BIO_FILE = os.path.join(DATA_DIR, "bio_training_data.jsonl")
LABEL_MAP_FILE = os.path.join(DATA_DIR, "label_maps.json")


# ================================================================
# Dataset
# ================================================================
class NLUDataset(Dataset):
    """Dataset for multi-task NLU training."""
    
    def __init__(self, data: List[Dict], tokenizer, label_maps: Dict, max_length: int = 128):
        self.data = data
        self.tokenizer = tokenizer
        self.label_maps = label_maps
        self.max_length = max_length
        self.intent2id = label_maps["intent2id"]
        self.memory2id = label_maps["memory2id"]
        self.bio2id = label_maps["bio2id"]
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        text = item["text"]
        tokens = item["tokens"]
        bio_tags = item["bio_tags"]
        
        # Tokenize with subword alignment
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
            return_offsets_mapping=True,
        )
        
        input_ids = encoding["input_ids"].squeeze(0)
        attention_mask = encoding["attention_mask"].squeeze(0)
        offset_mapping = encoding["offset_mapping"].squeeze(0)
        
        # Intent label
        intent_id = self.intent2id.get(item["intent"], 0)
        
        # Memory label
        memory_id = self.memory2id.get(item["memory_type"], 0)
        
        # Align BIO tags to subword tokens
        slot_labels = self._align_bio_tags(text, tokens, bio_tags, offset_mapping)
        
        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "intent_labels": torch.tensor(intent_id, dtype=torch.long),
            "memory_labels": torch.tensor(memory_id, dtype=torch.long),
            "slot_labels": slot_labels,
        }
    
    def _align_bio_tags(self, text, tokens, bio_tags, offset_mapping):
        """Align word-level BIO tags to subword tokens."""
        # Build character-to-tag mapping from word tokens
        text_lower = text.lower()
        char_tags = ["O"] * len(text)
        
        pos = 0
        for tok, tag in zip(tokens, bio_tags):
            idx = text_lower.find(tok.lower(), pos)
            if idx == -1:
                pos += len(tok) + 1
                continue
            for c in range(idx, idx + len(tok)):
                if c < len(char_tags):
                    char_tags[c] = tag
            pos = idx + len(tok)
        
        # Map subword tokens to BIO tags
        aligned = torch.full((self.max_length,), -100, dtype=torch.long)
        
        for i, (start, end) in enumerate(offset_mapping):
            start, end = start.item(), end.item()
            if start == 0 and end == 0:
                continue  # [CLS], [SEP], [PAD]
            
            # Take the tag of the first character of this subword
            if start < len(char_tags):
                tag = char_tags[start]
                # For continuation subwords, convert B- to I-
                if i > 0:
                    prev_start = offset_mapping[i-1][0].item()
                    prev_end = offset_mapping[i-1][1].item()
                    if prev_end == start and tag.startswith("B-"):
                        tag = "I-" + tag[2:]
                
                aligned[i] = self.bio2id.get(tag, self.bio2id.get("O", 0))
            
        return aligned


# ================================================================
# Training Loop
# ================================================================
def train(
    epochs: int = 15,
    batch_size: int = 16,
    lr: float = 3e-5,
    val_split: float = 0.15,
):
    """Train the multi-task NLU model."""
    from transformers import AutoTokenizer
    from .bert_nlu import MaceNLUModel
    
    # Load data
    if not os.path.exists(BIO_FILE):
        print(f"❌ BIO data not found: {BIO_FILE}")
        print(f"   Run: python -m mace.nlu.convert_to_bio")
        return
    
    data = []
    with open(BIO_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    
    label_maps = json.load(open(LABEL_MAP_FILE, "r", encoding="utf-8"))
    
    print(f"📊 Data: {len(data)} examples")
    print(f"📋 Intents: {len(label_maps['intents'])}")
    print(f"📋 Memory types: {len(label_maps['memory_types'])}")
    print(f"📋 BIO tags: {len(label_maps['bio_tags'])}")
    
    # Tokenizer
    model_name = "distilbert-base-uncased"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # Dataset
    dataset = NLUDataset(data, tokenizer, label_maps)
    
    val_size = int(len(dataset) * val_split)
    train_size = len(dataset) - val_size
    train_dataset, val_dataset = random_split(
        dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(42)
    )
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)
    
    print(f"📊 Train: {train_size}, Val: {val_size}")
    
    # Model
    device = torch.device("cpu")
    model = MaceNLUModel(
        num_intents=len(label_maps["intents"]),
        num_bio_tags=len(label_maps["bio_tags"]),
        num_memory=len(label_maps["memory_types"]),
        model_name=model_name,
    )
    model.to(device)
    
    # Count parameters
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"🧠 Parameters: {total:,} total, {trainable:,} trainable")
    
    # Optimizer
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    # Train
    best_val_acc = 0.0
    print(f"\n🔥 Training for {epochs} epochs...\n")
    
    for epoch in range(epochs):
        # --- Train ---
        model.train()
        total_loss = 0.0
        correct_intents = 0
        total_intents = 0
        
        for batch in train_loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            
            output = model(
                input_ids=batch["input_ids"],
                attention_mask=batch["attention_mask"],
                intent_labels=batch["intent_labels"],
                memory_labels=batch["memory_labels"],
                slot_labels=batch["slot_labels"],
            )
            
            loss = output["loss"]
            loss.backward()
            
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            optimizer.zero_grad()
            
            total_loss += loss.item()
            
            preds = output["intent_logits"].argmax(dim=-1)
            correct_intents += (preds == batch["intent_labels"]).sum().item()
            total_intents += len(batch["intent_labels"])
        
        train_acc = correct_intents / total_intents if total_intents > 0 else 0
        avg_loss = total_loss / len(train_loader)
        
        # --- Validate ---
        model.eval()
        val_correct = 0
        val_total = 0
        val_slot_correct = 0
        val_slot_total = 0
        
        with torch.no_grad():
            for batch in val_loader:
                batch = {k: v.to(device) for k, v in batch.items()}
                
                output = model(
                    input_ids=batch["input_ids"],
                    attention_mask=batch["attention_mask"],
                )
                
                preds = output["intent_logits"].argmax(dim=-1)
                val_correct += (preds == batch["intent_labels"]).sum().item()
                val_total += len(batch["intent_labels"])
                
                # Slot accuracy (non-padding only)
                slot_preds = output["slot_logits"].argmax(dim=-1)
                mask = batch["slot_labels"] != -100
                val_slot_correct += (slot_preds[mask] == batch["slot_labels"][mask]).sum().item()
                val_slot_total += mask.sum().item()
        
        val_acc = val_correct / val_total if val_total > 0 else 0
        slot_acc = val_slot_correct / val_slot_total if val_slot_total > 0 else 0
        
        scheduler.step()
        
        print(
            f"  Epoch {epoch+1:2d}/{epochs} | "
            f"Loss: {avg_loss:.4f} | "
            f"Train Intent: {train_acc:.1%} | "
            f"Val Intent: {val_acc:.1%} | "
            f"Val Slot: {slot_acc:.1%}"
        )
        
        # Save best
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            _save_model(model, tokenizer, label_maps)
    
    print(f"\n✅ Training complete! Best val accuracy: {best_val_acc:.1%}")
    print(f"📁 Model saved to: {MODEL_DIR}")
    
    return model


def _save_model(model, tokenizer, label_maps):
    """Save model, tokenizer, and label maps."""
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Save model weights
    torch.save(model.state_dict(), os.path.join(MODEL_DIR, "model.pt"))
    
    # Save tokenizer
    tokenizer_dir = os.path.join(MODEL_DIR, "tokenizer")
    os.makedirs(tokenizer_dir, exist_ok=True)
    tokenizer.save_pretrained(tokenizer_dir)
    
    # Save label maps
    with open(os.path.join(MODEL_DIR, "label_maps.json"), "w") as f:
        json.dump(label_maps, f, indent=2)


# ================================================================
# Entry point
# ================================================================
if __name__ == "__main__":
    train()
