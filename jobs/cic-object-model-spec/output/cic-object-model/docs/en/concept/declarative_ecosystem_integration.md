# Blueprint: The Declarative, Two-Speed Ecosystem

## 1. Philosophy and Principles

The CIC project is not a monolithic software but a dynamic ecosystem of independent yet tightly coupled components. During the development and integration of such a distributed system, traditional models (pure monorepo or pure multi-repo) run into limitations. Therefore, we apply a hybrid strategy based on the principles of modern Platform Engineering.

The central philosophy of our system is not to forcefully prevent errors, but to ensure **maximum transparency and lightning-fast, automated diagnostics**. The system is not "self-healing," but **"self-diagnosing"**. It does not take responsibility away from the development teams but provides them with clear, indisputable, real-time data to make the right decisions.

### Our Principles

*   **Declarative Ecosystem:** The relationship between components is not hidden in the code or in the developers' minds, but is **declared** in a central, version-controlled configuration file. This configuration is the living, breathing "map" of the system.
*   **Two-Speed Risk Management:** We operate a "fast" (commit-level) and a "slow" (release-level) integration process in parallel. With this dual approach, we ensure both maximum development speed and the rock-solid stability of the live system.
*   **Automated Feedback:** Every change in the system triggers an automated cascade that runs the necessary tests across the entire ecosystem. The results are displayed in a central location, a "dashboard," providing immediate and clear feedback on the impact of the change.

---

## 2. System Anatomy: Key Components

The machinery relies on five main building blocks:

*   **Parent Repo:** A central, "ancestor" repository that contains the development of a logical unit (e.g., a common base, a platform component). This repo is the source of changes.

*   **Child Repo:** A repository that depends on the Parent Repo. This repo is the "consumer" of changes.

*   **Ecosystem Map (`ecosystem.yaml`):** A version-controlled file located in the Parent Repo. Under the `children` field, it explicitly lists the identifiers of all dependent Child Repos. This is the system's DNS, the central source of truth for the dependency graph.

*   **Renovate Configuration (`renovate.json`):** A file in the Child Repos that describes the behavior of the Renovate bot, i.e., *how* it should handle updates from the parent (e.g., what name to use for the branch, what commit message to use).

*   **CI/CD Orchestrator:** The CI/CD pipeline of the Parent Repo, which plays the role of the "conductor." It reads the Map and initiates the cascade towards the Child Repos when a change occurs in the Parent.

---

## 3. How It Works: The Two Circulations

The system operates two parallel but distinct "circulations" for managing changes.

### 3.1. The Fast Circulation (Development Process)

*   **Goal:** Immediate feedback. To ensure that the latest, under-development changes in the Parent Repo do not break the components that depend on it. We want to catch errors the moment they are created, not days later.

*   **Process:**
    1.  **Trigger:** A developer pushes a commit to the `main` (or `dev`) branch of the `Parent Repo`.
    2.  **Orchestration:** The `Parent Repo`'s CI pipeline (the Orchestrator) starts. It reads the `ecosystem.yaml` and sends a `repository_dispatch` event to each repo listed in the `children` list. The event payload contains the new **commit hash** of the Parent Repo.
    3.  **Integration:** A dedicated CI pipeline in the `Child Repo`, created for this purpose, is triggered by the event. Based on the received commit hash, it creates a temporary branch named `r/parent-integration/<commit_hash>` and attempts to merge the parent's change.
    4.  **Testing:** The `Child Repo` runs its full test suite on this temporary integration branch.
    5.  **Feedback:** Depending on the test results, the `Child Repo`'s CI sends a status check (`success` or `failure`) back to the original commit in the `Parent Repo` via the GitHub API.

*   **Result:** In the `Parent Repo`'s commit history, it becomes clearly visible for each commit whether it can be successfully integrated across the entire ecosystem. Developers get immediate, targeted feedback on the impact of their changes.

### 3.2. The Slow Circulation (Stable Release Process)

*   **Goal:** To guarantee the stability of the live system. To ensure that only official, tested, stable releases of the Parent Repo can be merged into the `main` branch of the Child Repos, through a controlled and auditable process.

*   **Process:**
    1.  **Trigger:** A new semantic version tag `release/*` (e.g., `v1.2.0`) is created in the `Parent Repo`.
    2.  **Orchestration:** The `Parent Repo`'s CI pipeline (the Orchestrator) starts. It reads the `ecosystem.yaml` and sends an event to each repo in the `children` list, containing the new **release tag** name.
    3.  **Integration (by Renovate):** In the `Child Repo`, the Renovate bot (or a CI step) detects the event. According to the rules defined in `renovate.json`, it creates a branch named `m/feature/update-parent-to-v1.2.0`, updates the dependency to `v1.2.0`, and then opens a Pull Request towards the `Child Repo`'s `main` branch.
    4.  **Testing:** The Pull Request triggers the `Child Repo`'s full CI process, just as if a human developer had opened the PR.
    5.  **Feedback and Decision:** The CI status of the PR (green or red) indicates whether the new release can be successfully integrated. It is the responsibility of the `Child Repo`'s owners (CODEOWNERS) to review and approve the Pull Request, then merge it into the `main` branch.

*   **Result:** Dependency updates happen in the form of a controlled, tested, human-approvable Pull Request, guaranteeing the stability of the `main` branch and the auditability of changes.

---

## 4. The Result: A Self-Diagnosing Dashboard

This two-speed model creates a system that does not try to hide complexity, but brings it to the surface. The Pull Requests and commit history of the `Parent Repo` become a real-time **Control Plane** that shows the health status of the entire ecosystem.

With a single glance, one can assess which child components were "broken" by a particular change, and it becomes clear which team is responsible for fixing the error. This allows for informed, data-driven decision-making instead of teams pointing fingers at each other in the event of a complex failure.
