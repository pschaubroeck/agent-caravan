# Tests

The test suite verifies resolver behavior, catalog manifest integrity, overlay composition, runtime compatibility, and repeatable local profile bootstrapping.

- `unit/`: implementation behavior and local profile tests
- `integration/`: manifest and cross-resource boundary tests
- `fixtures/`: representative normalized bundles
- `package_tests/` (repository root): installed-wheel checks, run by `make package-smoke`

Run it from the repository root with:

```text
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
```

This source-checkout test run excludes the installed-wheel checks. Run those
separately with `make package-smoke`; the package smoke command builds and
installs a wheel before running `package_tests.test_package_distribution`.
