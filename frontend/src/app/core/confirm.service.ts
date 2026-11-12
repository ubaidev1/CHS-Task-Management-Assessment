import { Injectable, signal } from '@angular/core';

export interface ConfirmOptions {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
}

@Injectable({ providedIn: 'root' })
export class ConfirmService {
  readonly request = signal<ConfirmOptions | null>(null);
  private resolver?: (value: boolean) => void;

  /** Open a confirmation dialog; resolves true if confirmed, false if cancelled. */
  ask(options: ConfirmOptions): Promise<boolean> {
    this.request.set(options);
    return new Promise<boolean>((resolve) => {
      this.resolver = resolve;
    });
  }

  resolve(value: boolean): void {
    this.request.set(null);
    this.resolver?.(value);
    this.resolver = undefined;
  }
}
