# Competitive And Patent Watch

Last updated: 2026-06-18 07:28:24 -05:00

Private internal planning note. Not legal advice. Do not copy this file into public marketing, public repos, investor decks, or patent filings before counsel review.

## Purpose

SelfConnect should run its own race while watching competitors and patent publications closely enough to avoid being boxed in. The watch process should identify:

- what competitors publicly claim;
- what patent publications appear near SelfConnect's claim families;
- what design-arounds a large company might try;
- what evidence or implementation SelfConnect should build next.

## Watch Cadence

| Cadence | Action |
| --- | --- |
| Weekly | Check named competitors, public pages, GitHub releases, and major AI agent framework changes. |
| Monthly | Search patents and publications for AI-to-AI desktop control, OS-native agent mesh, UI automation, MCP desktop bridges, governed agent execution, WORM/TPM audit, and browser control. |
| Before any filing | Freeze dated evidence: source URLs, screenshots/PDFs, hashes, commit SHAs, test artifacts, and claim-family map. |
| Before public demos | Review whether the demo discloses unfiled claim details. |

## Current Named Watch Targets

| Target | What to watch | SelfConnect posture |
| --- | --- | --- |
| Project Lancelot / UAB | Public claims around Universal App Bridge, desktop control, MCP tools, spatial map, browser/CDP/extension control, AI-to-AI desktop automation, governance claims, and patent-pending statements. | Do not compete only on breadth. Differentiate on OS-native peer mesh, kernel/SID-bound authority, fail-closed target guard, echo-filtered delivery, birth/session continuity, and no-CDP browser UIA proof where applicable. |
| Microsoft Windows agent platform | Windows MCP, On-Device Registry, Agent ID, Agent Workspace, Windows AI APIs, WinUI/App SDK packaging, service and security posture changes. | Where Microsoft standardizes the platform, become compatible. Preserve SelfConnect's local OS-native transport and evidence chain as the differentiator. |
| OpenAI / Anthropic / Google / Gemini agent tooling | Tool calling, desktop control, computer use, skills, MCP support, handoffs, tracing, and governance features. | Use their agent surfaces as participants in the mesh; avoid making SelfConnect dependent on any one vendor. |
| Desktop automation and RPA vendors | UIA, CDP, accessibility, browser automation, computer-use, screen reading, and verification claims. | SelfConnect's claim is not generic automation. Keep focus on AI peer communication, verified readback, routing identity, and governance profiles. |

Sources checked on 2026-06-18:

- `https://projectlancelot.dev/competitive-matrix/`
- `https://projectlancelot.dev/uab.html`

## SelfConnect Claim Families To Keep Ahead

| Claim family | Current evidence direction | Workaround risk | Next defensive action |
| --- | --- | --- | --- |
| OS-identity-bound role leases | Named pipe DACL + impersonation + owner SID hash + role/birth/generation tuple. | Competitor uses API keys, process IDs, or localhost auth and argues it is equivalent. | Keep evidence showing no bearer secret exists to steal, and stale/wrong tuple denial. |
| Fail-closed target guard | HWND/PID/exe/class/title live match before send; not-self check; terminal class checks. | Competitor invokes UI element names or PIDs and accepts wrong-target risk. | Keep wrong PID, wrong class, stale HWND, and self-target denial tests. |
| Echo-filtered readback | Nonce/hash echo suppression with UIA readback records. | Competitor says it reads replies but does not distinguish own injected text from external output. | Keep redacted PASS artifacts showing echo-only, mixed echo/output, and external output classification. |
| Channel-router composition | Route by surface: terminal `WM_CHAR`, browser UIA `ValuePattern`/`InvokePattern`, control plane pipe/registry, optional ETW. | Competitor claims adaptive automation cascade broadly. | Frame SelfConnect around AI peer-message semantics and verified delivery, not generic app operation breadth. |
| Browser without CDP/API/MCP control path | Chrome/Gmail proof using UIA control path, with no Gmail API, no CDP/WebDriver, no extension, no MCP send. | Competitor uses CDP, extension, or browser API and claims same outcome. | Keep the channel-boundary finding: Chromium ignored `WM_CHAR`/keyboard path while UIA worked. |
| Birth/session continuity | `birth_id` + generation + compact handoff + mesh registry. | Competitor uses role names only and loses identity on migration/compaction. | Build compact-handoff as a first-class normal-mode command and proof. |
| Three governance profiles | Normal remains fast; enterprise adds controls; government adds restricted-environment evidence and approval requirements. | Competitor forces one policy model for all users or makes personal mode unusable. | Keep profile docs and tests that prove normal mode remains low-friction. |
| TPM/WORM evidence | TPM adapter, WORM fail-closed government mode, MSI installer, ATO evidence package. | Competitor adds software-only audit ledger and calls it compliance. | Get physical TPM PASS artifact and real S3/R2 Object Lock replication artifact. |

## Big-Company Workaround Checklist

Assume a Fortune 100 competitor will try to avoid claims by changing vocabulary and transport details. Watch for these moves:

| Workaround attempt | Defensive response |
| --- | --- |
| Replace named pipes with local HTTP and API keys. | Emphasize OS-kernel caller identity and non-transferable SID authority, not just IPC. |
| Replace `WM_CHAR` with SendInput, clipboard, accessibility, CDP, or screenshots. | Emphasize adaptive channel routing plus verified delivery/readback, not a single input primitive. |
| Use MCP tools for all actions. | Emphasize MCP as optional adapter; SelfConnect actions do not require MCP in the control path. |
| Track role names only. | Emphasize durable `birth_id`, generation, owner SID hash, and migration proof. |
| Add audit logs after the fact. | Emphasize pre-action gate + action + readback + signed evidence composition. |
| Use UIA to click browser controls. | Emphasize the composed browser channel boundary proof and no-CDP/no-extension/no-WebDriver path with delivery verification. |
| Claim government readiness from policy files. | Emphasize WORM, TPM, service mode, ATO evidence, and fail-closed government configuration. |

## Watch Record Template

Use this format for each new competitor, patent, paper, release, or public claim:

```markdown
## YYYY-MM-DD — Source Name

- Source URL:
- Archive/screenshot/PDF path:
- Hash:
- Public/private:
- Short summary:
- SelfConnect overlap:
- Claim families affected:
- Threat level: red / yellow / green
- Design-around pressure:
- Recommended action:
- Owner:
- Follow-up date:
```

## Threat Levels

| Level | Meaning | Action |
| --- | --- | --- |
| Red | Direct overlap with a SelfConnect claim family or competitor appears to have filed/published near the same composition. | Preserve evidence, brief counsel, add implementation proof or claim variant immediately. |
| Yellow | Adjacent feature or broad wording that could be used in a rejection or marketing comparison. | Add to matrix, build clearer differentiating evidence, monitor monthly. |
| Green | Interesting but outside current SelfConnect claims. | Track lightly; do not chase. |

## Operating Principle

Do not let competitor matrices define SelfConnect's race. SelfConnect should keep advancing the parts already proving differentiated value:

- normal-mode AI-to-AI mesh that stays fast for daily use;
- verified delivery and echo-filtered readback;
- durable birth/session identity across migration and compaction;
- OS-native control paths that do not require MCP, browser extensions, CDP, or public APIs;
- enterprise/government governance that can be turned on without contaminating normal mode.
