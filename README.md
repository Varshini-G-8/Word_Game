# Word Guess Game

A web-based word guessing game developed using Flask. The application supports
two types of users: players, who can register and play the game, and
administrators, who can view game activity reports.

---

## Overview

The Word Guess Game allows registered players to guess a randomly selected
five-letter word within a maximum of five attempts.

The application supports two user roles:

- **Player** – registers, logs in, and plays the word guessing game.
- **Administrator** – accesses the administration dashboard and views game
  activity reports.

The application uses Flask for the backend, Jinja2 templates for server-side
rendering, JavaScript for interactive gameplay, and SQLite for data storage.

---

## Features

### Authentication and User Management

- Player registration and login
- Password hashing
- Session-based authentication
- Role-based access control
- Logout functionality
- Username and password validation
- Prevention of duplicate usernames

### Word Guessing Game

- Five-letter word guessing
- Maximum of 5 guesses per word
- Maximum of 3 words per player per day
- Random word selection
- Guess submission and validation
- Previous guesses displayed on the game board
- Wordle-style color feedback
- Win and loss handling
- Option to continue with another word when eligible

### Guess Feedback

Each letter in a submitted guess receives a color based on its relationship
to the target word:

| Indicator | Meaning |
|-----------|---------|
| 🟩 Green | Correct letter in the correct position |
| 🟧 Orange | Correct letter in the wrong position |
| ⬜ Grey | Letter is not present in the target word |

The game checks exact letter matches first and then checks the remaining
letters to handle repeated letters correctly.

### Administrator Features

Administrators can:

- Access the administration dashboard
- View daily game activity
- View player activity
- View the number of words attempted
- View successful rounds
- View player-specific activity

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, Flask |
| Frontend | HTML5, CSS3, JavaScript |
| Templating | Jinja2 |
| Database | SQLite |
| ORM | Flask-SQLAlchemy |
| Authentication | Flask-Login |
| Password Security | Werkzeug |
| Version Control | Git |

---

## Project Structure

```text
wordle_game/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── static/
│   └── style.css
│
└── templates/
    ├── base.html
    ├── player_login.html
    ├── register.html
    ├── game.html
    ├── admin_home.html
    ├── admin_daily_report.html
    └── admin_user_report.html
