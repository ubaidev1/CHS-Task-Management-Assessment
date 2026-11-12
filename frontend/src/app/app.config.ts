import { provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  ApplicationConfig,
  inject,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
  provideZoneChangeDetection,
} from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { catchError, firstValueFrom, of } from 'rxjs';

import { AuthService } from './core/auth.service';
import { credentialsCsrfInterceptor, errorInterceptor } from './core/interceptors';
import { appRoutes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(appRoutes, withComponentInputBinding()),
    provideHttpClient(withInterceptors([credentialsCsrfInterceptor, errorInterceptor])),
    // Resolve the session (and seed the CSRF cookie) before the first route, so
    // guards see the correct auth state on a hard refresh.
    provideAppInitializer(() => {
      const auth = inject(AuthService);
      return firstValueFrom(auth.initSession().pipe(catchError(() => of(null))));
    }),
  ],
};
