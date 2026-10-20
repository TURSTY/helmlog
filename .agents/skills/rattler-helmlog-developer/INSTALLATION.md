# Installing and using Rattler HelmLog Developer

## Source of truth
Store the entire `rattler-helmlog-developer/` directory in the HelmLog fork, preferably under `.agents/skills/rattler-helmlog-developer/` (confirm your installed Codex version’s discovery convention before relying on automatic loading). Version it alongside code. The GitHub repository is the canonical copy; this ZIP is a portable snapshot.

## Codex
Copy or symlink the skill directory into the Codex skills directory supported by your installed Codex version, or configure the workspace to discover the repository skill. Verify discovery by asking Codex to identify this skill and report the baseline SHA. Do not assume GitHub hosting alone installs it.

## ChatGPT
ChatGPT does not automatically ingest arbitrary GitHub skill directories into every chat. In a new ChatGPT project/conversation, attach `SKILL.md` and the relevant reference documents (or the ZIP if supported), and instruct ChatGPT to follow them. If a skill-installation feature is available in your client, use its documented import workflow and verify that the skill appears.

## Suggested first prompt
"Use the Rattler HelmLog Developer skill. First read SKILL.md and the relevant references. Confirm the current Git branch and commit, summarize applicable contracts and approval rules, and propose the smallest safe next step. Do not commit, push, merge or deploy without my approval."

## Maintenance
Update after meaningful milestones, not each session. Review changed contracts against code, record verification commit and date, update decisions/roadmap, and obtain approval before committing the skill update. Never include credentials.
