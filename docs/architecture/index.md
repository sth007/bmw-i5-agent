# Architecture

The project is organized into small modules:

- `app/config.py` manages environment-backed settings.
- `app/models.py` defines the core data models.
- `app/agent.py` coordinates loading and ranking offers.
- `app/evaluator.py` contains offer scoring logic.
- `app/utils.py` provides reusable helpers.
