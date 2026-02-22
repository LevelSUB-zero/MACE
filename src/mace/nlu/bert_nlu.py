"""
MACE NLU — DistilBERT Multi-Task Model

Two prediction heads on a shared DistilBERT encoder:
  1. Intent Classifier: [CLS] token → intent label
  2. Slot Filler: Each token → BIO entity tag

Zero hallucination. ~5ms inference. Runs on CPU.
"""
import json
import os
import torch
import torch.nn as nn
from typing import Dict, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data", "nlu")
MODEL_DIR = os.path.join(BASE_DIR, "models", "nlu", "bert_nlu", "mace_bert_nlu")
LABEL_MAP_FILE = os.path.join(DATA_DIR, "label_maps.json")


# ================================================================
# Multi-Task Model
# ================================================================
class MaceNLUModel(nn.Module):
    """
    DistilBERT with two heads:
      - Intent head: [CLS] → num_intents
      - Slot head: each token → num_bio_tags
    """
    def __init__(self, num_intents: int, num_bio_tags: int, num_memory: int,
                 model_name: str = "distilbert-base-uncased", dropout: float = 0.1):
        super().__init__()
        from transformers import AutoModel
        
        self.encoder = AutoModel.from_pretrained(model_name)
        hidden_size = self.encoder.config.hidden_size  # 768 for distilbert
        
        # Intent classification head (from [CLS])
        self.intent_head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, num_intents),
        )
        
        # Memory type classification head (from [CLS])
        self.memory_head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_size, num_memory),
        )
        
        # Slot filling head (per token)
        self.slot_head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_size, num_bio_tags),
        )
    
    def forward(self, input_ids, attention_mask, 
                intent_labels=None, slot_labels=None, memory_labels=None):
        """
        Forward pass.
        
        Returns:
            dict with logits and optional losses
        """
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        sequence_output = outputs.last_hidden_state  # (batch, seq_len, hidden)
        cls_output = sequence_output[:, 0, :]  # (batch, hidden) — [CLS] token
        
        intent_logits = self.intent_head(cls_output)    # (batch, num_intents)
        memory_logits = self.memory_head(cls_output)     # (batch, num_memory)
        slot_logits = self.slot_head(sequence_output)     # (batch, seq_len, num_bio)
        
        result = {
            "intent_logits": intent_logits,
            "memory_logits": memory_logits,
            "slot_logits": slot_logits,
        }
        
        # Compute losses if labels provided
        if intent_labels is not None:
            loss_fn = nn.CrossEntropyLoss()
            intent_loss = loss_fn(intent_logits, intent_labels)
            result["intent_loss"] = intent_loss
            
            total_loss = intent_loss
            
            if memory_labels is not None:
                memory_loss = loss_fn(memory_logits, memory_labels)
                result["memory_loss"] = memory_loss
                total_loss = total_loss + 0.5 * memory_loss
            
            if slot_labels is not None:
                # Ignore padding tokens (label = -100)
                slot_loss = nn.CrossEntropyLoss(ignore_index=-100)(
                    slot_logits.view(-1, slot_logits.size(-1)),
                    slot_labels.view(-1),
                )
                result["slot_loss"] = slot_loss
                total_loss = total_loss + slot_loss
            
            result["loss"] = total_loss
        
        return result


# ================================================================
# Label Maps (loaded from JSON)
# ================================================================
_label_maps = None

def _load_label_maps(model_dir=None):
    global _label_maps
    if _label_maps is None:
        # Prefer label maps from model directory (trained together)
        model_lm = os.path.join(model_dir or MODEL_DIR, "label_maps.json")
        if os.path.exists(model_lm):
            with open(model_lm, "r", encoding="utf-8") as f:
                _label_maps = json.load(f)
        elif os.path.exists(LABEL_MAP_FILE):
            with open(LABEL_MAP_FILE, "r", encoding="utf-8") as f:
                _label_maps = json.load(f)
        else:
            raise FileNotFoundError(f"Label maps not found.\nRun: python -m mace.nlu.convert_to_bio")
    return _label_maps


