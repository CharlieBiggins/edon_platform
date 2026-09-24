# External GPU development rehearsal

Use an isolated CUDA environment with compatible releases of PyTorch,
Transformers, Datasets, PEFT, Accelerate, and bitsandbytes. Do not install those
dependencies into the EDON repository workspace.

The commands below rehearse the Qwen pipeline against the now-open proxy target.
They cannot establish the confirmatory Cerebrum claim. Run preflight after
provisioning; it will remain blocked until a fresh custodian-held target is
registered:

```bash
python preflight.py
```

Train the four registered adapters:

```bash
python train_lora.py --condition control --seed 26082341 --output-dir runs/control-26082341
python train_lora.py --condition control --seed 26082342 --output-dir runs/control-26082342
python train_lora.py --condition platform002 --seed 26082341 --output-dir runs/platform002-26082341
python train_lora.py --condition platform002 --seed 26082342 --output-dir runs/platform002-26082342
```

Produce label-free predictions:

```bash
python predict_qwen.py --adapter runs/control-26082341/adapter --output predictions/qwen-control-seed-26082341.jsonl
python predict_qwen.py --adapter runs/control-26082342/adapter --output predictions/qwen-control-seed-26082342.jsonl
python predict_qwen.py --adapter runs/platform002-26082341/adapter --output predictions/qwen-platform002-seed-26082341.jsonl
python predict_qwen.py --adapter runs/platform002-26082342/adapter --output predictions/qwen-platform002-seed-26082342.jsonl
```

Freeze, then score once:

```bash
python freeze_qwen_predictions.py
python score_qwen.py
```

Do not report this rehearsal as protected transfer. A confirmatory run needs a
new instrument and external custody record before any label access.