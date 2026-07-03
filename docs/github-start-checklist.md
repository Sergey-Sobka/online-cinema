# GitHub Start Checklist

Use this checklist after creating the GitHub repository.

## Initial Push

If the repository is already initialized locally:

```bash
git add .
git commit -m "Initial Online Cinema project setup"
git branch -M main
git remote add origin git@github.com:<owner>/<repo>.git
git push -u origin main
```

If the local repository is not initialized:

```bash
git init
git add .
git commit -m "Initial Online Cinema project setup"
git branch -M main
git remote add origin git@github.com:<owner>/<repo>.git
git push -u origin main
```

## Repository Settings

- Protect the `main` branch.
- Require pull requests before merging.
- Require at least 2 approvals.
- Require the `CI` workflow to pass before merge.
- Require branches to be up to date before merge.
- Disable force pushes to `main`.
- Disable direct pushes to `main` for regular contributors.

## Team Rules

- One Trello card = one branch = one pull request.
- Use clear branch names from the Trello cards.
- Rebase your branch if `main` changed before merge.
- Add or update tests for every custom feature.
- Update Swagger/OpenAPI docs for every custom endpoint.

