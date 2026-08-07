# Git Branch Management Specification

## 1. Branch Creation and Naming

The following rules apply to the creation and management of branches:

### Base Branches
- **`main`** (or **`m`**) contains the stable, production-ready code.
- **`devel`** (or **`d`**) contains ongoing development work and serves as the parent for both feature and hotfix branches.

### Release Branches
- **`release-<VERSION>`** (or **`r-<VERSION>`**) branches are used to prepare a specific version, stabilize the code, and ensure the creation of new versions. The naming convention is **`release-<VERSION>`**, for example, `release-1.0.0`, `release-1.1.0`.
- Release branches can be branched off from either the **`main`** or **`devel`** branches and represent stable, production-ready versions of the code.

## 2. Feature and Hotfix Branch Management

### Feature Branches
- Feature branches can be created from **`main`** (or **`m`**), **`devel`** (or **`d`**), or **`release-<VERSION>`** (or **`r-<VERSION>`**) branches.
- The naming convention for feature branches is **`<base-branch-sort name>/feature-<FEATURE-ID>`**, for example:
  - `m/feature-10`
  - `d/feature-10`
  - `r-1.0.0/feature-10`
  - `d/f-10/devel`
  
### Hotfix Branches
- Hotfix branches can be created from **`main`** (or **`m`**), **`devel`** (or **`d`**), or **`release-<VERSION>`** (or **`r-<VERSION>`**) branches.
- The naming convention for hotfix branches is **`<base-branch-sort name>/hotfix-<HOTFIX-ID>`**, for example:
  - `m/hotfix-10`
  - `d/hotfix-10`
  - `r-1.0.0/hotfix-10`

## 3. Merging and Branch Deletion

### Merge Rules
- After merging a **`feature`** or **`hotfix`** branch into the target branch (e.g., **`release-<VERSION>`**, **`main`**, **`devel`**), the merged branches are **not deleted**, but the following child branches **are deleted**:
  - **`<base-branch-sort name>/feature-<FEATURE-ID>/d`**, **`<base-branch-sort name>/hotfix-<HOTFIX-ID>/d`**, **`<base-branch-sort name>/release-<VERSION>/feature-<FEATURE-ID>/*`** branches that are associated with the feature or hotfix development using "sort commits".
- The goal is to keep the primary **`feature`** or **`hotfix`** branches intact and delete only unnecessary child branches.

### Deletion Command:
```bash
git push origin --delete <branch-name>  # Delete from the remote repository
```

## 4. CI and Developer Feedback

- CI processes run on the developer's machine for **`feature`**, **`hotfix`**, and **`release-<VERSION>`** branches, ensuring continuous integration and providing quick feedback. Developers are notified whether their changes are on the right track or not.
- The CI process runs after each commit to ensure that the changes do not break the code or introduce errors.

## 5. Feature/Hotfix Merge and Child Branch Deletion

### Merge and Deletion:
- After merging a **`feature`** or **`hotfix`** branch into the target branch (e.g., **`release-<VERSION>`**, **`main`**, **`devel`**), the child branches underneath are deleted:
    - For example, **`feature-<ID>/d`**, **`hotfix-<ID>/d`**, **`release-<VERSION>/feature-<ID>/*`** branches that have sort commits should be deleted after the merge.

### Deletion Process:
1. After the merge is successfully completed, the following branches will be deleted:
   ```bash
   git checkout release-1.0.0
   git merge release-1.0.0/feature-10
   git push origin --delete release-1.0.0/feature-10/d  # Delete child branches
   ```
