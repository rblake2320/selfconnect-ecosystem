# External Gate Readiness

Use this command from `selfconnect-ecosystem` to check the remaining gates that
cannot be closed by ordinary unit tests:

```powershell
python scripts\readiness.py --markdown
```

JSON output is available for automation:

```powershell
python scripts\readiness.py --json
```

Failing exit code for CI-style use:

```powershell
python scripts\readiness.py --json --fail-on-blockers
```

## Gates Covered

- key ecosystem repo cleanliness and upstream sync;
- Gemini CLI presence plus non-interactive auth readiness;
- TPM platform attestation readiness through `enterprise.tpm_attestation`;
- latest GitHub MSI artifact workflow status;
- required Windows code-signing secrets for MSI signing.

## Expected Blockers On The Current Workstation

As of 2026-06-21, the executable checks are expected to report:

- Gemini blocked until `GEMINI_API_KEY` or Google ADC is configured;
- TPM platform attestation `NA` on this host with `NCryptCreateClaim ->
  0x80090026`;
- MSI signing blocked until `WINDOWS_SIGNING_CERT_BASE64` and
  `WINDOWS_SIGNING_CERT_PASSWORD` GitHub secrets are configured.

The MSI artifact build/upload workflow itself is expected to pass.

## Open Tracking Issues

The current external blockers are tracked in the private ecosystem repo:

| Gate | Issue |
|---|---|
| Gemini non-interactive auth | https://github.com/rblake2320/selfconnect-ecosystem/issues/2 |
| TPM platform attestation PASS artifact | https://github.com/rblake2320/selfconnect-ecosystem/issues/3 |
| Windows MSI signing secrets and signed artifact | https://github.com/rblake2320/selfconnect-ecosystem/issues/4 |
