import { Component, inject } from '@angular/core';

import { ConfirmService } from '../core/confirm.service';

@Component({
  selector: 'app-confirm-dialog',
  template: `
    @if (request(); as r) {
      <div class="overlay" (click)="cancel()">
        <div class="modal" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
          <div class="icon" [class.danger]="r.danger">{{ r.danger ? '!' : '?' }}</div>
          <h3>{{ r.title }}</h3>
          <p>{{ r.message }}</p>
          <div class="actions">
            <button class="btn btn-ghost" (click)="cancel()">{{ r.cancelText || 'Cancel' }}</button>
            <button
              class="btn"
              [class.btn-danger]="r.danger"
              [class.btn-primary]="!r.danger"
              (click)="confirm()"
            >
              {{ r.confirmText || 'Confirm' }}
            </button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [
    `
      .overlay {
        position: fixed; inset: 0; z-index: 70;
        background: rgba(22, 32, 30, 0.42); backdrop-filter: blur(2px);
        display: grid; place-items: center; padding: 20px;
        animation: fade 0.18s ease both;
      }
      @keyframes fade { from { opacity: 0; } to { opacity: 1; } }
      .modal {
        width: 100%; max-width: 400px; background: var(--surface);
        border-radius: var(--radius-lg); padding: 28px; text-align: center;
        box-shadow: var(--shadow-lg);
        animation: pop 0.24s cubic-bezier(0.2, 0.7, 0.2, 1) both;
      }
      @keyframes pop { from { opacity: 0; transform: translateY(10px) scale(0.97); } to { opacity: 1; transform: none; } }
      .icon {
        width: 52px; height: 52px; margin: 0 auto 16px; border-radius: 50%;
        display: grid; place-items: center; font-size: 1.5rem; font-weight: 800;
        background: var(--accent-soft); color: var(--accent-700);
      }
      .icon.danger { background: var(--danger-bg); color: var(--danger); }
      .modal h3 { font-size: 1.25rem; }
      .modal p { color: var(--muted); margin: 10px 0 24px; line-height: 1.55; }
      .actions { display: flex; gap: 10px; justify-content: center; }
      .actions .btn { min-width: 110px; }
    `,
  ],
})
export class ConfirmDialog {
  private service = inject(ConfirmService);
  readonly request = this.service.request;

  confirm(): void {
    this.service.resolve(true);
  }

  cancel(): void {
    this.service.resolve(false);
  }
}
