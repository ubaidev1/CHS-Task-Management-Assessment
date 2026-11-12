import { Component, inject } from '@angular/core';

import { NotificationService } from '../core/notification.service';

@Component({
  selector: 'app-toasts',
  template: `
    <div class="toast-wrap">
      @for (t of toasts(); track t.id) {
        <div class="toast toast-{{ t.type }}">
          <span class="t-ico">{{ t.type === 'success' ? '✓' : '!' }}</span>
          <span class="t-text">{{ t.text }}</span>
          <button class="t-close" (click)="dismiss(t.id)" aria-label="Dismiss">×</button>
        </div>
      }
    </div>
  `,
  styles: [
    `
      .toast-wrap {
        position: fixed; top: 18px; right: 18px; z-index: 60;
        display: flex; flex-direction: column; gap: 10px; max-width: 360px;
      }
      .toast {
        display: flex; align-items: center; gap: 11px;
        padding: 13px 15px; border-radius: 13px; background: var(--surface);
        border: 1px solid var(--line); box-shadow: var(--shadow-lg);
        animation: toast-in 0.26s cubic-bezier(0.2, 0.7, 0.2, 1) both;
      }
      @keyframes toast-in { from { opacity: 0; transform: translateX(16px) scale(0.98); } to { opacity: 1; transform: none; } }
      .t-ico {
        width: 24px; height: 24px; flex: none; border-radius: 50%;
        display: grid; place-items: center; font-size: 0.8rem; font-weight: 800; color: #fff;
      }
      .toast-success .t-ico { background: var(--done); }
      .toast-error .t-ico { background: var(--danger); }
      .t-text { font-size: 0.9rem; font-weight: 500; color: var(--text); line-height: 1.4; }
      .t-close {
        margin-left: auto; background: none; border: none; cursor: pointer;
        color: var(--muted-2); font-size: 1.25rem; line-height: 1; padding: 0 2px;
      }
      .t-close:hover { color: var(--text); }
    `,
  ],
})
export class Toasts {
  private service = inject(NotificationService);
  readonly toasts = this.service.toasts;

  dismiss(id: number): void {
    this.service.dismiss(id);
  }
}
