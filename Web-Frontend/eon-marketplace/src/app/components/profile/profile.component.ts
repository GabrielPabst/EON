import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Macro } from '../../models/macro.model';
import { MacroService } from '../../services/macro.service';

type AccountView = { id: number; name: string; created_at: string } | null;

@Component({
  selector: 'app-account-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './profile.component.html',
  styleUrl: './profile.component.css'
})
export class ProfileComponent implements OnInit {
  private api = inject(MacroService);
  private router = inject(Router);

  // Account-Infos
  account: AccountView = null;

  // Filter
  nameFilter = '';
  categoryFilter = 'Alle';
  categories = ['Alle', 'Word', 'Excel', 'Multimedia', 'PDF', 'Netzwerk', 'Tools'];

  // UI-State
  loading = false;
  message = '';
  error = '';

  // Pagination (einfach)
  page = 1;
  perPage = 24;

  myMacros: Macro[] = [];

  ngOnInit(): void {
    // Account laden (Name anzeigen, "seit" etc.)
    this.api.getAccount().subscribe({
      next: (r) => this.account = r.account,
      error: () => this.account = null
    });

    this.loadMyMacros();
  }

  loadMyMacros(): void {
    this.loading = true;
    this.error = '';
    this.api.getMyMakros(this.page, this.perPage).subscribe({
      next: () => {
        this.myMacros = this.api.getAll();
        this.loading = false;
      },
      error: (err) => {
        this.error = err?.error?.error || err?.statusText || 'Konnte Makros nicht laden.';
        this.loading = false;
      }
    });
  }

  get filtered(): Macro[] {
    const name = this.nameFilter.toLowerCase();
    return this.myMacros.filter(m =>
      (!name || m.name.toLowerCase().includes(name)) &&
      (this.categoryFilter === 'Alle' || m.category === this.categoryFilter)
    );
  }

  goToDetail(id: string) {
    this.router.navigate(['/macro', id]);
  }

  goToUpload() {
    this.router.navigate(['/upload']);
  }

  delete(m: Macro) {
    if (!confirm(`„${m.name}“ wirklich löschen?`)) return;
    this.message = '';
    this.error = '';
    this.api.delete(m.id).subscribe({
      next: () => {
        this.message = 'Makro gelöscht.';
        this.myMacros = this.api.getAll();
      },
      error: (err) => {
        this.error = err?.error?.error || err?.statusText || 'Löschen fehlgeschlagen.';
      }
    });
  }

  categoryBorder(category: string) {
    return {
      'border-purple-500 hover:shadow-purple-500/40': category === 'Multimedia',
      'border-pink-500 hover:shadow-pink-500/40': category === 'PDF',
      'border-green-500 hover:shadow-green-500/40': category === 'Excel',
      'border-blue-500 hover:shadow-blue-500/40': category === 'Word',
      'border-yellow-400 hover:shadow-yellow-500/40': category === 'Netzwerk' || category === 'Tools',
      'border-white/10': !category
    };
  }
}
