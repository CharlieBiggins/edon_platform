# Environment configuration

Never commit live tokens, adapter credentials, or institutional secrets.

## API authentication

```bash
export EDON_API_KEY=replace-with-a-random-token-at-least-16-characters
```

## Default deterministic provider

```bash
export EDON_CEREBRUM_PROVIDER=deterministic
```

## CEREBRUM-BUILD-001 local Qwen provider

```bash
export EDON_CEREBRUM_PROVIDER=qwen
export EDON_CEREBRUM_MODEL=Qwen/Qwen3-4B-Instruct-2507
export EDON_CEREBRUM_ADAPTER=/persistent/models/cerebrum-build-001/final-adapter
export EDON_CEREBRUM_MODEL_LINEAGE=cerebrum-build-001:replace-with-frozen-hash
export EDON_CEREBRUM_LOAD_IN_4BIT=1
export EDON_CEREBRUM_MAX_INPUT_TOKENS=4096
export EDON_CEREBRUM_MAX_NEW_TOKENS=1536
export EDON_CEREBRUM_LOCAL_FILES_ONLY=0
```

The learned provider remains shadow-only and cannot mint execution authority.