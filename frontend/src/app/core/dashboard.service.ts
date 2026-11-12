import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { DashboardStats } from './models';

const API = environment.apiBase;

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private http = inject(HttpClient);

  stats(): Observable<DashboardStats> {
    return this.http.get<DashboardStats>(`${API}/dashboard/stats/`);
  }
}
