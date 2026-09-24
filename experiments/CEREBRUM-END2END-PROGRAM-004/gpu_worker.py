"""GPU implementation. Called only by the locked top-level runner."""
import importlib.metadata
import os
from pathlib import Path
import random
import time

from core import (ROOT, cfg, runtime_config, dependencies, verify, verify_parent,
                  tree_hash, read, rows, file_hash, write_json, canonical, parse)


def runtime():
    c=runtime_config()
    versions={k:importlib.metadata.version(k) for k in c["required_packages"]}
    if versions != c["required_packages"]: raise ValueError("pinned packages required")
    import torch
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1 or int(os.environ.get("WORLD_SIZE","1"))!=1:
        raise ValueError("exactly one CUDA GPU required")
    if str(torch.__version__)!="2.8.0+cu129" or torch.version.cuda!="12.9" or torch.cuda.get_device_name(0)!="NVIDIA L4":
        raise ValueError("registered parent-compatible L4 / torch 2.8.0+cu129 runtime required")
    return torch, versions


def runtime_preflight(parent):
    verify(); verify_parent(parent)
    torch, versions=runtime()
    from transformers import AutoTokenizer
    _,_,loss,_,_=dependencies(); c=runtime_config()
    tok=AutoTokenizer.from_pretrained(c["model_name"],revision=c["model_revision"],token=os.environ.get("HF_TOKEN"),use_fast=True)
    loss.loss_self_test()
    audit={"registration_sha256":file_hash(ROOT/"registration.json"),"parent_adapter_sha256":verify_parent(parent),
        "packages":versions,"torch":str(torch.__version__),"cuda":torch.version.cuda,"gpu":torch.cuda.get_device_name(0),
        "loss_value_and_gradient_passed":True,"compute_design":cfg()["compute_design"],"datasets":{}}
    for name in ("train-ordinary","train-boundary","development"):
        encoded=[loss.encode_row(r,tok,c,"trace") for r in rows(ROOT/"prepared"/(name+".jsonl"))]
        audit["datasets"][name]={"records":len(encoded),
            "maximum_sequence_tokens":max(len(x["input_ids"]) for x in encoded),
            "sequence_tokens_per_pass":sum(len(x["input_ids"]) for x in encoded),
            "completion_tokens_per_pass":sum(sum(y!=-100 for y in x["labels"]) for x in encoded),
            "truncations":0,"target_budget_violations":0}
    audit["boundary_to_ordinary_sequence_ratio"]=(audit["datasets"]["train-boundary"]["sequence_tokens_per_pass"]/
        audit["datasets"]["train-ordinary"]["sequence_tokens_per_pass"])
    write_json(ROOT/"results/runtime-readiness.json",audit)
    return audit


def load(parent, trainable=False):
    torch,_=runtime(); verify_parent(parent)
    # Base loading and completion loss remain the registered Program-003 implementations.
    dependencies()
    import gpu as parent_gpu
    from peft import PeftModel, prepare_model_for_kbit_training
    base,tok,dtype=parent_gpu.load_base(torch)
    if trainable: base=prepare_model_for_kbit_training(base,use_gradient_checkpointing=True)
    model=PeftModel.from_pretrained(base,str(parent),is_trainable=trainable)
    return model,tok,dtype


def training_binding(arm):
    return {"arm":arm,"registration_sha256":file_hash(ROOT/"registration.json"),
        "parent_adapter_sha256":cfg()["parent_adapter_sha256"],
        "runtime_sha256":file_hash(ROOT/"results/runtime-readiness.json"),
        "train_sha256":file_hash(ROOT/"prepared"/f"train-{arm}.jsonl")}


def trained(arm):
    verify()
    if arm not in cfg()["arms"]: raise ValueError("unknown arm")
    out=ROOT/"artifacts"/arm; m=read(out/"training.json")
    if m["binding"]!=training_binding(arm) or m["step"]!=cfg()["max_steps"] or m["adapter_sha256"]!=tree_hash(out/"adapter"):
        raise ValueError("trained adapter evidence mismatch")
    return m


