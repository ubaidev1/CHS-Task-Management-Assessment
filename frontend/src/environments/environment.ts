export const environment = {
  production: false,
  // Absolute API origin so the real cross-origin CORS + session/CSRF flow is
  // exercised (frontend :4200, backend :8000). Override for other deployments.
  apiBase: 'http://localhost:8000/api',
};
