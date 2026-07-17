# Agent Mesh Coordination Protocol

Last updated: 2026-06-18

This protocol exists to stop agents from wasting tokens by narrating locally when they are supposed to communicate over the SelfConnect mesh.

## Core Rule

When one mesh agent is asked to talk to another mesh agent, the response must be sent into the target agent's terminal through SelfConnect transport.

Do not answer by writing a long response in your own terminal and waiting for another agent or Ron to scrape it. That burns tokens, hides state in the wrong window, and breaks the point of SelfConnect.

## Required Reply Behavior

| Situation | Correct behavior |
| --- | --- |
| Codex sends Claude a mesh packet | Claude sends the answer into Codex's terminal using SelfConnect. |
| Claude sends Codex a mesh packet | Codex sends the answer into Claude's terminal using SelfConnect. |
| Gemini sends either agent a mesh packet | The receiver replies into Gemini's registered terminal using SelfConnect. |
| Ron asks agents to coordinate | Agents exchange compact packets with each other first; owner-facing summaries wait until Ron asks. |

The sender's local terminal should show only a minimal local status such as `SENT`, `ACK`, or a one-line blocker.

## Token Discipline

During coordination mode:

- Keep mesh packets to 8 lines or fewer unless the receiving agent asks for a longer artifact.
- Do not narrate the plan to Ron unless he explicitly asks for an owner-facing summary.
- Do not run multi-minute investigations during sync. Send current state first, then ask for assignment.
- Do not read or paste full terminal transcripts when a compact status packet is enough.
- Do not push, rebase, or clean a dirty repo just because another agent asked for status.
- Update the mesh registry with current task/status so other agents do not poll for state.

## Targeting Requirement

Before sending to another agent, use the mesh registry to get the active role, `birth_id`, HWND, PID, title, class, and profile. Role names can collide or migrate; `birth_id` identifies the actual terminal instance.

Example:

```powershell
python -m sc_mesh_registry list
python -m sc_cli guard --hwnd 28443124 --expect-pid 16680 --expect-exe WindowsTerminal.exe --expect-class CASCADIA_HOSTING_WINDOW_CLASS --expect-title "codex 1"
```

Then send with guarded expectations:

```powershell
python -m sc_cli send --hwnd 28443124 --text "[CLAUDE-1 -> CODEX-1] ACK. Waiting." --submit --allow-input --expect-pid 16680 --expect-exe WindowsTerminal.exe --expect-class CASCADIA_HOSTING_WINDOW_CLASS --expect-title "codex 1" --char-delay 0.01
```

## Auto-Submit Transport (new capability, 2026-07-17)

Mesh packets now **auto-submit**: the message is typed into the peer's console
**and** submitted, with no human pressing Enter. Previously `WriteConsoleInputW`
only *typed* the packet — it sat unsent in the peer's composer until a human hit
Enter, because a TUI (e.g. Codex) only submits a line when its window has focus.
Reporting "SENT" at that point was false: typed ≠ delivered.

Correct transport (see `mesh_send.py`):

1. Type the text into the peer console via `WriteConsoleInputW`.
2. **Submit**: briefly `SetForegroundWindow(peer)` + send a hardware `Enter`
   via `SendInput` (accepted as submit), then restore the previous foreground
   window.

Guards (as implemented in `mesh_send.py`): before typing and again before the
focus+Enter it validates the peer window is a live window, its **PID matches**,
and — when a title argument is supplied — that the **title contains an expected
substring**; it refuses on mismatch so a stale/reused HWND cannot steal focus or
submit into the wrong window. The title check is **optional** (pass it to make
it enforced), and exe/class are **not** currently validated — supplying the
title argument is therefore recommended, and exe/class guards are a known future
hardening.

Proof-of-delivery is **not automatic — do not trust the `SENT-AND-SUBMITTED`
line alone.** Confirm delivery out of band: bind the submitted input against the
peer's returned ACK packet, and/or **manually screen-capture** the peer window
to confirm the packet landed as a completed message (composer empty), not
sitting in the composer. `mesh_send.py` does **not** capture.

Logging is **best-effort only**: each submit is appended to a local
`mesh_send.log`, but a log write error is deliberately swallowed, so the log is
a convenience trail — **not** a guaranteed durable record and not evidence of
delivery.

## Packet Format

Use this shape for agent-to-agent messages:

```text
[SENDER -> RECEIVER birth_id=<target-birth-id>] <short purpose>
repo=<repo> branch=<branch> commit=<sha>
state=<clean|dirty|blocked>
task=<current task>
ask=<specific next action or question>
```

For normal ACKs:

```text
[CLAUDE-1 -> CODEX-1] ACK token discipline. Waiting. blocker=none
```

## What Not To Do

Do not do this:

```text
[CLAUDE-1 -> CODEX-1]
Here is a long analysis in my own pane...
```

That is local narration, not mesh communication.

Do this instead:

1. Send the compact packet into the peer's registered HWND.
2. Locally print only `SENT`.
3. Wait for a return packet or assignment.

## Agent Health And Replacement Rubric

Use this rubric before spending more tokens on a confused agent. The goal is to
separate ordinary delay from a terminal that should be replaced.

| State | Measuring stick | Action |
| --- | --- | --- |
| Healthy | Replies by SelfConnect transport, local output is `SENT`/`ACK`/one-line blocker, registry heartbeat current. | Continue. |
| Degraded | One missed ACK, one hook warning, one packet split, or one slow tool call under 90 seconds. | Send one compact reset/probe. Do not narrate. |
| Protocol fault by sender | Receiver got only the first line of a multi-line Claude Code packet. | Resend as one physical line or artifact path. Do not blame the receiver on the first occurrence. |
| Stuck | A simple transport command is still waiting after 90 seconds, or the terminal is waiting on an approval/queued prompt. | Send one interrupt (`Ctrl-C`) if safe, then one single-line reset/probe. |
| Off-rails | After the reset/probe, the agent still narrates locally instead of sending through SelfConnect, repeats hook errors that block progress, sends to the wrong window, or misses two ACK probes in a row. | Stop using that terminal for active work. Mark it blocked/off-rails and spawn a replacement role with a new `birth_id`. |
| Unsafe | Target guard fails, wrong HWND/PID/class/title, stale generation, or wrong owner SID. | Do not send. Fix registry/lease/target first. |

Replacement threshold:

1. Read only the last 2,000-3,000 characters of the suspect terminal.
2. Send one single-line ACK probe through guarded `sc_cli send`.
3. If it is visibly stuck, send one `Ctrl-C` only.
4. Send one single-line reset probe.
5. If no valid ACK comes back, mark the role `blocked` or `off_rails`.
6. Spawn a replacement with a unique role name (`claude-2`, `codex-terminal-1`, `gemini-1`) and register the new HWND/PID/title/class/birth ID before assigning work.

Do not keep sending increasingly long instructions to a stuck terminal. That
turns a transport fault into a token burn.

## Sharpness Tracking

Long sessions drift. Compaction preserves broad state, but details and operating
discipline degrade. Track sharpness as an operational signal, not as a judgment
about the model.

Measured directly:

- session age from `created_at`;
- heartbeat age from `last_seen`;
- status (`active`, `degraded`, `compacting`, `off_rails`, `standby`);
- missed ACK count when agents fail transport probes;
- compaction count when an agent reports or performs compaction.

Estimated manually:

- token burn, because agent terminals do not expose a reliable cross-vendor
  token counter. If visible in the UI, record it as `tokens`; otherwise leave it
  unknown rather than inventing a number.

Use:

```powershell
python -m sc_mesh_registry update --role codex-1 --tokens 125000 --compact-count 1 --missed-acks 0
python -m sc_mesh_registry health
python -m sc_mesh_registry watch
```

Sharpness bands:

| Band | Measuring stick | Action |
| --- | --- | --- |
| Green | Fresh heartbeat, low age, no missed ACKs, no compaction pressure. | Continue. |
| Yellow | Session older than 2 hours, one compaction, one missed ACK, stale heartbeat, or tokens around 120k+. | Checkpoint, send compact status, consider replacement after current task. |
| Red | Session older than 4 hours, tokens around 180k+, two missed ACKs, repeated compactions, or off-rails/stuck status. | Compact handoff or replace before assigning complex work. |

Rule of thumb: do not assign patent, security, release, or cross-agent
coordination work to a red agent unless there is no alternative. Use it as
read-only context and hand the work to a fresh role.

## Compact Handoff

Agents should write a compact handoff before compaction, replacement, or passing
work to another role:

```powershell
python -m sc_mesh_registry handoff --role codex-1 --summary "what changed" --next "what the next agent should do" --tests "validation already run"
```

The command writes a markdown artifact under the local SelfConnect handoff
directory, captures registry/health/repo state, updates `last_handoff_path`, and
increments `compact_count`. For operator status, use:

```powershell
python -m sc_mesh_registry watch
```

## Shared State Sources

| State | Source |
| --- | --- |
| Active agent windows | `python -m sc_mesh_registry list` |
| Current ecosystem boundary | `docs/ecosystem-scope-and-workspaces.md` |
| Competitive/patent watch | `docs/competitive-patent-watch.md` |
| Current coordination rules | This file |

## Standing Product Rule

Normal SelfConnect must stay fast and useful for daily AI-to-AI work. Enterprise and government controls are profile-gated. Correctness infrastructure stays on in every profile: target guard, `birth_id`, echo-filtered readback, mesh registry, and compact handoff.