def train(arm,parent):
    verify();verify_parent(parent)
    if arm not in cfg()["arms"]: raise ValueError("unknown arm")
    out=ROOT/"artifacts"/arm
    if (out/"training.json").exists(): return trained(arm)
    if (ROOT/"results/selection.json").exists(): raise ValueError("training closed after selection")
    ready=read(ROOT/"results/runtime-readiness.json")
    if ready["registration_sha256"]!=file_hash(ROOT/"registration.json"): raise ValueError("runtime registration changed")
    binding=training_binding(arm);write_json(out/"start.json",binding)
    torch,_=runtime()
    from transformers import Trainer,TrainingArguments
    from transformers.trainer_utils import get_last_checkpoint
    from transformers import set_seed
    c=runtime_config();set_seed(c["training_seed"])
    model,tok,dtype=load(parent,True);model.config.use_cache=False
    _,_,loss,_,_=dependencies()
    encoded=[loss.encode_row(r,tok,c,"trace") for r in rows(ROOT/"prepared"/f"train-{arm}.jsonl")]
    def collate(features):
        width=max(len(r["input_ids"]) for r in features)
        return {k:torch.tensor([r[k]+[pad]*(width-len(r[k])) for r in features],dtype=torch.long)
                for k,pad in (("input_ids",tok.pad_token_id),("attention_mask",0),("labels",-100))}
    class CompletionTrainer(Trainer):
        def __init__(self,*a,**kw):
            super().__init__(*a,**kw);self.model_accepts_loss_kwargs=False
        def compute_loss(self,model,inputs,return_outputs=False,num_items_in_batch=None):
            labels=inputs.pop("labels");output=model(**inputs)
            value=loss.completion_loss(output.logits,labels,c["loss_token_chunk_size"])
            return (value,output) if return_outputs else value
    args=TrainingArguments(output_dir=str(out/"checkpoints"),max_steps=c["max_steps"],num_train_epochs=c["epochs"],
        per_device_train_batch_size=1,gradient_accumulation_steps=c["effective_batch_size"],
        learning_rate=c["learning_rate"],warmup_steps=c["warmup_steps"],weight_decay=c["weight_decay"],
        save_steps=cfg()["save_steps"],save_total_limit=2,logging_steps=4,
        bf16=dtype==torch.bfloat16,fp16=dtype==torch.float16,gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant":False},report_to=[],remove_unused_columns=False,
        optim="paged_adamw_8bit",seed=c["training_seed"],data_seed=c["training_seed"],dataloader_drop_last=False)
    trainer=CompletionTrainer(model=model,args=args,train_dataset=encoded,data_collator=collate)
    checkpoints=out/"checkpoints"
    last=get_last_checkpoint(str(checkpoints)) if checkpoints.exists() else None
    if last:
        for name in ("optimizer.pt","scheduler.pt","trainer_state.json","rng_state.pth"):
            if not (Path(last)/name).is_file():raise ValueError("incomplete checkpoint; do not restart silently")
    result=trainer.train(resume_from_checkpoint=last)
    if trainer.state.global_step!=c["max_steps"]:raise ValueError("wrong final training step")
    trainer.save_model(str(out/"adapter"));tok.save_pretrained(str(out/"adapter"))
    m={"binding":binding,"step":trainer.state.global_step,"adapter_sha256":tree_hash(out/"adapter"),
       "metrics":result.metrics,"resumed":last is not None,
       "runtime_note":"Metrics cover this invocation only when resumed.","binding_authority":False}
    write_json(out/"training.json",m)
    return m


def prediction_binding(arm,split,parent):
    ah=verify_parent(parent) if arm=="parent" else trained(arm)["adapter_sha256"]
    return {"arm":arm,"split":split,"adapter_sha256":ah,
            "registration_sha256":file_hash(ROOT/"registration.json"),
            "input_sha256":file_hash(ROOT/"prepared"/(split+".jsonl")),
            "runtime_sha256":file_hash(ROOT/"results/runtime-readiness.json")}


