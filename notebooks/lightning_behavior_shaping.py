"""
MACE NLU Behavior Shaping Trainer (Llama 3.2 1B)
Uses Unsloth for ultra-fast fine-tuning.
Robust to TRL versions (Polyfills missing classes).

Prompt Format:
Input: {text}
Output: {json}<eos>
"""
import torch
import os
import json
import inspect
from datasets import Dataset
from transformers import TrainingArguments, DataCollatorForLanguageModeling
from unsloth import FastLanguageModel

# Try importing TRL components, handle failures gracefully
try:
    from trl import SFTTrainer
except ImportError:
    raise ImportError("Please run: pip install trl")

# Polyfill DataCollatorForCompletionOnlyLM if missing
try:
    from trl import DataCollatorForCompletionOnlyLM
except ImportError:
    print("⚠️ TRL DataCollatorForCompletionOnlyLM not found. Using local polyfill.")
    
    class DataCollatorForCompletionOnlyLM(DataCollatorForLanguageModeling):
        def __init__(self, response_template, tokenizer, mlm=False):
            super().__init__(tokenizer=tokenizer, mlm=mlm)
            self.response_template = response_template
            self.tokenizer = tokenizer

        def torch_call(self, examples):
            batch = super().torch_call(examples)
            labels = batch["labels"].clone()
            
            # Find the response template in each sequence and mask everything before it
            # This is a simplified version; real one handles tokenization boundaries better
            # For "Output:", it usually tokenizes to specific IDs.
            
            # Efficient heuristic: Mask input dynamically
            # We assume the standard SFTTrainer creates labels=input_ids
            # We enforce -100 on the instruction part.
            
            response_token_ids = self.tokenizer.encode(self.response_template, add_special_tokens=False)
            
            for i in range(len(labels)):
                # Find sequence of response_token_ids
                # This is slow in loop but fine for small/med data
                inds = (labels[i] == response_token_ids[0]).nonzero(as_tuple=True)[0]
                start_idx = -1
                for idx in inds:
                    if len(labels[i]) >= idx + len(response_token_ids):
                        if torch.equal(labels[i][idx:idx+len(response_token_ids)], torch.tensor(response_token_ids, device=labels.device)):
                            start_idx = idx + len(response_token_ids)
                            break
                
                if start_idx != -1:
                    labels[i][:start_idx] = -100
            
            batch["labels"] = labels
            return batch

# ==========================================
# CONFIG
# ==========================================
MODEL_NAME = "unsloth/Llama-3.2-1B-Instruct"
DATA_FILE = "generated_training_data.jsonl"
OUTPUT_DIR = "mace_nlu_llama3.2_1b"
MAX_SEQ_LENGTH = 512
LORA_R = 32           # Increased from 16 → more capacity to learn JSON structure
LORA_ALPHA = 32       # Match rank for stable scaling
LORA_DROPOUT = 0.05
NUM_EPOCHS = 5        # Full passes over ~1063 examples (~665 steps)
LEARNING_RATE = 5e-5  # Lower LR for stable convergence (was 2e-4)
EVAL_SPLIT = 0.1      # 10% held out for validation

def formatting_prompts_func(examples):
    inputs = examples["text"]
    outputs = []
    
    for i in range(len(inputs)):
        obj = {
            "text": examples["text"][i],
            "root_intent": examples["root_intent"][i],
            "memory_type": examples["memory_type"][i],
            "complexity": examples["complexity"][i],
            "entities": examples["entities"][i]
        }
        json_str = json.dumps(obj, ensure_ascii=False)
        outputs.append(json_str)

    texts = []
    for input_text, output_json in zip(inputs, outputs):
        text = f"Input: {input_text}\nOutput: {output_json}" + "<|eot_id|>"
        texts.append(text)
    return {"text": texts}

def sanity_check(model, tokenizer):
    """Run 5 test prompts to verify model outputs valid JSON before export."""
    FastLanguageModel.for_inference(model)
    
    test_inputs = [
        "remind me to buy groceries tomorrow",
        "what is the capital of France",
        "my name is John and I live in New York",
        "delete all my saved notes about cooking",
        "if it rains tomorrow, remind me to take an umbrella",
    ]
    
    print("\n" + "="*60)
    print("🧪 POST-TRAINING SANITY CHECK")
    print("="*60)
    
    passed = 0
    for text in test_inputs:
        prompt = f"Input: {text}\nOutput:"
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.0,
                do_sample=False,
                repetition_penalty=1.15,
            )
        
        response = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        
        # Check if it's valid JSON
        try:
            parsed = json.loads(response)
            status = "✅ VALID JSON"
            passed += 1
        except json.JSONDecodeError:
            status = "❌ INVALID"
        
        print(f"\n📝 Input: {text}")
        print(f"   Output: {response[:200]}")
        print(f"   Status: {status}")
    
    print(f"\n{'='*60}")
    print(f"🏁 Result: {passed}/{len(test_inputs)} passed JSON validation")
    print(f"{'='*60}\n")
    
    return passed

