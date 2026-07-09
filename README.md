# Nox List

A Pointercrate-style ranked level list web app, built to explore REST API design, relational data modeling, and full-stack integration from scratch.

## Overview

Nox List is a Pointercrate-adjacent Demon List documenting the hardest Geometry Dash demon levels completed by members of the Nox discord server. Created as a passion project to practice Full-Stack web development.

## Tech Stack

**Backend**
- Python
- FastAPI
- SQLModel (SQLite)
- Pydantic

**Frontend**
- HTML / CSS / JavaScript
- Fetch API for GET/POST/DELETE requests

## Features

- Ranked level list with stable `level_id`s and mutable `list_position` values
- Create, reorder, update, and delete levels with automatic position-shifting for affected entries
- REST endpoints designed around stable resource identifiers in the URL, with position changes handled in the request body

## Status

🚧 **In active development.** Core backend logic (CRUD routes, position-shift helpers) and initial frontend integration are in progress. Not yet deployed.

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the dev server
uvicorn backend.routes:app --reload
```

## Roadmap

- [ ] Finalize and test position-shift logic for insert/delete/reorder (unit tests with pytest)
- [ ] Flesh out frontend integration with live API data
- [ ] Deploy backend + frontend
- [ ] Add authentication (register/login) flow

## Author

Tato223 | Dante