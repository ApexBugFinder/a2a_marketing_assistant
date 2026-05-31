import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { environment } from '../../environments/environment';
import { AppUser } from '../models/user.model';

const STORAGE_KEY = 'ma_auth';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private router = inject(Router);

  private _user = new BehaviorSubject<AppUser | null>(this.readStoredUser());
  user$ = this._user.asObservable();

  isAuthenticated(): boolean {
    return this._user.value !== null;
  }

  get currentUser(): AppUser | null {
    return this._user.value;
  }

  /**
   * Kicks off the LinkedIn sign-in.
   *
   * In mock mode (environment.mockAuth) we skip a real LinkedIn app and route
   * straight to our own callback with a fake `code`, simulating the OAuth
   * redirect round-trip. In real mode we send the browser to LinkedIn's
   * authorize endpoint (the user is returned to linkedinRedirectUri with a code).
   */
  loginWithLinkedIn(): void {
    const state = this.randomState();
    sessionStorage.setItem('ma_oauth_state', state);

    if (environment.mockAuth) {
      // MOCK — pretend LinkedIn redirected back to us with an auth code.
      const code = 'mock_' + state;
      this.router.navigate(['/auth/callback'], { queryParams: { code, state } });
      return;
    }

    const params = new URLSearchParams({
      response_type: 'code',
      client_id: environment.linkedinClientId,
      redirect_uri: environment.linkedinRedirectUri,
      scope: environment.linkedinScope,
      state,
    });
    window.location.href = `${environment.linkedinAuthUrl}?${params.toString()}`;
  }

  /**
   * Completes sign-in given the `code` returned to the callback route.
   * Resolves to the authenticated user, or null on failure.
   */
  async handleCallback(code: string | null, state: string | null): Promise<AppUser | null> {
    if (!code) return null;

    const expectedState = sessionStorage.getItem('ma_oauth_state');
    if (state && expectedState && state !== expectedState) {
      return null; // CSRF guard — state mismatch
    }
    sessionStorage.removeItem('ma_oauth_state');

    let user: AppUser;
    if (environment.mockAuth) {
      // MOCK token exchange — replace with a POST to a backend
      // /auth/linkedin/callback that exchanges `code` via the LinkedIn OIDC
      // token endpoint (openid profile email) and returns the real profile.
      user = {
        name: 'LinkedIn Member',
        email: 'member@linkedin.com',
        linkedinUrn: 'urn:li:person:MOCK',
      };
    } else {
      // Real exchange would live here (backend call). Until then, fail closed.
      return null;
    }

    this.persist(user);
    return user;
  }

  logout(): void {
    localStorage.removeItem(STORAGE_KEY);
    this._user.next(null);
    this.router.navigate(['/login']);
  }

  private persist(user: AppUser): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    this._user.next(user);
  }

  private readStoredUser(): AppUser | null {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? (JSON.parse(raw) as AppUser) : null;
    } catch {
      return null;
    }
  }

  private randomState(): string {
    return (
      Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2)
    );
  }
}
