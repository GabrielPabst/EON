import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-home-page',
  standalone: true,
  imports: [],
  templateUrl: './home-page.component.html',
  styleUrl: './home-page.component.css'
})
export class HomePageComponent {
  private router = inject(Router);

  navigateToMacros() {
    this.router.navigate(['/macros']);
  }

  navigateToDownloadApp() {
    this.router.navigate(['/downloadApp']);
  }
}
