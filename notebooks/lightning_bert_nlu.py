#!/usr/bin/env python3
"""
MACE NLU — DistilBERT Training on Lightning AI Studio
======================================================
SELF-CONTAINED. No external MACE imports needed.

STEPS:
  1. Lightning AI → New Studio → GPU (free T4)
  2. Upload: this script + generated_training_data.jsonl
  3. Terminal:
       pip install transformers torch datasets
       python lightning_bert_nlu.py
  4. Download the output folder: mace_bert_nlu/
  5. On your PC, copy it to: models/nlu/bert_nlu/

Architecture:
  DistilBERT (66M) with 3 heads:
    - Intent classifier  ([CLS] → 20 classes)
    - Memory classifier  ([CLS] → 6 classes)
    - Slot filler         (each token → BIO tags)
"""
import json
import os
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split

# ================================================================
# CONFIG
# ================================================================
TRAINING_FILE = "generated_training_data.jsonl"
OUTPUT_DIR = "mace_bert_nlu"
MODEL_NAME = "distilbert-base-uncased"
MAX_LENGTH = 128
EPOCHS = 20
BATCH_SIZE = 16
LR = 3e-5

# ================================================================
# STEP 1: Convert JSON → BIO
# ================================================================
def tokenize_simple(text):
    return text.split()

def find_entity_spans(text, tokens, entities):
    """Align entity values to tokens → BIO tags."""
    tags = ["O"] * len(tokens)
    if not entities:
        return tags
    
    text_lower = text.lower()
    token_positions = []
    pos = 0
    for tok in tokens:
        idx = text_lower.find(tok.lower(), pos)
        if idx == -1:
            idx = pos
        token_positions.append((idx, idx + len(tok)))
        pos = idx + len(tok)
    
    for entity_key, entity_value in entities.items():
        if not isinstance(entity_value, str):
            entity_value = str(entity_value)
        val_lower = entity_value.lower()
        start_idx = text_lower.find(val_lower)
        if start_idx == -1:
            continue
        end_idx = start_idx + len(val_lower)
        
        entity_tokens = []
        for i, (tok_start, tok_end) in enumerate(token_positions):
            if tok_start >= start_idx and tok_end <= end_idx:
                entity_tokens.append(i)
            elif tok_start < end_idx and tok_end > start_idx:
                entity_tokens.append(i)
        
        for j, tok_idx in enumerate(entity_tokens):
            if tags[tok_idx] == "O":
                tags[tok_idx] = f"B-{entity_key}" if j == 0 else f"I-{entity_key}"
    
    return tags

def convert_data(filepath):
    """Load JSON data and convert to BIO format."""
    examples = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    bio_data = []
    for ex in examples:
        text = ex.get("text", "")
        tokens = tokenize_simple(text)
        entities = ex.get("entities", {})
        bio_tags = find_entity_spans(text, tokens, entities)
        bio_data.append({
            "tokens": tokens,
            "bio_tags": bio_tags,
            "intent": ex.get("root_intent", "unknown"),
            "memory_type": ex.get("memory_type", "none"),
            "text": text,
        })
    
    # Collect label sets
    intents = sorted(set(d["intent"] for d in bio_data))
    memory_types = sorted(set(d["memory_type"] for d in bio_data))
    bio_tag_set = set(["O"])
    for d in bio_data:
        bio_tag_set.update(d["bio_tags"])
    bio_tags_list = sorted(bio_tag_set)
    
    label_maps = {
        "intents": intents,
        "memory_types": memory_types,
        "bio_tags": bio_tags_list,
        "intent2id": {v: i for i, v in enumerate(intents)},
        "id2intent": {str(i): v for i, v in enumerate(intents)},
        "memory2id": {v: i for i, v in enumerate(memory_types)},
        "id2memory": {str(i): v for i, v in enumerate(memory_types)},
        "bio2id": {v: i for i, v in enumerate(bio_tags_list)},
        "id2bio": {str(i): v for i, v in enumerate(bio_tags_list)},
    }
    
    return bio_data, label_maps


