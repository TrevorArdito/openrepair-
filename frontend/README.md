# Frontend (React + Vite + Tailwind PWA)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (API calls are proxied to http://localhost:8000)
npm test           # unit tests
npm run build      # production build in dist/ (includes the offline service worker)
```

- `src/features/<feature>/` — pages per feature (vehicles, garage, account, …)
- `src/components/` — shop-friendly UI kit (big buttons, high contrast, dark mode)
- `src/i18n/locales/en/common.json` — **all** user-facing text. Never hard-code strings.
- `src/lib/` — API client, unit conversion (store metric, show metric or imperial), VIN checks.
