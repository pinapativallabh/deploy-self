# Bonk frontend

The Bonk frontend is a Next.js application for the self-hosted deployment control plane.

## Local development

```bash
npm ci
npm run dev
```

The browser client requires the backend at `http://localhost:8000`. Docker Compose configures this automatically. Open `http://localhost:3000/login` to sign in.

## Quality checks

```bash
npm run lint
npm run build
```

For full-stack setup and deployment instructions, see the repository [README](../README.md).
