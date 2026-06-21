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

Contract tests for the readiness checker:

```powershell
npm run test:readiness
```

GitHub Actions runs the same contract test in `.github/workflows/readiness.yml`.
The live readiness report is smoke-run there, but external blockers are not
treated as CI failures unless `--fail-on-blockers` is used intentionally.

## Gates Covered

- key ecosystem repo cleanliness and upstream sync;
- Gemini CLI presence plus persistent non-interactive auth readiness;
- Gemini auth variables in Process, User, and Machine environment scopes,
  without printing secret values;
- TPM platform attestation readiness through `enterprise.tpm_attestation`;
- latest GitHub MSI artifact workflow status;
- required Windows code-signing secrets for MSI signing.

## Expected Blockers On The Current Workstation

As of 2026-06-21, the executable checks are expected to report:

- Gemini persistent readiness blocked until a non-OAuth path is configured
  outside the repo. Gemini CLI personal/free/Pro routing stopped serving
  requests on 2026-06-18 and moved to Antigravity CLI. Enterprise/Cloud/API-key
  paths remain supported. For scale testing, use a paid Cloud/API route rather
  than `oauth-personal`: persistent `GEMINI_API_KEY`/`GOOGLE_API_KEY`, Google
  ADC, or Gemini Enterprise Agent Platform variables such as
  `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and
  `GOOGLE_GENAI_USE_ENTERPRISE=true`. Core ephemeral API-key tests have already
  passed Gemini preflight and real visible-window ACK runs;
- Gemini 10/15/20 scale blocked until the API key/project has enough Gemini
  request quota; the 5-Gemini rung passed, but the 10-Gemini rung hit provider
  quota. Treat quota as project/billing-tier capacity, not a SelfConnect
  transport failure;
- TPM platform attestation `NA` on this host with `NCryptCreateClaim ->
  0x80090026`. This means the current firmware/provider does not support the
  requested platform claim path. Viable PASS paths are a supported discrete TPM
  or a separate attestation service path such as Azure Attestation, documented
  distinctly from the NCrypt claim embodiment;
- MSI signing blocked until a signing provider is configured. Traditional
  certificate secrets are one route, but the preferred low-friction production
  path is Azure Artifact Signing/Trusted Signing; SignPath Foundation is a
  possible free OSS path if publisher-name tradeoffs are acceptable.

The MSI artifact build/upload workflow itself is expected to pass.

## Open Tracking Issues

The current external blockers are tracked in the private ecosystem repo:

| Gate | Issue |
|---|---|
| Gemini non-interactive auth | https://github.com/rblake2320/selfconnect-ecosystem/issues/2 |
| Gemini 10/15/20 scale quota | https://github.com/rblake2320/selfconnect-ecosystem/issues/5 |
| TPM platform attestation PASS artifact | https://github.com/rblake2320/selfconnect-ecosystem/issues/3 |
| Windows MSI signing secrets and signed artifact | https://github.com/rblake2320/selfconnect-ecosystem/issues/4 |

## Current External References

- Gemini CLI transition to Antigravity CLI:
  https://github.com/google-gemini/gemini-cli/discussions/27274
- Gemini API rate limits and usage tiers:
  https://ai.google.dev/gemini-api/docs/rate-limits
- Gemini Enterprise Agent Platform quotas:
  https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/quotas
- Gemini Enterprise Agent Platform quickstart:
  https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/start
- Azure Artifact Signing pricing:
  https://azure.microsoft.com/en-us/pricing/details/artifact-signing/
- Azure Artifact Signing quickstart:
  https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart
