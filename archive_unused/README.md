# Archived generated files

This folder keeps generated development artifacts that are not required by the
application source code. They were moved here instead of deleted so they remain
recoverable.

- `python_cache/` contains Python bytecode caches from the project root and
  source folders.
- `pytest_cache/` contains pytest's local run cache.
- `temporary_output/` contains rendered previews, smoke-test uploads, and other
  intermediate build files formerly stored in `tmp/`.

The application can recreate these files when its tests and supporting scripts
run. Production uploads, reports, submission output, source documents, and the
virtual environment were intentionally left in their original locations.
