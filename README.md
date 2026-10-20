# Galactic Guardians

A space shooter in a single Python file (`Galactic Guardians.py`). It has a server/client mode so friends on the same network can play together, and a log of game events that is chained with hashes like a small blockchain.

## What it does

- Pygame window with PyOpenGL rendering for the ship, lasers and aliens.
- Socket-based multiplayer: one player runs the server, others connect over the local network.
- Encrypted traffic between players using the `cryptography` package.
- Game events (lasers fired, aliens destroyed) written to a simple blockchain-style log so they cannot be edited quietly afterwards.
- Single-player mode as well.

## Running it

```bash
pip install pygame PyOpenGL cryptography
python "Galactic Guardians.py"
```

Choose server or client mode when it starts. Clients need the server's local IP.

## Why I built it

A way to practise sockets, encryption and hash chaining in something more fun than an exercise.
