# Release scripts

Release tooling validates claims, licenses, manifests, secret scans, frozen
results, public artifact allowlists, and sanitized IP-governance status.

Validate the IP package:

```bash
python scripts/release/validate_ip_governance.py
```

This structural check is not legal review. A passing result does not establish
patentability, filing status, ownership, trademark rights, secrecy, freedom to
operate, or permission to publish a particular release.