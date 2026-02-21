# CSS Refactor Freeze and Migration Plan

## Temporary Freeze Rule
- Freeze window starts now and applies during refactor.
- Allowed changes: regression fixes only.
- Disallowed changes: visual redesign, component restyling, or new visual patterns.

## Target CSS Structure
- `app/main/static/css/reset.css`
- `app/main/static/css/typography.css`
- `app/main/static/css/containers.css`
- `app/main/static/css/header.css`
- `app/main/static/css/nav.css`
- `app/main/static/css/buttons.css`
- `app/main/static/css/forms.css`
- `app/main/static/css/tables.css`
- `app/main/static/css/cards.css`
- `app/main/static/css/status.css`
- `app/main/static/css/home.css`
- `app/main/static/css/project.css`
- `app/main/static/css/pipeline.css`
- `app/main/static/css/run-detail.css`
- `app/main/static/css/custom.css` (orchestrator + temporary compatibility only)

## Layering Rules
Import order in `custom.css` must stay:
1. reset
2. base
3. layout
4. components
5. pages
6. utilities/compatibility

## Naming Convention
- Use feature-scoped class prefixes, not generic globals.
- Reusable primitives use component names (`.status-pill`, `.app-nav-btn`).
- Page-only selectors stay in page files (`home.css`, `project.css`, `pipeline.css`, `run-detail.css`).
- New IDs are discouraged; prefer classes.

## Migration Passes
1. Pass 1: header/nav
2. Pass 2: buttons
3. Pass 3: cards/meta tiles
4. Pass 4: tables (projects/pipelines/runs/upload queue)
5. Pass 5: status chips/pills
6. Pass 6: page-specific home/project/pipeline/run

## Per-Pass Checklist
- Run app locally.
- Compare baseline screenshots.
- Fix regressions immediately.
- Record selector moves/deletions in PR notes.

## Baseline Screenshot Inventory
Store baseline and after images under `docs/img/ui-baseline/`.
Required pages:
- home
- project list
- project detail (pipelines table visible)
- pipeline detail (upload + runs list)
- run detail

Suggested filenames:
- `home.before.png`
- `project-list.before.png`
- `project-detail.before.png`
- `pipeline-detail.before.png`
- `run-detail.before.png`

## PR Template Requirements
Every refactor PR should include:
- moved selectors list
- deleted selectors list
- before/after screenshots for changed surfaces
- regression notes (if any)

## Definition of Done
- `custom.css` is orchestration + minimal compatibility only.
- No duplicated component styles across CSS modules.
- No regressions on key pages in screenshot checklist.
- Team can locate style ownership quickly by file scope.