# ================================================================
# Inference Engine
# ================================================================
class BertNLU:
    """
    Production inference engine.
    
    Usage:
        nlu = BertNLU()
        result = nlu.predict("My name is Bob")
        # result = {
        #     "text": "My name is Bob",
        #     "intent": "profile_store",
        #     "intent_confidence": 0.97,
        #     "memory_type": "sem",
        #     "entities": {"name": "Bob"},
        #     "bio_tags": ["O", "O", "O", "B-name"],
        # }
    """
    
    def __init__(self, model_dir: str = None):
        self.model_dir = model_dir or MODEL_DIR
        self.model = None
        self.tokenizer = None
        self.label_maps = None
        self.device = torch.device("cpu")  # Always CPU — fast enough
    
    def _load(self):
        """Lazy-load model and tokenizer."""
        if self.model is not None:
            return
        
        from transformers import AutoTokenizer
        
        self.label_maps = _load_label_maps()
        
        # Load tokenizer
        tokenizer_path = os.path.join(self.model_dir, "tokenizer")
        if os.path.exists(tokenizer_path):
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
        else:
            self.tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
        
        # Load model
        model_path = os.path.join(self.model_dir, "model.pt")
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found: {model_path}\n"
                f"Run: python -m mace.nlu.train_bert_nlu"
            )
        
        num_intents = len(self.label_maps["intents"])
        num_bio = len(self.label_maps["bio_tags"])
        num_memory = len(self.label_maps["memory_types"])
        
        self.model = MaceNLUModel(
            num_intents=num_intents,
            num_bio_tags=num_bio,
            num_memory=num_memory,
        )
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()
        self.model.to(self.device)
    
    def predict(self, text: str) -> Dict:
        """Run inference on a single text input."""
        self._load()
        
        # Tokenize
        encoding = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=128,
            padding="max_length",
            return_offsets_mapping=True,
        )
        
        offset_mapping = encoding.pop("offset_mapping")[0]
        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)
        
        # Inference
        with torch.no_grad():
            output = self.model(input_ids, attention_mask)
        
        # Decode intent
        intent_probs = torch.softmax(output["intent_logits"], dim=-1)
        intent_id = intent_probs.argmax(dim=-1).item()
        intent_conf = intent_probs[0, intent_id].item()
        intent_label = self.label_maps["id2intent"][str(intent_id)]
        
        # Decode memory type
        memory_probs = torch.softmax(output["memory_logits"], dim=-1)
        memory_id = memory_probs.argmax(dim=-1).item()
        memory_label = self.label_maps["id2memory"][str(memory_id)]
        
        # Decode slots (BIO tags)
        slot_probs = torch.softmax(output["slot_logits"], dim=-1)
        slot_ids = slot_probs.argmax(dim=-1)[0]  # (seq_len,)
        
        # Map back to original tokens and extract entities
        entities = {}
        bio_tags = []
        tokens = text.split()
        
        # Align subword tokens back to original words
        current_entity_key = None
        current_entity_tokens = []
        
        for i, (start, end) in enumerate(offset_mapping):
            if start == 0 and end == 0:
                continue  # [CLS], [SEP], [PAD]
            
            tag_id = slot_ids[i].item()
            tag = self.label_maps["id2bio"][str(tag_id)]
            
            if tag.startswith("B-"):
                # Save previous entity
                if current_entity_key and current_entity_tokens:
                    entity_text = text[current_entity_tokens[0][0]:current_entity_tokens[-1][1]]
                    entities[current_entity_key] = entity_text.strip()
                
                current_entity_key = tag[2:]
                current_entity_tokens = [(start.item(), end.item())]
                
            elif tag.startswith("I-") and current_entity_key:
                current_entity_tokens.append((start.item(), end.item()))
                
            else:
                # O tag — save any pending entity
                if current_entity_key and current_entity_tokens:
                    entity_text = text[current_entity_tokens[0][0]:current_entity_tokens[-1][1]]
                    entities[current_entity_key] = entity_text.strip()
                current_entity_key = None
                current_entity_tokens = []
        
        # Don't forget last entity
        if current_entity_key and current_entity_tokens:
            entity_text = text[current_entity_tokens[0][0]:current_entity_tokens[-1][1]]
            entities[current_entity_key] = entity_text.strip()
        
        # Get complexity from config mapping
        from .config import get_default_complexity
        complexity = get_default_complexity(intent_label)
        
        return {
            "text": text,
            "intent": intent_label,
            "intent_confidence": round(intent_conf, 3),
            "memory_type": memory_label,
            "complexity": complexity,
            "entities": entities,
            "is_confident": intent_conf > 0.5,
        }
    
    def predict_batch(self, texts: List[str]) -> List[Dict]:
        """Run inference on multiple texts."""
        return [self.predict(t) for t in texts]


# ================================================================
# Global singleton
# ================================================================
_nlu = None

def get_bert_nlu() -> BertNLU:
    """Get or create the global BertNLU instance."""
    global _nlu
    if _nlu is None:
        _nlu = BertNLU()
    return _nlu


# ================================================================
# CLI test
# ================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("MACE NLU — DistilBERT Inference Test")
    print("=" * 60)
    
    nlu = BertNLU()
    
    tests = [
        "my name is bob",
        "remind me to buy milk tomorrow",
        "hey whats up",
        "what is 5 + 3",
        "I like horror movies",
        "remind me to call mom when i get home",
        "no wait my email is bob@gmail.com",
        "save this and email it to alice",
    ]
    
    for t in tests:
        try:
            r = nlu.predict(t)
            ent_str = json.dumps(r["entities"]) if r["entities"] else "(none)"
            print(f"\n  📝 \"{t}\"")
            print(f"     intent={r['intent']} ({r['intent_confidence']:.0%})")
            print(f"     memory={r['memory_type']} complexity={r['complexity']}")
            print(f"     entities={ent_str}")
        except FileNotFoundError as e:
            print(f"\n  ❌ {e}")
            break