# ================================================================
# STEP 2: Model
# ================================================================
class MaceNLUModel(nn.Module):
    """DistilBERT + Intent Head + Memory Head + Slot Head."""
    
    def __init__(self, num_intents, num_bio_tags, num_memory, model_name=MODEL_NAME, dropout=0.1):
        super().__init__()
        from transformers import AutoModel
        self.encoder = AutoModel.from_pretrained(model_name)
        h = self.encoder.config.hidden_size
        
        self.intent_head = nn.Sequential(
            nn.Dropout(dropout), nn.Linear(h, h // 2), nn.ReLU(),
            nn.Dropout(dropout), nn.Linear(h // 2, num_intents),
        )
        self.memory_head = nn.Sequential(nn.Dropout(dropout), nn.Linear(h, num_memory))
        self.slot_head = nn.Sequential(nn.Dropout(dropout), nn.Linear(h, num_bio_tags))
    
    def forward(self, input_ids, attention_mask, intent_labels=None, slot_labels=None, memory_labels=None):
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        seq = out.last_hidden_state
        cls = seq[:, 0, :]
        
        intent_logits = self.intent_head(cls)
        memory_logits = self.memory_head(cls)
        slot_logits = self.slot_head(seq)
        
        result = {"intent_logits": intent_logits, "memory_logits": memory_logits, "slot_logits": slot_logits}
        
        if intent_labels is not None:
            ce = nn.CrossEntropyLoss()
            loss = ce(intent_logits, intent_labels)
            if memory_labels is not None:
                loss = loss + 0.5 * ce(memory_logits, memory_labels)
            if slot_labels is not None:
                slot_loss = nn.CrossEntropyLoss(ignore_index=-100)(
                    slot_logits.view(-1, slot_logits.size(-1)), slot_labels.view(-1))
                loss = loss + slot_loss
            result["loss"] = loss
        
        return result


# ================================================================
# STEP 3: Dataset
# ================================================================
class NLUDataset(Dataset):
    def __init__(self, data, tokenizer, label_maps, max_length=MAX_LENGTH):
        self.data = data
        self.tokenizer = tokenizer
        self.label_maps = label_maps
        self.max_length = max_length
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        enc = self.tokenizer(item["text"], truncation=True, max_length=self.max_length,
                             padding="max_length", return_tensors="pt", return_offsets_mapping=True)
        
        input_ids = enc["input_ids"].squeeze(0)
        attention_mask = enc["attention_mask"].squeeze(0)
        offset_mapping = enc["offset_mapping"].squeeze(0)
        
        intent_id = self.label_maps["intent2id"].get(item["intent"], 0)
        memory_id = self.label_maps["memory2id"].get(item["memory_type"], 0)
        
        # Align BIO tags to subword tokens
        text_lower = item["text"].lower()
        char_tags = ["O"] * len(item["text"])
        pos = 0
        for tok, tag in zip(item["tokens"], item["bio_tags"]):
            idx_found = text_lower.find(tok.lower(), pos)
            if idx_found == -1:
                pos += len(tok) + 1
                continue
            for c in range(idx_found, min(idx_found + len(tok), len(char_tags))):
                char_tags[c] = tag
            pos = idx_found + len(tok)
        
        slot_labels = torch.full((self.max_length,), -100, dtype=torch.long)
        for i, (start, end) in enumerate(offset_mapping):
            s, e = start.item(), end.item()
            if s == 0 and e == 0:
                continue
            if s < len(char_tags):
                tag = char_tags[s]
                slot_labels[i] = self.label_maps["bio2id"].get(tag, 0)
        
        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "intent_labels": torch.tensor(intent_id, dtype=torch.long),
            "memory_labels": torch.tensor(memory_id, dtype=torch.long),
            "slot_labels": slot_labels,
        }


# ================================================================
# STEP 4: Train
# ================================================================
def train():
    from transformers import AutoTokenizer
    
    if not os.path.exists(TRAINING_FILE):
        print(f"❌ Upload '{TRAINING_FILE}' first!")
        return
    
    # Convert data
    print("📊 Converting data to BIO format...")
    bio_data, label_maps = convert_data(TRAINING_FILE)
    print(f"   {len(bio_data)} examples, {len(label_maps['intents'])} intents, {len(label_maps['bio_tags'])} BIO tags")
    
    # Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    # Dataset split
    dataset = NLUDataset(bio_data, tokenizer, label_maps)
    val_size = max(1, int(len(dataset) * 0.15))
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(dataset, [train_size, val_size], generator=torch.Generator().manual_seed(42))
    
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE)
    print(f"   Train: {train_size}, Val: {val_size}")
    
    # Model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🖥️  Device: {device}")
    
    model = MaceNLUModel(
        num_intents=len(label_maps["intents"]),
        num_bio_tags=len(label_maps["bio_tags"]),
        num_memory=len(label_maps["memory_types"]),
    ).to(device)
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"🧠 Parameters: {total_params:,}")
    
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    
    best_val_acc = 0.0
    print(f"\n🔥 Training for {EPOCHS} epochs...\n")
    
    for epoch in range(EPOCHS):
        # Train
        model.train()
        total_loss, correct, total = 0.0, 0, 0
        for batch in train_loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            out = model(batch["input_ids"], batch["attention_mask"],
                       batch["intent_labels"], batch["slot_labels"], batch["memory_labels"])
            
            out["loss"].backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            optimizer.zero_grad()
            
            total_loss += out["loss"].item()
            correct += (out["intent_logits"].argmax(-1) == batch["intent_labels"]).sum().item()
            total += len(batch["intent_labels"])
        
        train_acc = correct / total
        
        # Validate
        model.eval()
        val_correct, val_total, slot_correct, slot_total = 0, 0, 0, 0
        with torch.no_grad():
            for batch in val_loader:
                batch = {k: v.to(device) for k, v in batch.items()}
                out = model(batch["input_ids"], batch["attention_mask"])
                val_correct += (out["intent_logits"].argmax(-1) == batch["intent_labels"]).sum().item()
                val_total += len(batch["intent_labels"])
                mask = batch["slot_labels"] != -100
                slot_correct += (out["slot_logits"].argmax(-1)[mask] == batch["slot_labels"][mask]).sum().item()
                slot_total += mask.sum().item()
        
        val_acc = val_correct / max(val_total, 1)
        slot_acc = slot_correct / max(slot_total, 1)
        scheduler.step()
        
        print(f"  Epoch {epoch+1:2d}/{EPOCHS} | Loss: {total_loss/len(train_loader):.4f} | "
              f"Train: {train_acc:.1%} | Val Intent: {val_acc:.1%} | Val Slot: {slot_acc:.1%}")
        
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            save_model(model, tokenizer, label_maps)
    
    print(f"\n✅ Training complete! Best val intent accuracy: {best_val_acc:.1%}")
    
    # Test
    test_model(model, tokenizer, label_maps, device)
    
    print(f"\n📁 Model saved to: {OUTPUT_DIR}/")
    print(f"""
{'='*60}
ON YOUR PC:
{'='*60}

1. Download the '{OUTPUT_DIR}/' folder
2. Copy it to: models/nlu/bert_nlu/
3. Test:
   python -m mace.nlu.bert_nlu

{'='*60}
""")


