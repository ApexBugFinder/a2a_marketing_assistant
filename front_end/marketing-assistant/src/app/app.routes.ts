import { Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'chat', pathMatch: 'full' },
  {
    path: 'login',
    loadComponent: () => import('./pages/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'auth/callback',
    loadComponent: () =>
      import('./pages/auth-callback/auth-callback.component').then((m) => m.AuthCallbackComponent),
  },
  {
    path: 'chat',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/chat/chat.component').then((m) => m.ChatComponent),
  },
  {
    path: 'deliverables',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/deliverables/deliverables.component').then((m) => m.DeliverablesComponent),
  },
  {
    path: 'history',
    canActivate: [authGuard],
    loadComponent: () => import('./pages/history/history.component').then((m) => m.HistoryComponent),
  },
  { path: '**', redirectTo: 'chat' },
];
