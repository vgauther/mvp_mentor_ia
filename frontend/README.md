# Frontend Mentor IA

Application Vue 3 + TypeScript du squelette Mentor IA.

```bash
cp .env.example .env
npm ci
npm run dev
```

Le démarrage initialise Keycloak en mode `login-required`, puis appelle
`GET /api/me/` avec le jeton d'accès obtenu.

Commandes utiles :

```bash
npm run type-check
npm run test:unit -- --run
npm run build
```
