import { Routes } from '@angular/router';

import { authGuard, roleGuard } from './core/guards';

export const appRoutes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login').then((m) => m.Login),
  },
  {
    path: '',
    loadComponent: () => import('./layout/shell').then((m) => m.Shell),
    canActivate: [authGuard],
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'dashboard',
        loadComponent: () => import('./features/dashboard/dashboard').then((m) => m.Dashboard),
      },
      {
        path: 'tasks',
        loadComponent: () => import('./features/tasks/task-list').then((m) => m.TaskList),
      },
      {
        path: 'tasks/new',
        loadComponent: () => import('./features/tasks/task-create').then((m) => m.TaskCreate),
        canActivate: [roleGuard('admin', 'manager')],
      },
      {
        path: 'tasks/:id',
        loadComponent: () => import('./features/tasks/task-detail').then((m) => m.TaskDetail),
      },
      {
        path: 'users',
        loadComponent: () => import('./features/users/user-list').then((m) => m.UserList),
        canActivate: [roleGuard('admin', 'manager')],
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
