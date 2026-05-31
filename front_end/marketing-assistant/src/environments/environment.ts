export const environment = {
  production: false,
  agentApiUrl: 'http://localhost:10113',
  toolsApiUrl: 'http://localhost:8000',

  // LinkedIn OAuth — placeholders for the real flow. Unused while auth is mocked
  // (see auth.service.ts). To go live: register these in your LinkedIn app and
  // swap the mock token exchange for a backend /auth/linkedin/callback call.
  linkedinClientId: 'YOUR_LINKEDIN_CLIENT_ID',
  linkedinRedirectUri: 'http://localhost:4200/auth/callback',
  linkedinScope: 'openid profile email',
  linkedinAuthUrl: 'https://www.linkedin.com/oauth/v2/authorization',

  // Toggle: when true, auth.service simulates the LinkedIn round-trip without a
  // real LinkedIn app. Set false once the backend callback endpoint exists.
  mockAuth: true,
};