def train():
    print(f"🚀 Loading model: {MODEL_NAME}")
    
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = MODEL_NAME,
        max_seq_length = MAX_SEQ_LENGTH,
        dtype = None,
        load_in_4bit = True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r = LORA_R,
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                          "gate_proj", "up_proj", "down_proj",],
        lora_alpha = LORA_ALPHA,
        lora_dropout = LORA_DROPOUT,
        bias = "none",
        use_gradient_checkpointing = "unsloth",
        random_state = 3407,
        use_rslora = False,
        loftq_config = None,
    )

    # Load Data
    print(f"📂 Loading data from {DATA_FILE}...")
    data = []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
    except FileNotFoundError:
        print(f"❌ Error: {DATA_FILE} not found. Please upload it.")
        return
    
    dataset = Dataset.from_list(data)
    dataset = dataset.map(formatting_prompts_func, batched=True)
    
    # Split into train/eval
    split = dataset.train_test_split(test_size=EVAL_SPLIT, seed=3407)
    train_dataset = split["train"]
    eval_dataset = split["test"]

    print(f"📊 Training on {len(train_dataset)} examples, evaluating on {len(eval_dataset)}")
    
    # Setup Collator
    response_template = "Output:"
    collator = DataCollatorForCompletionOnlyLM(response_template, tokenizer=tokenizer)

    # Detect Argument Name (tokenizer vs processing_class)
    sft_args = {}
    sig = inspect.signature(SFTTrainer.__init__)
    if "processing_class" in sig.parameters:
        sft_args["processing_class"] = tokenizer
    else:
        sft_args["tokenizer"] = tokenizer

    print(f"🔧 Using SFTTrainer args: {list(sft_args.keys())}")

    trainer = SFTTrainer(
        model = model,
        train_dataset = train_dataset,
        eval_dataset = eval_dataset,
        dataset_text_field = "text",
        max_seq_length = MAX_SEQ_LENGTH,
        data_collator = collator,
        dataset_num_proc = 2,
        packing = False,
        args = TrainingArguments(
            per_device_train_batch_size = 2,
            gradient_accumulation_steps = 4,
            num_train_epochs = NUM_EPOCHS,
            learning_rate = LEARNING_RATE,
            fp16 = not torch.cuda.is_bf16_supported(),
            bf16 = torch.cuda.is_bf16_supported(),
            logging_steps = 10,
            eval_strategy = "steps",
            eval_steps = 50,
            save_strategy = "steps",
            save_steps = 100,
            warmup_ratio = 0.1,
            optim = "adamw_8bit",
            weight_decay = 0.01,
            lr_scheduler_type = "cosine",
            seed = 3407,
            output_dir = "outputs",
            report_to = "none",
            load_best_model_at_end = True,
            metric_for_best_model = "eval_loss",
        ),
        **sft_args
    )

    print("🔥 Starting training...")
    trainer.train()

    # Sanity check before saving
    passed = sanity_check(model, tokenizer)
    if passed < 3:
        print("⚠️ WARNING: Less than 3/5 sanity checks passed. Model may need more training.")

    print("💾 Saving model...")
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    
    print("📦 Converting to GGUF...")
    import subprocess
    print("🔄 Upgrading gguf package to avoid MODEL_ARCH errors...")
    subprocess.run(["pip", "install", "--upgrade", "gguf"], capture_output=True)
    subprocess.run(["pip", "install", "--upgrade", "--no-cache-dir",
                     "unsloth_zoo @ git+https://github.com/unslothai/unsloth-zoo.git"], capture_output=True)
    
    try:
        model.save_pretrained_gguf(OUTPUT_DIR, tokenizer, quantization_method = "q4_k_m")
    except Exception as e:
        print(f"⚠️ GGUF conversion failed: {e}")
        print("💡 Try running manually: pip install git+https://github.com/ggerganov/llama.cpp.git@master#subdirectory=gguf-py")

    print(f"✅ Done! Model saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    train()
