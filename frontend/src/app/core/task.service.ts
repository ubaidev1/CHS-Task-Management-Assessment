import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { Task, TaskStatus } from './models';

const API = environment.apiBase;

export interface AssignResponse {
  detail: string;
  queued: boolean;
  event_id?: string;
}

@Injectable({ providedIn: 'root' })
export class TaskService {
  private http = inject(HttpClient);

  list(): Observable<Task[]> {
    return this.http.get<Task[]>(`${API}/tasks/`);
  }

  get(id: number): Observable<Task> {
    return this.http.get<Task>(`${API}/tasks/${id}/`);
  }

  create(payload: Partial<Task>): Observable<Task> {
    return this.http.post<Task>(`${API}/tasks/`, payload);
  }

  update(id: number, payload: Partial<Task>): Observable<Task> {
    return this.http.patch<Task>(`${API}/tasks/${id}/`, payload);
  }

  updateStatus(id: number, status: TaskStatus): Observable<Task> {
    return this.http.patch<Task>(`${API}/tasks/${id}/`, { status });
  }

  remove(id: number): Observable<void> {
    return this.http.delete<void>(`${API}/tasks/${id}/`);
  }

  assign(id: number, assignedTo: number): Observable<AssignResponse> {
    return this.http.post<AssignResponse>(`${API}/tasks/${id}/assign/`, {
      assigned_to: assignedTo,
    });
  }
}
