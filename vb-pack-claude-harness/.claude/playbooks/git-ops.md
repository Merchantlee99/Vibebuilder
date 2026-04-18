# Git Operations Playbook

## Inspection first

Before any destructive or ambiguous operation:

```bash
git status
git log --oneline -20
git diff
git diff --cached
git worktree list
```

These are cheap. Use them freely.

## Harness gates that touch git

- `bootstrap.py --promote enforced` — pre-flight requires clean worktree.
- `bootstrap.py --adopt-project` — may `git init` + seed empty commit.
- Gate ⑥ scope — uses `git diff` internally to size-check edits.
- `activity_replay.py` — reconstructs events from `git log` during hook-disabled windows.

## Commits

- One logical change per commit.
- Never amend a pushed commit unless user explicitly asks.
- Never skip hooks (`--no-verify`) unless user explicitly asks.
- Never force-push to main/master.

## Branches

- Feature branches preferred over direct main commits once past `bootstrap` mode.
- Worker subagents default to `isolation: worktree` — gives a disposable worktree for the task.

## Destructive operations — always confirm first

- `git reset --hard`
- `git clean -fd`
- `git branch -D`
- `git checkout -- <file>` (discards uncommitted changes)
- `git push --force`
- `git rebase -i` (not allowed — interactive, can't be automated safely)

## Undoing

- Uncommitted changes: `git stash` (recoverable) over `git checkout --` (destructive)
- Published commit: `git revert` (new commit undoing it) over `git reset` (rewrites)
- Wrong branch: `git branch new-name && git reset --hard @{-1}` sequence (ask first)

## Commit message style

Conventional commit prefix:
- `feat:` new feature
- `fix:` bug fix
- `refactor:` no behavior change
- `test:` tests only
- `docs:` docs only
- `chore:` tooling, deps, infra
- `perf:` perf improvement
- `ci:` CI config

## Worktrees (for worker subagents)

```bash
git worktree list                                    # current worktrees
git worktree add ../wt-auth -b worker/auth main      # new worktree
git worktree remove ../wt-auth                       # clean up
```

- Claude Agent tool `isolation: "worktree"` creates these automatically.
- Empty worktrees (no changes) are auto-removed on agent return.
