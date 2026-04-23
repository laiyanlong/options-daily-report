# .claude/ — workspace for Claude Code (public repo)

Keeps sessions productive in this **data-only** repository.

## Layout

```
.claude/
├── README.md            ← you are here
├── memory/              ← facts Claude Code should know
│   ├── scope.md         ← what this repo contains + what it doesn't
│   ├── data-contract.md ← stable schema the app depends on
│   └── contributing.md  ← how OSS contributors can help
└── workflows/           ← common tasks
    ├── fix-readme-typo.md
    ├── improve-dashboard-viewer.md
    └── report-data-issue.md
```

## Key reminder for every session

This repo is **data-only**. Python source code does NOT live here.
If a task asks you to modify generation logic, redirect the user to the
private `options-core` repo.
