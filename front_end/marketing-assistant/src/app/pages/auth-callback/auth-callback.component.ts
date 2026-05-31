import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-auth-callback',
  standalone: true,
  imports: [],
  templateUrl: './auth-callback.component.html',
  styleUrl: './auth-callback.component.scss',
})
export class AuthCallbackComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private auth = inject(AuthService);

  error = signal(false);

  async ngOnInit(): Promise<void> {
    const code = this.route.snapshot.queryParamMap.get('code');
    const state = this.route.snapshot.queryParamMap.get('state');

    const user = await this.auth.handleCallback(code, state);
    if (user) {
      this.router.navigate(['/chat']);
    } else {
      this.error.set(true);
    }
  }

  backToLogin(): void {
    this.router.navigate(['/login']);
  }
}
