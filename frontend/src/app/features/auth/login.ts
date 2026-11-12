import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly expired = signal(this.route.snapshot.queryParamMap.has('expired'));

  readonly demos = [
    { role: 'Admin', username: 'admin', password: 'Admin@12345' },
    { role: 'Manager', username: 'manager', password: 'Manager@12345' },
    { role: 'Employee', username: 'employee', password: 'Employee@12345' },
  ];

  readonly form = this.fb.nonNullable.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
  });

  invalid(name: 'username' | 'password'): boolean {
    const c = this.form.get(name);
    return !!c && c.invalid && c.touched;
  }

  fill(username: string, password: string): void {
    this.form.setValue({ username, password });
  }

  submit(): void {
    this.error.set(null);
    this.expired.set(false);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.loading.set(true);
    const { username, password } = this.form.getRawValue();
    this.auth.login(username, password).subscribe({
      next: () => this.router.navigateByUrl('/dashboard'),
      error: (e) => {
        this.loading.set(false);
        this.error.set(e?.error?.detail ?? 'Unable to sign in. Please try again.');
      },
    });
  }
}