def read_prefix(path,expected_ids):
    """Return intact bytes and prefix. Only a malformed final line may be recovered."""
    if not path.exists():return [],b""
    parts=path.read_bytes().splitlines(keepends=True); kept=[]; records=[]
    for i,b in enumerate(parts):
        try:r=parse(b.decode())
        except (ValueError,UnicodeDecodeError):
            if i!=len(parts)-1:raise ValueError("corrupt interior prediction")
            break
        records.append(r);kept.append(b)
    ids=[r["case_id"] for r in records]
    if len(ids)>len(expected_ids) or ids!=expected_ids[:len(ids)] or len(set(ids))!=len(ids):
        raise ValueError("prediction prefix mismatch")
    data=b"".join(kept)
    if data and not data.endswith(b"\n"):data+=b"\n"
    return records,data


def validate_predictions(arm,split,parent):
    path=ROOT/"results"/f"{split}-{arm}-predictions.jsonl"
    binding=prediction_binding(arm,split,parent)
    expected={**binding,"predictions_sha256":file_hash(path),"count":cfg()[split]["records"]}
    if read(path.with_suffix(".manifest.json"))!=expected or read(path.with_suffix(".binding.json"))!=binding:
        raise ValueError("prediction binding mismatch")
    data=rows(path); inputs=rows(ROOT/"prepared"/(split+".jsonl"))
    if [r["case_id"] for r in data]!=[r["case_id"] for r in inputs]:raise ValueError("prediction IDs differ")
    return data


def predict(arm,split,parent):
    verify()
    if split not in ("development","confirmation"):raise ValueError("unknown split")
    if arm not in (*cfg()["arms"],"parent"):raise ValueError("unknown model")
    if split=="confirmation":
        from run import verify_access
        verify_access(parent)
    elif (ROOT/"results/confirmation-access.json").exists():raise ValueError("development closed")
    inputs=rows(ROOT/"prepared"/(split+".jsonl"))
    path=ROOT/"results"/f"{split}-{arm}-predictions.jsonl"
    binding=prediction_binding(arm,split,parent);write_json(path.with_suffix(".binding.json"),binding)
    if path.with_suffix(".manifest.json").exists():return validate_predictions(arm,split,parent)
    records,valid=read_prefix(path,[r["case_id"] for r in inputs])
    if path.exists() and valid!=path.read_bytes():
        # Retain the original bytes as crash evidence before recovering only the partial tail.
        from core import write_once
        write_once(path.with_suffix(".interrupted-"+file_hash(path).split(":")[1]),path.read_bytes())
        with path.open("wb") as f:f.write(valid)
    if len(records)<len(inputs):
        torch,_=runtime(); model,tok,_=load(parent,False)
        if arm!="parent":
            from peft import PeftModel
            model=model.unload()
            model=PeftModel.from_pretrained(model,str(ROOT/"artifacts"/arm/"adapter"))
        model.eval(); c=runtime_config();_,trace,loss,_,_=dependencies()
        # Qualification sees oracle targets; generate below receives only source prompt text.
        for r in inputs:loss.encode_row(r,tok,c,"trace")
        with path.open("ab") as f:
            for i,r in enumerate(inputs[len(records):],start=len(records)+1):
                prompt=tok(trace.prompt_for(r["prompt"],"trace"),return_tensors="pt",add_special_tokens=False)
                length=int(prompt["input_ids"].shape[-1]);start=time.monotonic()
                with torch.no_grad():
                    result=model.generate(**{k:v.to(model.device) for k,v in prompt.items()},
                        max_new_tokens=c["max_new_tokens"],do_sample=False,pad_token_id=tok.pad_token_id,eos_token_id=tok.eos_token_id)
                tokens=result[0,length:];ended=bool(len(tokens) and int(tokens[-1])==tok.eos_token_id)
                record={"case_id":r["case_id"],"raw_output":tok.decode(tokens,skip_special_tokens=True).strip(),
                    "ended_with_eos":ended,"hit_generation_limit":len(tokens)>=c["max_new_tokens"] and not ended,
                    "prompt_token_count":length,"generated_token_count":len(tokens),"generation_seconds":time.monotonic()-start}
                f.write((canonical(record)+"\n").encode());f.flush();os.fsync(f.fileno())
                print(f"{split} {arm}: {i}/{len(inputs)}",flush=True)
    write_json(path.with_suffix(".manifest.json"),{**binding,"predictions_sha256":file_hash(path),"count":len(inputs)})
    return validate_predictions(arm,split,parent)