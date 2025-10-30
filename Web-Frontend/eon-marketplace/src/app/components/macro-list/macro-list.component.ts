import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Macro } from '../../models/macro.model';
import { MacroService } from '../../services/macro.service';

@Component({
  selector: 'app-macro-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './macro-list.component.html',
  styleUrls: ['./macro-list.component.css']
})
export class MacroListComponent implements OnInit {
  nameFilter = '';
  categoryFilter = 'Alle';
  showCategoryImage = false;

  categories = ['Alle', 'Word', 'Excel', 'Multimedia', 'PDF', 'Netzwerk', 'Tools'];
  macros: Macro[] = [];
  busy = false;

  // Optional: statische Thumbnails pro Kategorie
  categoryImageMap: Record<string, string> = {
    Word: 'assets/word.png',
    Excel: 'assets/excel.png',
    Multimedia: 'assets/multimedia.png',
    PDF: 'assets/pdf.png',
    Netzwerk: 'assets/network.png',
    Tools: 'assets/tools.png'
  };

  constructor(private router: Router, private api: MacroService) {}

  ngOnInit(): void {
    // Stream abonnieren
    this.api.stream().subscribe(list => (this.macros = list));
    // Initial: komplette Marketplace-Liste
    this.loadMarketplace();
  }

  // --- Backend Calls ---
  loadMarketplace(page = 1, perPage = 30) {
    this.busy = true;
    this.api.fetchMarketplace(page, perPage).subscribe({
      next: () => (this.busy = false),
      error: () => (this.busy = false)
    });
  }

  runSearch(page = 1, perPage = 30) {
    const q = this.nameFilter.trim();
    const usecase = this.categoryFilter !== 'Alle' ? this.categoryFilter : undefined;

    // Ohne Filter → Marketplace
    if (!q && !usecase) {
      this.loadMarketplace(page, perPage);
      return;
    }

    this.busy = true;
    this.api.search(q, usecase, undefined, page, perPage).subscribe({
      next: () => (this.busy = false),
      error: () => (this.busy = false)
    });
  }

  // --- UI Events ---
  onFilterChange() {
    this.runSearch();
  }

  // --- Helpers/UI ---
  getImagePath(category: string): string {
    return this.categoryImageMap[category] || '';
  }

  goToDetail(id: string) {
    this.router.navigate(['/macro', id]);
  }

  onImgError(event: Event) {
    (event.target as HTMLImageElement).style.display = 'none';
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

  categoryTagClass(category: string) {
    return {
      'text-purple-400 border-purple-400': category === 'Multimedia',
      'text-pink-400 border-pink-400': category === 'PDF',
      'text-green-400 border-green-400': category === 'Excel',
      'text-blue-400 border-blue-400': category === 'Word',
      'text-yellow-400 border-yellow-400': category === 'Netzwerk' || category === 'Tools'
    };
  }
}
