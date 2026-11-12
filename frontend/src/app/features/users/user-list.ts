import { Component, computed, inject, signal, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { AuthService } from '../../core/auth.service';
import { ROLE_LABELS, Role, User } from '../../core/models';
import { NotificationService } from '../../core/notification.service';
import { UserService } from '../../core/user.service';

@Component({
  selector: 'app-user-list',
  imports: [ReactiveFormsModule],
  templateUrl: './user-list.html',
  styleUrl: './user-list.scss',
})
export class UserList implements OnInit {
  private userService = inject(UserService);
  private auth = inject(AuthService);
  private fb = inject(FormBuilder);
  private notify = inject(NotificationService);

  readonly roleLabels = ROLE_LABELS;
  readonly roles: Role[] = ['employee', 'manager', 'admin'];

  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly users = signal<User[]>([]);

  readonly showForm = signal(false);
  readonly saving = signal(false);
  readonly createError = signal<string | null>(null);

  readonly isAdmin = computed(() => this.auth.hasRole('admin'));

  readonly form = this.fb.nonNullable.group({
    username: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    role: this.fb.nonNullable.control<Role>('employee'),
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.userService.list().subscribe({
      next: (u) => {
        this.users.set(u);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Could not load users.');
        this.loading.set(false);
      },
    });
  }

  toggleForm(): void {
    this.showForm.update((v) => !v);
    this.createError.set(null);
  }

  invalid(name: string): boolean {
    const c = this.form.get(name);
    return !!c && c.invalid && c.touched;
  }

  submit(): void {
    this.createError.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.userService.create(this.form.getRawValue()).subscribe({
      next: (created) => {
        this.users.update((list) => [...list, created]);
        this.saving.set(false);
        this.showForm.set(false);
        this.form.reset({ username: '', email: '', role: 'employee', password: '' });
        this.notify.success(`User “${created.username}” created.`);
      },
      error: (e) => {
        this.saving.set(false);
        this.createError.set(this.flattenError(e));
      },
    });
  }

  private flattenError(err: unknown): string {
    const e = (err as { error?: unknown })?.error;
    if (!e) return 'Could not create the user.';
    if (typeof e === 'string') return e;
    const obj = e as Record<string, unknown>;
    if (typeof obj['detail'] === 'string') return obj['detail'] as string;
    const parts = Object.entries(obj).map(
      ([k, v]) => `${k}: ${Array.isArray(v) ? v.join(' ') : v}`,
    );
    return parts.join(' • ') || 'Could not create the user.';
  }
}
