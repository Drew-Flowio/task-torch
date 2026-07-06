# Foundry local data directory

Point Foundry at your Milestone backend databases with environment variables:

```bash
export OGM_FOUNDRY_INTAKE_DB="/path/to/intake.db"
export OGM_FOUNDRY_REPOSITORY_DB="/path/to/repository.db"
export OGM_FOUNDRY_VAULT_ROOT="/path/to/vault"
```

If these files are absent, Foundry renders honest empty states instead of fake metrics.
