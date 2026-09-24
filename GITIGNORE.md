# Recommended ignore rules

The enclosing Prism workspace controls its own persistence allowlist. If the
`edon/` folder is exported into a standalone Git repository, place the following
content in that repository's `.gitignore`:

```gitignore
__pycache__/
*.py[cod]
*.so
.pytest_cache/
.coverage
htmlcov/
build/
dist/
*.egg-info/
.venv/
venv/
.env
var/
*.safetensors
*.ckpt
*.pt
*.pth
*.bin
models/**/final-adapter/
models/**/checkpoint-*/
private-ip/
legal-private/
counsel-workspace/
protected-evaluations/
signed-agreements/
```

Large weights, checkpoints, protected labels, secrets, and raw institutional
data should remain outside Git. Completed invention disclosures, legal advice,
assignments, signatures, filing credentials, and trade-secret values should also
remain outside Git.