# Preboard frontend

The React interface is part of the fused Preboard repository. Use the root setup commands:

```bash
make install
cp .env.example .env
cp frontend/.env.example frontend/.env.local
make dev
```

React runs at `http://localhost:3000` and calls the Python API at `http://127.0.0.1:8000` through authenticated server-side routes. See the root `README.md` for accounts, security boundaries, testing, and Databricks configuration.
