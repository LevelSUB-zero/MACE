# =============================================================
# MACE NLU Fine-Tuning — Google Colab
# =============================================================
# INSTRUCTIONS:
#   1. Open Google Colab → Runtime → T4 GPU
#   2. Paste EACH SECTION into its own cell
#   3. Run cells one by one, top to bottom
#   4. When prompted, upload instruction_data.jsonl
# =============================================================


# %%  ============ CELL 1: INSTALL ============
# Run this FIRST. Restart runtime if Colab asks.
!pip install --no-deps trl peft accelerate bitsandbytes
!pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
!pip install --no-deps xformers


# %%  ============ CELL 2: LOAD MODEL ============
from unsloth import FastLanguageModel
import torch

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/Qwen2.5-3B-Instruct-bnb-4bit",
    max_seq_length = 2048,
    dtype = None,
    load_in_4bit = True,
)
print("✅ Model loaded")


# %%  ============ CELL 3: ADD LORA ============
model = FastLanguageModel.get_peft_model(
    model,
    r = 32,
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj"],
    lora_alpha = 64,
    lora_dropout = 0,
    bias = "none",
    use_gradient_checkpointing = "unsloth",
    random_state = 42,
)
model.print_trainable_parameters()


# %%  ============ CELL 4: UPLOAD DATA ============
from google.colab import files
uploaded = files.upload()  # Upload instruction_data.jsonl here
TRAINING_FILE = list(uploaded.keys())[0]
print(f"✅ Uploaded: {TRAINING_FILE}")


# %%  ============ CELL 5: PREPARE DATASET ============
import json
from datasets import Dataset

data = []
with open(TRAINING_FILE, "r") as f:
    for line in f:
        line = line.strip()
        if line:
            data.append(json.loads(line))

print(f"Loaded {len(data)} examples")

# Format into a single "text" field using ChatML
def format_to_text(example):
    if "messages" in example:
        msgs = example["messages"]
        parts = []
        for m in msgs:
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

dataset = Dataset.from_list([format_to_text(ex) for ex in data])
print(f"✅ Dataset: {len(dataset)} examples")
print(dataset[0]["text"][:300])


# %%  ============ CELL 6: TRAIN ============
from trl import SFTTrainer
from transformers import TrainingArguments

trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = 2048,
    dataset_num_proc = 2,
    packing = False,
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 5,
        num_train_epochs = 3,
        learning_rate = 2e-4,
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(),
        logging_steps = 5,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 42,
        output_dir = "outputs",
        report_to = "none",
    ),
)

stats = trainer.train()
print(f"\n✅ Done! Loss: {stats.metrics['train_loss']:.4f}, Time: {stats.metrics['train_runtime']:.0f}s")


# %%  ============ CELL 7: TEST ============
FastLanguageModel.for_inference(model)

tests = [
    "my name is bob",
    "yo remind me 2 get milk tmrw",
    "no wait, my email is bob@gmail.com",
    "hey whats up",
]

for t in tests:
    inputs = tokenizer.apply_chat_template(
        [
            {"role": "system", "content": "You are MACE-NLU. Parse user input into MemoryAction JSON."},
            {"role": "user", "content": f"Parse: {t}"},
        ],
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
    ).to("cuda")

    out = model.generate(input_ids=inputs, max_new_tokens=512, temperature=0.1, do_sample=True)
    resp = tokenizer.decode(out[0][inputs.shape[1]:], skip_special_tokens=True)
    print(f"\n📝 {t}")
    print(f"📤 {resp[:200]}")


# %%  ============ CELL 8: EXPORT GGUF ============
model.save_pretrained_gguf(
    "mace-nlu",
    tokenizer,
    quantization_method = "q4_k_m",
)
print("✅ GGUF exported")


# %%  ============ CELL 9: DOWNLOAD ============
import glob
gguf = glob.glob("**/*.gguf", recursive=True)
print("GGUF files:", gguf)
if gguf:
    files.download(gguf[0])


# %%  ============ CELL 10: DEPLOY INSTRUCTIONS ============
print("""
After downloading the .gguf file:

1. Create a file called 'Modelfile':

   FROM ./mace-nlu-unsloth.Q4_K_M.gguf

   TEMPLATE \"\"\"<|im_start|>system
   {{ .System }}<|im_end|>
   <|im_start|>user
   {{ .Prompt }}<|im_end|>
   <|im_start|>assistant
   \"\"\"

   SYSTEM "You are MACE-NLU. Parse user input into MemoryAction JSON."
   PARAMETER temperature 0.1
   PARAMETER stop "<|im_end|>"

2. ollama create mace-nlu -f Modelfile
3. ollama run mace-nlu "Parse: my name is bob"
""")
