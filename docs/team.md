# Team & Collaboration

## Who's Building This

| Person | Background | Role |
|--------|-----------|------|
| **Brandon** | AWS developer, software engineer, experienced with AI coding agents (kiro-cli, Claude Code) | Architecture, AI agent workflow, mentoring on dev process |
| **Friend** | Azure sales data engineer, developer-savvy | Azure expertise, data pipeline design, learning to build from idea to product |

## The Goal

This is a **collaborative learning project** with two purposes:
1. **Build PSR** — take the idea from plan to working product on Azure
2. **Show the process** — Brandon demonstrates how to use AI coding agents to go from idea to code, while learning Azure alongside his friend who knows the platform

---

## Development Tooling — Different Tools, Same Repo

Each developer uses the AI tools they have access to. The code is the common ground.

**Brandon's Stack:**
- **kiro-cli** — primary AI coding agent (terminal-first, autonomous, reads codebase and drives edits)
- **`az` CLI + `azd`** — learning Azure alongside the project
- Workflow: terminal-driven, agent does the heavy lifting

**Friend's Stack (Microsoft Employee — Full Access):**
- **GitHub Copilot** (VS Code) — inline completions, chat, code generation. Backed by GPT-4o. Free with Microsoft employment
- **GitHub Copilot CLI** (`gh copilot`) — terminal command suggestions and explanations
- **GitHub Copilot Coding Agent** — can be assigned GitHub issues and works autonomously in PRs (runs in cloud, not local). Closest Microsoft equivalent to Claude Code
- **`az` CLI + `azd` + `func`** — already knows these
- Workflow: VS Code-driven, Copilot assists inline

**The Gap (and How We Bridge It):**
Microsoft doesn't have a true kiro-cli equivalent — a local, terminal-first, autonomous coding agent that reads your whole codebase, makes multi-file edits, runs commands, and iterates in a loop. Copilot is excellent at *assisting* but not at *driving*.

How we work around this:
1. Both devs work on the same GitHub repo — tool choice is personal, code is shared
2. Brandon screen-shares / works in Discord so friend can see the CLI agent workflow in action
3. Friend uses Copilot Coding Agent for autonomous PR work (assign it a GitHub issue, it opens a PR)
4. For pair sessions: Brandon drives with kiro-cli while friend watches and learns the agent-first approach
5. GPT-4o (which powers Copilot) is a strong model — the gap is in the *agent harness*, not the model quality

---

## Core Azure CLI Tools (Both Developers)

- **`az` (Azure CLI)** — Azure resource management. Install: `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash`
- **`azd` (Azure Developer CLI)** — scaffold, provision, deploy. Install: `curl -fsSL https://aka.ms/install-azd.sh | bash`
- **`func` (Azure Functions Core Tools)** — local Functions dev/test. Install: `npm i -g azure-functions-core-tools@4`
- **`bicep`** — Azure IaC (bundled with `az`)

---

## Setup Checklist

Brandon:
- [ ] Install `az` CLI and run `az login`
- [ ] Install `azd` CLI
- [ ] Install `func` (Azure Functions Core Tools)
- [ ] kiro-cli (already set up and running)

Friend:
- [ ] `az` CLI + `azd` + `func` (likely already has these)
- [ ] VS Code + GitHub Copilot (has via Microsoft)
- [ ] `gh` CLI + Copilot CLI extension: `gh extension install github/gh-copilot`
- [ ] Enable Copilot Coding Agent on the shared repo (Settings → Copilot → Coding agent)

Shared:
- [ ] Create shared Azure resource group
- [ ] Set up GitHub repo with branch protection
- [ ] Add both devs as collaborators
