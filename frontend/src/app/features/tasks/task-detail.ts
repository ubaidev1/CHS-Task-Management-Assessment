import { DatePipe } from '@angular/common';
import { Component, computed, inject, input, signal, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { STATUS_LABELS, Task, TaskStatus, User } from '../../core/models';
import { TaskService } from '../../core/task.service';
import { UserService } from '../../core/user.service';

@Component({
  selector: 'app-task-detail',
  imports: [ReactiveFormsModule, RouterLink, DatePipe],
  templateUrl: './task-detail.html',
  styleUrl: './task-detail.scss',
})
export class TaskDetail implements OnInit {
  private taskService = inject(TaskService);
  private userService = inject(UserService);
  private auth = inject(AuthService);
  private fb = inject(FormBuilder);
  private router = inject(Router);

  /** Bound from the :id route param via withComponentInputBinding(). */
  readonly id = input.required<string>();

  readonly statusLabels = STATUS_LABELS;
  readonly statuses: TaskStatus[] = ['pending', 'in_progress', 'completed'];

  readonly loading = signal(true);
  readonly notFound = signal(false);
  readonly error = signal<string | null>(null);
  readonly success = signal<string | null>(null);
  readonly saving = signal(false);
  readonly task = signal<Task | null>(null);
  readonly users = signal<User[]>([]);

  readonly canManage = computed(() => this.auth.hasRole('admin', 'manager'));
  readonly isAdmin = computed(() => this.auth.hasRole('admin'));
  readonly canChangeStatus = computed(() => {
    const t = this.task();
    const u = this.auth.user();
    return !!t && !!u && (this.canManage() || t.assigned_to === u.id);
  });

  readonly editForm = this.fb.nonNullable.group({
    title: ['', Validators.required],
    description: [''],
  });
  readonly assignCtrl = this.fb.control<number | null>(null);

  ngOnInit(): void {
    this.load();
    if (this.canManage()) {
      this.userService.list().subscribe({ next: (u) => this.users.set(u) });
    }
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.notFound.set(false);
    this.taskService.get(Number(this.id())).subscribe({
      next: (t) => {
        this.task.set(t);
        this.editForm.patchValue({ title: t.title, description: t.description });
        this.assignCtrl.setValue(t.assigned_to);
        this.loading.set(false);
      },
      error: (e) => {
        this.loading.set(false);
        if (e.status === 404) this.notFound.set(true);
        else this.error.set('Could not load this task.');
      },
    });
  }

  changeStatus(status: TaskStatus): void {
    const t = this.task();
    if (!t || t.status === status) return;
    this.clearBanners();
    this.saving.set(true);
    this.taskService.updateStatus(t.id, status).subscribe({
      next: (updated) => {
        this.task.set(updated);
        this.saving.set(false);
        this.success.set('Status updated.');
      },
      error: () => this.fail('Could not update the status.'),
    });
  }

  saveDetails(): void {
    const t = this.task();
    if (!t || this.editForm.invalid) {
      this.editForm.markAllAsTouched();
      return;
    }
    this.clearBanners();
    this.saving.set(true);
    this.taskService.update(t.id, this.editForm.getRawValue()).subscribe({
      next: (updated) => {
        this.task.set(updated);
        this.saving.set(false);
        this.success.set('Task details saved.');
      },
      error: () => this.fail('Could not save changes.'),
    });
  }

  reassign(): void {
    const t = this.task();
    const to = this.assignCtrl.value;
    if (!t || to == null) return;
    this.clearBanners();
    this.saving.set(true);
    this.taskService.assign(t.id, to).subscribe({
      next: (res) => {
        this.saving.set(false);
        this.success.set(
          res.queued ? 'Reassigned — a notification has been queued.' : res.detail,
        );
        this.load();
      },
      error: () => this.fail('Could not reassign the task.'),
    });
  }

  remove(): void {
    const t = this.task();
    if (!t || !confirm(`Delete task "${t.title}"? This cannot be undone.`)) return;
    this.clearBanners();
    this.saving.set(true);
    this.taskService.remove(t.id).subscribe({
      next: () => this.router.navigate(['/tasks']),
      error: () => this.fail('Could not delete the task.'),
    });
  }

  private clearBanners(): void {
    this.success.set(null);
    this.error.set(null);
  }

  private fail(msg: string): void {
    this.saving.set(false);
    this.error.set(msg);
  }
}
