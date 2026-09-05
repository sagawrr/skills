---
name: k16-preview
description: Manages dev-server previews on the k16-server headless box — runs Vite (or any app) on a port, delivers LAN, off-LAN ssh, or ephemeral public URLs, and shares or stops public links via k16-share/k16-share-stop. Use when the user wants to preview, view, expose, share, or tunnel an app running on k16, get a shareable URL, or stop sharing.
license: MIT
compatibility: claude-code, opencode
metadata:
  box: k16-server (headless Ubuntu; herdr for panes; scripts at ~/.local/bin)
---

# k16-preview

Pick the delivery path first — they answer different needs:

| User need | Path | URL the user gets |
|---|---|---|
| Look at it themselves, at home | LAN URL | `http://k16-server.local:<port>` |
| Send a link to someone else / another device | `k16-share` | `https://<random>.trycloudflare.com` |
| Look at it themselves, away from home | ssh tunnel for their Mac | `http://localhost:<port>` on their Mac |

Never start a public share unless one was requested. Public URLs die with
their process by design — nothing stays exposed behind the user's back.

## Prerequisites

`k16-share` and `k16-share-stop` (in `scripts/` in the skill's source repo)
must be installed at `~/.local/bin/` on the k16-server and made executable.
Non-interactive shells lack the login PATH — prefix commands with:

```bash
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"
```

## 1. Check what is already running — never start a duplicate

```bash
ss -tlnp | grep :<port>
```

If something listens, reuse it: find the owning pane with `herdr pane list`
(check each pane's `foreground_cwd`). Only start a server if nothing listens.
If an unexpected process holds the port, report the owner — never kill blind.
(`--strictPort` on Vite exists so a wrong second server fails loudly instead
of silently serving different code on the same URL.)

## 2. Run the dev server (only if needed)

Servers live in a **shell** pane, never an agent's pane: `herdr pane run`
types into whatever owns the pane's foreground, and an agent receives typed
text as chat input.

```bash
herdr pane run <shell-pane-id> npm run dev -- --host 0.0.0.0 --strictPort
```

Verify both before claiming anything:

```bash
ss -tln | grep :<port>
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:<port>/
```

Expect `200`. Fix the origin first if not — every delivery path depends on it.

## 3. Deliver

**LAN:** report `http://k16-server.local:<port>` (mDNS + UFW + Vite
allowedHosts are already configured). Verify the port listens; done.

**Public link (share):**

```bash
$HOME/.local/bin/k16-share <port>
```

One call starts the tunnel, waits for the URL, and verifies it. It prints:

- `URL: https://<random>.trycloudflare.com` — give this to the user only after
  `status:` shows `verified HTTP 200`
- `status: already sharing ...` — a share was already running; reuse it, do
  not start another
- hints for 403 (app rejects Host header — check Vite allowedHosts) and 502
  (origin stopped listening)

The URL is random per tunnel and dies when the tunnel stops. Re-sharing after
a stop yields a NEW URL — always run the script again and re-read its output.

**Off-LAN personal use (give instructions, run nothing):** the user's Mac has
the `k16-tailcat` SSH alias:

```bash
ssh -f -N -L <port>:localhost:<port> k16-tailcat   # then browse localhost:<port>
```

## 4. Stop sharing (when the user is done)

```bash
$HOME/.local/bin/k16-share-stop
```

Stops the managed tunnel and sweeps strays, then verifies nothing public
remains. Dev servers keep running unless the user asks to stop them.

## Report state honestly

Say what is still running and where: dev server port + owning pane, share
URL + that it dies with its process. A dev server inside a linked worktree
serves that worktree's code, NOT main — check `foreground_cwd` before
claiming which code a URL serves.

## Facts

- `w1` = main Inaam checkout (`/srv/projects/inaam`); other workspaces hold
  linked worktrees.
- Only 5173/tcp is UFW-open (LAN only). Shares need no firewall changes —
  the tunnel is outbound-only.
- HMR/websockets work through shares; SSE does not (quick-tunnel limitation).
