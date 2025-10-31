import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AsyncPipe } from '@angular/common';
import { MacroService } from './services/macro.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLinkActive, RouterLink, AsyncPipe],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  title = 'EON-Marketplace';

  constructor(private api: MacroService) {}
  get isLoggedIn$() {
    return this.api.isLoggedIn$;
  }

  logout() {
    this.api.logout().subscribe();
  }
}
