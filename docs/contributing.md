# Contributing

## Branching Strategy

- **main** - Protected branch for releases only. Direct pushes are blocked.
- **dev** - Active development branch.

### Workflow

1. Create a feature branch from `dev`:
   ```bash
   git checkout dev
   git pull
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit.

3. Push your branch and open a Pull Request to `dev`.

4. After review, merge to `dev`.

5. For releases, create a PR from `dev` to `main`.
