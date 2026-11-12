import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { Role, User } from './models';

const API = environment.apiBase;

export interface CreateUserPayload {
  username: string;
  email: string;
  role: Role;
  password: string;
}

@Injectable({ providedIn: 'root' })
export class UserService {
  private http = inject(HttpClient);

  list(): Observable<User[]> {
    return this.http.get<User[]>(`${API}/users/`);
  }

  create(payload: CreateUserPayload): Observable<User> {
    return this.http.post<User>(`${API}/users/`, payload);
  }
}
