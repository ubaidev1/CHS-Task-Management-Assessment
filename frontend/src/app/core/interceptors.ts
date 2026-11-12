import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { AuthService } from './auth.service';

const SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS', 'TRACE'];

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Sends the session cookie with every request (withCredentials) and attaches
 * Django's X-CSRFToken header on unsafe methods, reading the non-HttpOnly
 * csrftoken cookie. Cross-origin requests need this explicitly because
 * Angular's built-in XSRF support only covers same-origin calls.
 */
export const credentialsCsrfInterceptor: HttpInterceptorFn = (req, next) => {
  let request = req.clone({ withCredentials: true });

  if (!SAFE_METHODS.includes(req.method.toUpperCase())) {
    const token = readCookie('csrftoken');
    if (token) {
      request = request.clone({ headers: request.headers.set('X-CSRFToken', token) });
    }
  }
  return next(request);
};

/**
 * Global session-expiry handling: a 401 means "not authenticated / session
 * expired", so clear local state and route to login with a notice. 403
 * (forbidden) is left to the calling component to show an inline message.
 */
export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const auth = inject(AuthService);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      const onLogin = router.url.startsWith('/login');
      if (error.status === 401 && !onLogin) {
        auth.clear();
        router.navigate(['/login'], { queryParams: { expired: 1 } });
      }
      return throwError(() => error);
    }),
  );
};
