import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Macro } from '../../models/macro.model';
import { MacroService } from '../../services/macro.service';

@Component({
  selector: 'app-macro-details',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './macro-details.component.html',
  styleUrl: './macro-details.component.css'
})
export class MacroDetailsComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private api = inject(MacroService);

  macro: Macro | undefined;
  busy = false;
  error = '';

  categoryImageMap: Record<string, string> = {
    Word: 'assets/word.png',
    Excel: 'assets/excel.png',
    Multimedia: 'assets/multimedia.png',
    PDF: 'assets/pdf.png',
    Netzwerk: 'assets/network.png',
    Tools: 'assets/tools.png'
  };

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.error = 'Keine ID angegeben.';
      return;
    }

    const cached = this.api.getAll().find(m => m.id === id);
    if (cached) {
      this.macro = cached;
      return;
    }

    this.busy = true;
    this.api.getById(id).subscribe({
      next: m => { this.macro = m; this.busy = false; },
      error: err => {
        this.error = err?.error?.message || err?.statusText || 'Makro nicht gefunden.';
        this.busy = false;
      }
    });
  }

  backToList() {
    this.router.navigate(['/macros']);
  }

  download() {
    if (this.macro) {
      this.api.download(this.macro.id).subscribe();
    }
  }

  get categoryImage(): string {
    if (this.macro && this.macro.category) {
      return this.categoryImageMap[this.macro.category] || 'assets/default.webp';
    }
    return 'assets/default.webp';
  }

  get categoryAlt(): string {
    return this.macro?.category ?? 'Kategorie';
  }

  isVideo(url: string): boolean {
    return /\.(mp4|webm)$/i.test(url);
  }
}
