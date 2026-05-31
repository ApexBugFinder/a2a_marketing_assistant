import { Component, inject, signal } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { AuthService } from './services/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    AsyncPipe,
    RouterOutlet, RouterLink, RouterLinkActive,
    MatSidenavModule, MatListModule, MatIconModule, MatButtonModule,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private router = inject(Router);
  private auth = inject(AuthService);

  user$ = this.auth.user$;

  // Hide the app shell (sidenav) on auth screens — they render full-bleed.
  shellVisible = signal(this.computeShellVisible(this.router.url));

  navItems = [
    { label: 'Chat',    icon: 'chat',        route: '/chat' },
    { label: 'Review',  icon: 'rate_review',  route: '/deliverables' },
    { label: 'History', icon: 'history',      route: '/history' },
  ];

  constructor() {
    this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe((e) => this.shellVisible.set(this.computeShellVisible(e.urlAfterRedirects)));
  }

  logout(): void {
    this.auth.logout();
  }

  initial(name: string | undefined | null): string {
    return name?.trim()?.charAt(0)?.toUpperCase() || '?';
  }

  private computeShellVisible(url: string): boolean {
    return !(url.startsWith('/login') || url.startsWith('/auth'));
  }
}
