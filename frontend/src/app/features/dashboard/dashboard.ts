import { Component, computed, inject, signal, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { DashboardService } from '../../core/dashboard.service';
import { DashboardStats, ROLE_LABELS } from '../../core/models';

@Component({
  selector: 'app-dashboard',
  imports: [RouterLink],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard implements OnInit {
  private dash = inject(DashboardService);
  private auth = inject(AuthService);

  readonly user = this.auth.user;
  readonly roleLabels = ROLE_LABELS;
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly stats = signal<DashboardStats | null>(null);

  readonly completion = computed(() => {
    const s = this.stats();
    if (!s || s.total_tasks === 0) return 0;
    return Math.round((s.completed_tasks / s.total_tasks) * 100);
  });

  /** SVG progress ring geometry (r = 54). */
  readonly RING_C = 2 * Math.PI * 54;
  readonly ringOffset = computed(() => this.RING_C * (1 - this.completion() / 100));

  readonly scopeNote = computed(() =>
    this.auth.hasRole('admin', 'manager')
      ? 'Showing statistics across all tasks.'
      : 'Showing statistics for tasks assigned to you.',
  );

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.dash.stats().subscribe({
      next: (s) => {
        this.stats.set(s);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Could not load dashboard statistics.');
        this.loading.set(false);
      },
    });
  }
}
