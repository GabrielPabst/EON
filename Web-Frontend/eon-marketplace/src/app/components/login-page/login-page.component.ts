import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgClass } from '@angular/common';
import { Router } from '@angular/router';
import { MacroService } from '../../services/macro.service';

@Component({
  selector: 'app-login-page',
  standalone: true,
  imports: [FormsModule, NgClass],
  templateUrl: './login-page.component.html',
  styleUrl: './login-page.component.css'
})
export class LoginPageComponent {
  constructor(private api: MacroService, private router: Router) {}

  mode: 'login' | 'signup' = 'login';
  busy = false;
  message = '';
  error = '';

  creds = {
    name: '',
    password: '',
    confirm: ''
  };

  switchMode(next: 'login' | 'signup') {
    if (this.mode === next) return;
    this.mode = next;
    this.message = '';
    this.error = '';
    this.creds.password = '';
    this.creds.confirm = '';
  }

  submit() {
    this.message = '';
    this.error = '';

    if (!this.creds.name || !this.creds.password) {
      this.error = 'Bitte Benutzername und Passwort eingeben.';
      return;
    }
    if (this.mode === 'signup' && this.creds.password !== this.creds.confirm) {
      this.error = 'Passwörter stimmen nicht überein.';
      return;
    }

    this.busy = true;

    const req$ = this.mode === 'login'
      ? this.api.login(this.creds.name, this.creds.password)
      : this.api.register(this.creds.name, this.creds.password);

    req$.subscribe({
      next: () => {
        this.busy = false;
        // Optional: kurze Erfolgsmeldung, dann Redirect
        // this.message = this.mode === 'login' ? 'Erfolgreich angemeldet.' : 'Konto erstellt.';
        this.router.navigateByUrl('/home');
      },
      error: (err) => {
        this.busy = false;
        this.error =
          err?.error?.message ||
          err?.error?.error ||
          err?.statusText ||
          'Vorgang fehlgeschlagen.';
      }
    });
  }
}
