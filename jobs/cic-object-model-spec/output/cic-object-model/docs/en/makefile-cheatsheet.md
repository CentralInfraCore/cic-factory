# Makefile Cheatsheet

This file provides a comprehensive list of all available `make` commands and their functions.

## Container Lifecycle

- `make up`: Starts the `builder` development container in the background. The container will remain running until explicitly stopped.
- `make down`: Stops and removes all containers, networks, and volumes associated with the project.
- `make shell`: Opens an interactive `bash` shell inside the running `builder` container. This is the primary way to interact with the development environment.
- `make build`: Builds or rebuilds the Docker images for the `setup` and `builder` services.

## Main Development Tasks

- `make validate`: Runs the schema compiler in a validation-only mode. It checks the source schemas in `/schemas` against the rules defined in the meta-schema.
- `make test`: Executes the `pytest` test suite for the Python-based tooling. This includes running unit tests for the compiler.
- `make fmt`: Automatically formats all Python code using `black` and `isort` to ensure consistent code style.
- `make lint`: Lints the Python code with `ruff` and all YAML files with `yamllint` to catch potential errors and style issues.
- `make typecheck`: Runs static type analysis on the Python codebase using `mypy`.
- `make check`: A convenience target that runs `fmt`, `lint`, and `typecheck` in sequence.

## Release Management

- `make release-dependency VERSION=<version>`: This is the primary command for creating a signed, versioned artifact. It takes a `VERSION` argument (e.g., `v1.2.3`) and generates a signed schema file in the `/dependencies` directory. The process includes validation, checksumming, signing via Vault, and creating a new Git branch and tag for the release.
- `make release-schema VERSION=<version>`: Similar to `release-dependency`, but intended for creating final, application-specific schemas. It places the signed artifact in the `/release` directory.

## Repository Setup

- `make repo.init`: Sets up the Git hooks for this repository. Currently, this installs the `commit-msg` hook, which automatically signs commits using a local Vault agent. This should be run once after cloning the repository.

## Infrastructure & Maintenance

- `make infra.deps`: (Re)generates the `requirements.txt` file from `requirements.in` and installs all Python dependencies into the local `./p_venv` cache. Run this command after adding or removing a dependency in `requirements.in`.
- `make infra.coverage`: Generates an HTML test coverage report in the `./htmlcov` directory. This provides a detailed view of which parts of the code are covered by tests.
- `make infra.clean`: A cleanup command that stops all containers, removes all generated files (like `./p_venv`, `requirements.txt`), and deletes all caches and Docker volumes. This is useful for starting from a completely clean state.
