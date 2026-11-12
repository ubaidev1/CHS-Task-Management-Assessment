import { Component, inject, signal, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { STATUS_LABELS, TaskStatus, User } from '../../core/models';
import { NotificationService } from '../../core/notification.service';
import { TaskService } from '../../core/task.service';
import { UserService } from '../../core/user.service';

@Component({
  selector: 'app-task-create',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './task-create.html',
  styleUrl: './task-create.scss',
})
export class TaskCreate implements OnInit {
  private taskService = inject(TaskService);
  private userService = inject(UserService);
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private notify = inject(NotificationService);

  readonly statusLabels = STATUS_LABELS;
  readonly statuses: TaskStatus[] = ['pending', 'in_progress', 'completed'];
  readonly users = signal<User[]>([]);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);

  readonly form = this.fb.nonNullable.group({
    title: ['', [Validators.required, Validators.maxLength(255)]],
    description: [''],
    assigned_to: this.fb.control<number | null>(null),
    status: this.fb.nonNullable.control<TaskStatus>('pending'),
  });

  ngOnInit(): void {
    this.userService.list().subscribe({
      next: (u) => this.users.set(u),
      error: () => this.error.set('Could not load the user list.'),
    });
  }

  invalidTitle(): boolean {
    const c = this.form.get('title');
    return !!c && c.invalid && c.touched;
  }

  submit(): void {
    this.error.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    const v = this.form.getRawValue();
    const payload = {
      title: v.title,
      description: v.description,
      status: v.status,
      ...(v.assigned_to != null ? { assigned_to: v.assigned_to } : {}),
    };
    this.taskService.create(payload).subscribe({
      next: (task) => {
        this.notify.success(
          payload.assigned_to
            ? 'Task created and assigned — a notification has been queued.'
            : 'Task created.',
        );
        this.router.navigate(['/tasks', task.id]);
      },
      error: () => {
        this.saving.set(false);
        this.error.set('Could not create the task. Please try again.');
      },
    });
  }
}
