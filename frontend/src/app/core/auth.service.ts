import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { environment } from '../../environments/environment';
import { Role, SessionInfo, User } from './models';

const API = environment.apiBase;

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);

  /** Current user, or null when signed out. Drives guards and nav. */
  readonly user = signal<User | null>(null);
  readonly isAuthenticated = computed(() => this.user() !== null);

  /** Convenience role check used by templates. */
  hasRole(...roles: Role[]): boolean {
    const u = this.user();
    return !!u && roles.includes(u.role);
  }

  /**
   * Resolve the current session AND seed the CSRF cookie. Called at startup,
   * so guards know who is signed in before the first route activates.
   */
  initSession(): Observable<SessionInfo> {
    return this.http
      .get<SessionInfo>(`${API}/auth/session/`)
      .pipe(tap((s) => this.user.set(s.authenticated && s.user ? s.user : null)));
  }

  login(username: string, password: string): Observable<User> {
    return this.http
      .post<User>(`${API}/auth/login/`, { username, password })
      .pipe(tap((u) => this.user.set(u)));
  }

  logout(): Observable<void> {
    return this.http
      .post<void>(`${API}/auth/logout/`, {})
      .pipe(tap(() => this.user.set(null)));
  }

  /** Clear local auth state (used by the error interceptor on 401). */
  clear(): void {
    this.user.set(null);
  }
}
