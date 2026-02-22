# ============================================================
# MACE NLU Fine-Tuning — Lightning AI Studio
# ============================================================
# Model: Qwen2.5-1.5B-Instruct (fits 2GB VRAM GPUs)
#
# STEPS:
# 1. Lightning AI → New Studio → T4 GPU
# 2. Upload: this script + instruction_data.jsonl
# 3. Terminal:
#    pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
#    pip install --no-deps xformers trl peft accelerate bitsandbytes
#    huggingface-cli login   (paste token from hf.co/settings/tokens)
#    python lightning_studio_finetune.py
# ============================================================

import os
import json
import torch
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import Dataset

# =================== CONFIG ===================
# Qwen2.5-1.5B: Best small model for structured JSON output
# GGUF Q4_K_M = ~1GB → fits your 2GB GTX 960M
MODEL_NAME = "unsloth/Qwen2.5-1.5B-Instruct-bnb-4bit"
MAX_SEQ_LENGTH = 2048
TRAINING_FILE = "instruction_data.jsonl"
OUTPUT_NAME = "mace-nlu"

# =================== 1. LOAD MODEL ===================
print(f"🚀 Loading {MODEL_NAME}...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_NAME,
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=None,
    load_in_4bit=True,
)
print(f"✅ Model loaded! GPU: {torch.cuda.memory_allocated()/1024**3:.1f} GB")

# =================== 2. ADD LORA ===================
model = FastLanguageModel.get_peft_model(
    model,
    r=16,              # Lower rank for smaller model
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_alpha=32,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)
model.print_trainable_parameters()

# =================== 3. LOAD DATA ===================
if not os.path.exists(TRAINING_FILE):
    raise FileNotFoundError(
        f"❌ Upload '{TRAINING_FILE}' first!\n"
        f"   (from your PC: data/nlu/instruction_data.jsonl)"
    )

data = []
with open(TRAINING_FILE, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                continue

print(f"📊 Loaded {len(data)} examples")

def format_chatml(example):
    if "messages" in example:
        parts = []
        for m in example["messages"]:
            parts.append(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>")
        return {"text": "\n".join(parts)}
    else:
        sys = example.get("system", "You are MACE-NLU.")
        inp = example.get("input", "")
        out = example.get("output", "")
        return {"text": (
            f"<|im_start|>system\n{sys}<|im_end|>\n"
            f"<|im_start|>user\n{inp}<|im_end|>\n"
            f"<|im_start|>assistant\n{out}<|im_end|>"
        )}

dataset = Dataset.from_list([format_chatml(ex) for ex in data])
print(f"✅ Dataset: {len(dataset)} examples")

# =================== 4. TRAIN ===================
print("🔥 Training...")
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LENGTH,
    dataset_num_proc=2,
    packing=False,
    args=TrainingArguments(
        per_device_train_batch_size=4,     # Can use larger batch with 1.5B
        gradient_accumulation_steps=2,
        warmup_steps=5,
        num_train_epochs=5,                # More epochs for smaller model
        learning_rate=3e-4,                # Slightly higher LR for small model
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=5,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",        # Cosine works better for small models
        seed=42,
        output_dir="outputs",
        report_to="none",
    ),
)

stats = trainer.train()
print(f"\n✅ Training done! Loss: {stats.metrics['train_loss']:.4f}")

# =================== 5. TEST ===================
print("\n🧪 Testing...")
FastLanguageModel.for_inference(model)

tests = [
    "my name is bob",
    "yo remind me 2 get milk tmrw",
    "remind me to call mom when i get home",
    "no wait my email is bob@gmail.com",
    "hey whats up",
    "what is 5 + 3",
    "put that in the other folder",
]

for t in tests:
    inputs = tokenizer.apply_chat_template(
        [
            {"role": "system", "content": "You are MACE-NLU. Parse user input into MemoryAction JSON."},
            {"role": "user", "content": f"Parse: {t}"},
        ],
        tokenize=True, add_generation_prompt=True, return_tensors="pt",
    ).to("cuda")
    out = model.generate(input_ids=inputs, max_new_tokens=512, temperature=0.1, do_sample=True)
    resp = tokenizer.decode(out[0][inputs.shape[1]:], skip_special_tokens=True)
    print(f"  📝 {t}")
    print(f"  📤 {resp[:250]}\n")

# =================== 6. EXPORT TO HUGGINGFACE ===================
print("\n📦 Pushing to HuggingFace Hub...")
print("   (run 'huggingface-cli login' first if not logged in)")

try:
    from huggingface_hub import HfApi
    api = HfApi()
    user_info = api.whoami()
    hf_user = user_info["name"]
    hf_repo = f"{hf_user}/mace-nlu-1.5B-GGUF"

    model.push_to_hub_gguf(
        hf_repo,
        tokenizer,
        quantization_method="q4_k_m",
    )

    print(f"""
{'='*60}
✅ PUSHED TO HUGGINGFACE: {hf_repo}
{'='*60}

ON YOUR PC, RUN THESE COMMANDS:

  ollama pull hf.co/{hf_repo}
  ollama run hf.co/{hf_repo} "Parse: my name is bob"

  # To give it a short name:
  ollama cp hf.co/{hf_repo} mace-nlu
  ollama run mace-nlu "Parse: my name is bob"

{'='*60}
""")

except Exception as e:
    print(f"⚠️ HuggingFace push failed: {e}")
    print("Saving GGUF locally instead...")

    model.save_pretrained_gguf(OUTPUT_NAME, tokenizer, quantization_method="q4_k_m")

    import glob
    gguf_files = glob.glob("**/*.gguf", recursive=True)
    print(f"📁 GGUF files: {gguf_files}")
    print(f"""
{'='*60}
MANUAL DOWNLOAD STEPS:
{'='*60}

1. Right-click the .gguf file in file browser → Download
2. On your PC, put it in a folder and create 'Modelfile':

   FROM ./mace-nlu-unsloth.Q4_K_M.gguf
   SYSTEM "You are MACE-NLU. Parse input into MemoryAction JSON."
   PARAMETER temperature 0.1
   PARAMETER stop "<|im_end|>"

3. Run:
   ollama create mace-nlu -f Modelfile
   ollama run mace-nlu "Parse: my name is bob"

{'='*60}
""")
