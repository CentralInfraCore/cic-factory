# Developer Workflow

This document outlines the typical workflows for interacting with the schema framework, from initial setup to creating a new release.

## First-Time Setup

Before you begin, ensure you have the following prerequisites installed on your host machine:
- `docker`
- `docker-compose`
- `make`
- `git`

Follow these steps to initialize the project after cloning the repository:

1.  **Start the Vault Signing Agent:**
    This project requires a running Vault instance for signing release artifacts. A helper script is provided to run a temporary, local Vault server for development.

    ```sh
    # This needs to be run from the project root in a separate terminal
    ./tools/vault-sign-agent.sh -k /path/to/your/key.pem -c /path/to/your/cert.crt --root-ca-file /path/to/your/CICRootCA.crt
    ```
    This agent will remain running in the background.

2.  **Install Python Dependencies:**
    This command compiles the `requirements.in` file and installs all necessary Python packages into a local `./p_venv` directory, which is used as a cache by the Docker container.

    ```sh
    make infra.deps
    ```

3.  **Build Docker Images:**
    Build the necessary Docker images for the `setup` and `builder` services.

    ```sh
    make build
    ```

4.  **Start the Development Container:**
    This starts the `builder` container in the background.

    ```sh
    make up
    ```

5.  **Initialize Git Hooks:**
    This script sets up the `commit-msg` Git hook, which automatically signs your commits using the running Vault agent.

    ```sh
    make repo.init
    ```

Your environment is now fully configured and ready for development.

## Day-to-Day Development

This is the typical cycle you will follow when modifying or creating schemas.

1.  **Modify a Schema:**
    Make your desired changes to a schema file located in the `/schemas` directory.

2.  **Run Validation:**
    Before creating a release, it's crucial to validate your changes. The `validate` command runs the compiler in a validation-only mode.

    ```sh
    make validate
    ```

3.  **Run Tests:**
    To ensure the tooling itself is working correctly, run the `pytest` suite.

    ```sh
    make test
    ```

4.  **Commit Your Changes:**
    When you are ready, commit your changes. The `commit-msg` hook will automatically run, connect to your local Vault agent, and append a signing block to your commit message.

    ```sh
    git add .
    git commit -m "feat: Update schema with new properties"
    ```

## Creating a Release

When a schema is ready to be versioned and distributed, you will create a "release artifact". This is a signed, immutable version of the schema.

1.  **Ensure Your Working Directory is Clean:**
    The release script will abort if you have uncommitted changes.

2.  **Run the Release Command:**
    Use the `make release-dependency` command to generate a signed schema and place it in the `/dependencies` directory. The `VERSION` variable must be a valid semantic version (e.g., `v1.2.3`).

    ```sh
    make release-dependency VERSION=v1.0.0
    ```

3.  **Review the Process:**
    The script will perform the following actions automatically:
    - Create a new release branch (e.g., `template-schema/releases/v1.0.0`).
    - Invoke the `compiler.py` script to generate the signed artifact.
    - Commit the new artifact to the release branch.
    - Create a GPG-signed Git tag for the release version.
    - Switch back to your original branch.

4.  **Push the Tag:**
    The release process concludes by creating a local Git tag. To share the release with others, you must push this tag to the remote repository.

    ```sh
    # Example tag name: template-schema@v1.0.0
    git push origin <tag_name>
    ```
