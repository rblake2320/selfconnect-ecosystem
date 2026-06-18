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

## Shared State Sources

| State | Source |
| --- | --- |
| Active agent windows | `python -m sc_mesh_registry list` |
| Current ecosystem boundary | `docs/ecosystem-scope-and-workspaces.md` |
| Competitive/patent watch | `docs/competitive-patent-watch.md` |
| Current coordination rules | This file |

## Standing Product Rule

Normal SelfConnect must stay fast and useful for daily AI-to-AI work. Enterprise and government controls are profile-gated. Correctness infrastructure stays on in every profile: target guard, `birth_id`, echo-filtered readback, mesh registry, and compact handoff.
