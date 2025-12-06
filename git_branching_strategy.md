## Smart Spend - Git Branching & Commit Strategy

---

# 1️⃣ Branching Strategy

We’ll use a **simplified Git Flow** with `main`, `dev`, and feature branches:

| Branch Name   | Purpose | Workflow |
|---------------|---------|----------|
| **main**      | Production-ready code | Only merges from `dev` after CI passes and QA approval |
| **dev**       | Integration & development | All feature branches merge here first. CI runs automatically. |
| **feature/<name>** | New feature development | Branch off `dev`. Merge back to `dev` via Pull Request when done. |
| **hotfix/<name>** | Critical bug fix in production | Branch off `main`. Merge to both `main` and `dev` after fix. |

**Example:**
```bash
git checkout dev
git checkout -b feature/upload-endpoint
```

---

# 2️⃣ Commit Message Conventions

Use **imperative style** and prefix commits to indicate type:

| Type      | Prefix     | Example Commit Message |
|-----------|------------|----------------------|
| Feature   | `feature:` | `feature: add CSV upload endpoint with background processing` |
| Fix       | `fix:`     | `fix: resolve CSV parsing error for empty rows` |
| Chore     | `chore:`   | `chore: update requirements and GitHub Actions workflow` |
| Docs      | `docs:`    | `docs: update README with setup instructions` |
| Test      | `test:`    | `test: add unit tests for transaction categorization` |
| Refactor  | `refactor:`| `refactor: optimize CSV processing function` |

> Keep messages **clear, concise, and descriptive**.

---

# 3️⃣ Pull Request (PR) Guidelines

- PRs should always target `dev` branch.
- Include a descriptive title, e.g., `feature: add user authentication`.
- Link relevant issues (if any) in PR description.
- CI must pass before merging.
- Ensure **no secrets are committed**.
- Add reviewers for code review before merging to `dev`.

---

# 4️⃣ Merging Strategy

- **Dev → Main**:  Only merge when `dev` is stable, CI passed, and QA approved.
```bash
git checkout main
git merge dev
git push origin main
```
- **Feature → Dev**: After completing a feature, open a PR to `dev`.
```bash
git checkout dev
git merge feature/<name>
git push origin dev
```
- **Hotfix → Main + Dev**:
```bash
git checkout main
git merge hotfix/<name>
git push origin main

git checkout dev
git merge hotfix/<name>
git push origin dev
```

---

# 5️⃣ Example Workflow

1. Create a feature branch from `dev`:
```bash
git checkout dev
git checkout -b feature/user-auth
```
2. Implement feature and commit in small steps:
```bash
git add smart-spend-backend/app/routers/auth.py
git commit -m "feature: add JWT authentication for login and registration"
```
3. Push to GitHub:
```bash
git push origin feature/user-auth
```
4. Open a PR to merge `feature/user-auth` → `dev`.
5. CI runs tests and linter. Code review is performed.
6. After approval, merge PR to `dev`.
7. Repeat until `dev` is stable, then merge `dev` → `main`.

---

# 6️⃣ Tagging Releases (Optional)

Once `main` is stable, tag releases for production:
```bash
git checkout main
git tag -a v1.0.0 -m "Initial production release"
git push origin v1.0.0
```
> Use semantic versioning: `MAJOR.MINOR.PATCH`.

---

✅ **Outcome**

- Clean commit history.
- Safe handling of secrets.
- CI ensures code quality.
- Stable production releases.
- Clear path for features, fixes, and hotfixes.

---
---
