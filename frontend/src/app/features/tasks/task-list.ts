import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { STATUS_LABELS, Task, TaskStatus } from '../../core/models';
import { TaskService } from '../../core/task.service';

type Filter = 'all' | TaskStatus;

@Component({
  selector: 'app-task-list',
  imports: [RouterLink, DatePipe],
  templateUrl: './task-list.html',
  styleUrl: './task-list.scss',
})
export class TaskList implements OnInit {
  private taskService = inject(TaskService);
  private auth = inject(AuthService);

  readonly statusLabels = STATUS_LABELS;
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly tasks = signal<Task[]>([]);
  readonly filter = signal<Filter>('all');

  readonly canManage = computed(() => this.auth.hasRole('admin', 'manager'));

  readonly filters: { key: Filter; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'pending', label: 'Pending' },
    { key: 'in_progress', label: 'In progress' },
    { key: 'completed', label: 'Completed' },
  ];

  readonly filtered = computed(() => {
    const f = this.filter();
    const all = this.tasks();
    return f === 'all' ? all : all.filter((t) => t.status === f);
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.taskService.list().subscribe({
      next: (tasks) => {
        this.tasks.set(tasks);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Could not load tasks.');
        this.loading.set(false);
      },
    });
  }

  countFor(key: Filter): number {
    return key === 'all'
      ? this.tasks().length
      : this.tasks().filter((t) => t.status === key).length;
  }
}
