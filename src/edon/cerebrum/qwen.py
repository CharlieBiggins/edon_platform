"""Local Qwen inference boundary for non-binding C1 operations proposals.

The module intentionally imports the optional GPU stack lazily. Importing EDON,
running the deterministic reference provider, or validating the repository does
not require transformers, PEFT, torch, or bitsandbytes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Protocol

from edon.common.hashing import canonical_json

from .operations import OperationsProposalError, PROPOSAL_REQUIREMENTS


class TextGenerationBackend(Protocol):
    """Minimal backend contract used by the Qwen operations provider."""

    def generate(self, messages: list[dict[str, str]]) -> str: ...


SYSTEM_PROMPT = """You are C1, the non-authoritative learned model inside the Cerebrum System.
You are acting as an institutional operations planner.
You may propose exactly one shadow-mode operation. You have no authority to execute,
commit, authorize, sign, approve, or mutate institutional state. Never emit an
authorization reference, execution token, kernel token, signature, commit flag, or
claim of binding authority. Return one JSON object and no surrounding prose.

The object must contain:
- proposal_type: one allowed proposal type
- payload: an object containing the fields required for that proposal type
- rationale: a concise explanation of at least ten characters
- confidence: a number from 0 to 1
- binding_authority: false

When evidence is insufficient or no safe proposal exists, return ABSTAIN with an
empty payload. Do not invent identifiers that are absent from the supplied context.
"""


def _parse_json_object(text: str) -> dict[str, Any]:
    """Accept exactly one JSON object, optionally inside a JSON code fence."""

    candidate = str(text).strip()
    if candidate.startswith("```json") and candidate.endswith("```"):
        candidate = candidate[7:-3].strip()
    elif candidate.startswith("```") and candidate.endswith("```"):
        candidate = candidate[3:-3].strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise OperationsProposalError("Qwen provider output is not one JSON object") from exc
    if not isinstance(value, dict):
        raise OperationsProposalError("Qwen provider output must be a JSON object")
    return value


class QwenOperationsProvider:
    """Render a shadow context for Qwen and fail closed on generation errors."""

    def __init__(self, backend: TextGenerationBackend, *, fail_closed: bool = True):
        self.backend = backend
        self.fail_closed = bool(fail_closed)
        self.last_error: str | None = None

    @staticmethod
    def messages(context: dict[str, Any]) -> list[dict[str, str]]:
        requirements = {
            proposal_type: sorted(fields)
            for proposal_type, fields in sorted(PROPOSAL_REQUIREMENTS.items())
        }
        request = {
            "mode": "SHADOW",
            "binding_authority": False,
            "allowed_proposal_types": sorted(PROPOSAL_REQUIREMENTS),
            "required_payload_fields": requirements,
            "context": context,
        }
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": canonical_json(request)},
        ]

    @staticmethod
    def _closed_abstention(reason: str) -> dict[str, Any]:
        return {
            "proposal_type": "ABSTAIN",
            "payload": {},
            "rationale": "The learned provider failed closed because its output was invalid or unavailable.",
            "confidence": 0.0,
            "binding_authority": False,
            "provider_diagnostic": reason[:500],
        }

    @staticmethod
    def _validate_grounding(proposal: dict[str, Any], context: dict[str, Any]) -> None:
        """Require dispatch recommendations to match a feasible context row."""

        if str(proposal.get("proposal_type", "")).upper() != "DISPATCH_STEP":
            return
        payload = proposal.get("payload")
        if not isinstance(payload, dict):
            raise OperationsProposalError("dispatch payload must be an object")
        assignments = context.get("assignment_proposals")
        if not isinstance(assignments, list):
            raise OperationsProposalError("dispatch proposal has no assignment context")
        grounded = any(
            isinstance(row, dict)
            and row.get("dispatchable") is True
            and row.get("plan_id") == payload.get("plan_id")
            and row.get("step_id") == payload.get("step_id")
            and row.get("recommended_agent_id") == payload.get("agent_id")
            for row in assignments
        )
        if not grounded:
            raise OperationsProposalError(
                "dispatch proposal is not grounded in a feasible assignment context row"
            )

    def propose(self, context: dict[str, Any]) -> dict[str, Any]:
        try:
            raw = self.backend.generate(self.messages(context))
            proposal = _parse_json_object(raw)
            self._validate_grounding(proposal, context)
            self.last_error = None
            return proposal
        except Exception as exc:
            if not self.fail_closed:
                if isinstance(exc, OperationsProposalError):
                    raise
                raise OperationsProposalError("Qwen generation failed") from exc
            self.last_error = f"{type(exc).__name__}: {exc}"
            return self._closed_abstention(self.last_error)


class TransformersQwenBackend:
    """Lazy local Transformers/PEFT backend suitable for a Qwen base plus LoRA."""

    def __init__(
        self,
        model_name: str,
        *,
        adapter_path: str | Path | None = None,
        load_in_4bit: bool = True,
        max_input_tokens: int = 4096,
        max_new_tokens: int = 1536,
        local_files_only: bool = False,
    ):
        self.model_name = str(model_name).strip()
        if not self.model_name:
            raise OperationsProposalError("Qwen model name is required")
        self.adapter_path = Path(adapter_path).expanduser() if adapter_path else None
        if self.adapter_path is not None and not self.adapter_path.exists():
            raise OperationsProposalError(f"Qwen adapter path does not exist: {self.adapter_path}")
        self.load_in_4bit = bool(load_in_4bit)
        self.max_input_tokens = int(max_input_tokens)
        self.max_new_tokens = int(max_new_tokens)
        self.local_files_only = bool(local_files_only)
        if self.max_input_tokens < 512:
            raise OperationsProposalError("max_input_tokens must be at least 512")
        if self.max_new_tokens < 64:
            raise OperationsProposalError("max_new_tokens must be at least 64")
        self._tokenizer: Any = None
        self._model: Any = None
        self._torch: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise OperationsProposalError(
                "local Qwen requires torch and transformers; install the frozen GPU runtime"
            ) from exc

        model_kwargs: dict[str, Any] = {
            "device_map": "auto",
            "local_files_only": self.local_files_only,
        }
        if self.load_in_4bit:
            try:
                from transformers import BitsAndBytesConfig
            except ImportError as exc:
                raise OperationsProposalError(
                    "4-bit Qwen loading requires a transformers build with BitsAndBytesConfig"
                ) from exc
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
            )
        elif torch.cuda.is_available():
            model_kwargs["torch_dtype"] = torch.bfloat16

        tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            local_files_only=self.local_files_only,
        )
        model = AutoModelForCausalLM.from_pretrained(self.model_name, **model_kwargs)
        if self.adapter_path is not None:
            try:
                from peft import PeftModel
            except ImportError as exc:
                raise OperationsProposalError("loading a C1 LoRA requires PEFT") from exc
            model = PeftModel.from_pretrained(model, str(self.adapter_path), is_trainable=False)
        model.eval()
        self._torch = torch
        self._tokenizer = tokenizer
        self._model = model

    def generate(self, messages: list[dict[str, str]]) -> str:
        self._load()
        tokenizer = self._tokenizer
        model = self._model
        torch = self._torch
        try:
            rendered = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            rendered = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        inputs = tokenizer(
            rendered,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_input_tokens,
        )
        device = next(model.parameters()).device
        inputs = {name: tensor.to(device) for name, tensor in inputs.items()}
        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )
        new_tokens = output[0, inputs["input_ids"].shape[1]:]
        return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def configured_operations_provider(
    environ: Mapping[str, str] | None = None,
) -> tuple[Any, str]:
    """Build the default deterministic or explicitly enabled local Qwen provider."""

    values = os.environ if environ is None else environ
    provider_name = values.get(
        "EDON_C1_PROVIDER",
        values.get("EDON_CEREBRUM_PROVIDER", "deterministic"),
    ).strip().lower()
    if provider_name in {"deterministic", "reference"}:
        from .operations import DeterministicShadowProvider

        return DeterministicShadowProvider(), "deterministic-shadow-provider:v1"
    if provider_name not in {"qwen", "qwen-transformers", "local-qwen"}:
        raise OperationsProposalError(f"unsupported EDON_C1_PROVIDER: {provider_name}")

    lineage = values.get(
        "EDON_C1_MODEL_LINEAGE",
        values.get("EDON_CEREBRUM_MODEL_LINEAGE", ""),
    ).strip()
    if not lineage:
        raise OperationsProposalError(
            "EDON_C1_MODEL_LINEAGE or historical EDON_CEREBRUM_MODEL_LINEAGE is required "
            "when the learned provider is enabled"
        )
    backend = TransformersQwenBackend(
        values.get(
            "EDON_C1_MODEL",
            values.get("EDON_CEREBRUM_MODEL", "Qwen/Qwen3-4B-Instruct-2507"),
        ),
        adapter_path=values.get("EDON_C1_ADAPTER") or values.get("EDON_CEREBRUM_ADAPTER") or None,
        load_in_4bit=values.get(
            "EDON_C1_LOAD_IN_4BIT", values.get("EDON_CEREBRUM_LOAD_IN_4BIT", "1")
        ) not in {"0", "false", "False"},
        max_input_tokens=int(values.get(
            "EDON_C1_MAX_INPUT_TOKENS",
            values.get("EDON_CEREBRUM_MAX_INPUT_TOKENS", "4096"),
        )),
        max_new_tokens=int(values.get(
            "EDON_C1_MAX_NEW_TOKENS",
            values.get("EDON_CEREBRUM_MAX_NEW_TOKENS", "1536"),
        )),
        local_files_only=values.get(
            "EDON_C1_LOCAL_FILES_ONLY",
            values.get("EDON_CEREBRUM_LOCAL_FILES_ONLY", "0"),
        ) in {"1", "true", "True"},
    )
    return QwenOperationsProvider(backend, fail_closed=True), lineage