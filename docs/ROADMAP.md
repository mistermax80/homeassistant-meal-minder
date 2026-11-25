# Meal Minder development roadmap

Last reviewed: 2026-11-25

Current release: `1.0.0-alpha.7`

This roadmap is a working proposal based on the code at alpha.7. Priorities
focus first on reliable existing behavior; larger product features remain
candidates until their scope is agreed.

## Project status

Meal Minder is a Home Assistant custom integration with persistent meal plans,
recurring and date-specific meals, a calendar, four sensors, service actions,
WebSocket commands, import/export, and diagnostics. The repository has focused
`unittest` coverage for storage, the calendar, and sensor scheduling.

The current release is still alpha. The options flow exposes meal management,
but creating and editing meals through that UI currently ends in
`not_implemented` (`custom_components/meal_minder/config_flow.py`). The README
also has stale feature claims and references a dashboard screenshot that is not
tracked in the repository. Italian selector/service translations exist; other
languages are not present.

### Known correctness gaps to address first

- **Meal removal searches only the first plan.** The loop in
  `storage.py:225-237` returns even when the meal was not found there, so meals
  in later plans cannot be removed through this method.
- **WebSocket plan lookup and default instance selection use the wrong data
  level.** `websocket_api.py:87-96,318-327` treats the top-level integration
  data as an entry map, but storage is held under `hass.data[DOMAIN]["instances"]`.
- **WebSocket writes do not notify entities.** Unlike service writes, the
  add/update/delete handlers in `websocket_api.py` do not fire
  `meal_minder_updated`; calendar and sensor state can therefore remain stale.
- **Diagnostics uses the same outdated storage layout.**
  `diagnostics.py:17` indexes the entry directly under `hass.data[DOMAIN]`
  instead of under `"instances"`.
- **Import validation and failure safety need strengthening.** The import
  paths accept only a shallow shape check before replacing stored data. Define
  and test the accepted schema, and ensure invalid input or a failed save
  cannot leave the live instance in a partially changed state.

## Proposed milestones

### 1. Alpha reliability — next

- Fix the storage lookup, diagnostics lookup, and multi-plan meal-removal bugs.
- Make every successful WebSocket mutation notify entities, and return clear
  errors for invalid or missing config entries.
- Validate backup data before replacing storage; preserve the current data if
  validation or persistence fails.
- Add regression tests for each fix, including multiple configured instances.
- Add a repeatable Home Assistant test environment and CI checks for tests,
  lint, and supported Home Assistant versions.

**Exit criteria:** the known correctness gaps above have regression coverage;
the complete test and lint checks pass in CI; backup import/export preserves
existing data on rejected input.

### 2. Beta usability

- Complete the config-flow meal create, edit, and delete screens, or remove
  unavailable actions until they are implemented.
- Make the README and service/API documentation match behavior that has
  actually been tested; add or remove the missing dashboard screenshot
  reference.
- Document installation, setup, entity attributes, scheduling rules, backup
  recovery, and supported Home Assistant versions.
- Verify Italian translations and add another language only when translation
  maintenance can be supported.
- Evaluate Lovelace UI, shopping-list integration, and Companion App
  notifications as separate, scoped proposals rather than assuming they are
  part of the core release.

**Exit criteria:** users can manage the advertised meal workflows without
unfinished UI actions, and the documentation matches the released behavior.

### 3. Stable release

- Define and document the storage/export compatibility policy and migration
  behavior before changing persisted formats.
- Keep compatibility tests for upgrade, backup, restore, time zones, and
  daylight-saving transitions.
- Publish release notes, supported-version policy, troubleshooting guidance,
  and a clear process for reporting defects.
- Resolve all high-priority defects and meet the beta exit criteria before
  removing the alpha status.

**Stable-release gate:** supported Home Assistant versions are tested in CI;
critical user data flows have regression tests; no known data-loss or
integration-blocking defects remain.

## Later feature candidates

Recipe support, pantry tracking, nutrition information, AI meal suggestions,
and multi-user behavior are possible future directions, not commitments for
the next release. Revisit them after the reliability and beta milestones using
user feedback and explicit scope decisions.

## Development and validation notes

- Tests use the standard-library `unittest` runner: `python -m unittest discover
  -v`.
- This checkout does not declare or include the Home Assistant test dependency
  or Ruff executable. At review time, tests could not import because
  `homeassistant` is unavailable, and lint could not run because `ruff` is
  unavailable. Run both in the project’s configured Home Assistant development
  environment before merging functional changes.
- There is no checked-in GitHub Actions workflow at this revision.