def save_model(model, tokenizer, label_maps):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    torch.save(model.state_dict(), os.path.join(OUTPUT_DIR, "model.pt"))
    tokenizer.save_pretrained(os.path.join(OUTPUT_DIR, "tokenizer"))
    with open(os.path.join(OUTPUT_DIR, "label_maps.json"), "w") as f:
        json.dump(label_maps, f, indent=2)


def test_model(model, tokenizer, label_maps, device):
    """Quick inference test."""
    print("\n🧪 Testing...")
    model.eval()
    
    tests = [
        "my name is bob",
        "remind me to buy milk tomorrow",
        "hey whats up",
        "what is 5 + 3",
        "I like horror movies",
        "no wait my email is bob@gmail.com",
        "save this and email it to alice",
    ]
    
    for text in tests:
        enc = tokenizer(text, return_tensors="pt", truncation=True, max_length=MAX_LENGTH,
                       padding="max_length", return_offsets_mapping=True)
        offsets = enc.pop("offset_mapping")[0]
        inp = {k: v.to(device) for k, v in enc.items()}
        
        with torch.no_grad():
            out = model(inp["input_ids"], inp["attention_mask"])
        
        # Intent
        probs = torch.softmax(out["intent_logits"], -1)
        intent_id = probs.argmax(-1).item()
        intent = label_maps["id2intent"][str(intent_id)]
        conf = probs[0, intent_id].item()
        
        # Memory
        mem_id = torch.softmax(out["memory_logits"], -1).argmax(-1).item()
        memory = label_maps["id2memory"][str(mem_id)]
        
        # Entities
        slot_ids = out["slot_logits"].argmax(-1)[0]
        entities = {}
        cur_key, cur_spans = None, []
        for i, (s, e) in enumerate(offsets):
            if s == 0 and e == 0:
                continue
            tag = label_maps["id2bio"][str(slot_ids[i].item())]
            if tag.startswith("B-"):
                if cur_key and cur_spans:
                    entities[cur_key] = text[cur_spans[0][0]:cur_spans[-1][1]].strip()
                cur_key = tag[2:]
                cur_spans = [(s.item(), e.item())]
            elif tag.startswith("I-") and cur_key:
                cur_spans.append((s.item(), e.item()))
            else:
                if cur_key and cur_spans:
                    entities[cur_key] = text[cur_spans[0][0]:cur_spans[-1][1]].strip()
                cur_key, cur_spans = None, []
        if cur_key and cur_spans:
            entities[cur_key] = text[cur_spans[0][0]:cur_spans[-1][1]].strip()
        
        ent_str = json.dumps(entities) if entities else "(none)"
        print(f"  {'✅' if conf > 0.5 else '❓'} \"{text}\"")
        print(f"     intent={intent} ({conf:.0%}) memory={memory} entities={ent_str}")


if __name__ == "__main__":
    train()
