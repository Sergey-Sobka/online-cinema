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
git switch -c develop
git push -u origin develop
```

If the local repository is not initialized:

```bash
git init
git add .
git commit -m "Initial Online Cinema project setup"
git branch -M main
git remote add origin git@github.com:<owner>/<repo>.git
git push -u origin main
git switch -c develop
git push -u origin develop
```

## Repository Settings

- Protect the `develop` branch.
- Protect the `main` branch.
- Require pull requests before merging.
- Require at least 2 approvals.
- Require the `CI` workflow to pass before merge.
- Require branches to be up to date before merge.
- Disable force pushes to `main`.
- Disable force pushes to `develop`.
- Disable direct pushes to `main` for regular contributors.
- Disable direct pushes to `develop` for regular contributors.

## Team Rules

- One Trello card = one branch = one pull request.
- Use clear branch names from the Trello cards.
- Open feature pull requests into `develop`.
- Rebase your branch if `develop` changed before merge.
- Merge `develop` into `main` only after the integrated version is stable.
- Add or update tests for every custom feature.
- Update Swagger/OpenAPI docs for every custom endpoint.
