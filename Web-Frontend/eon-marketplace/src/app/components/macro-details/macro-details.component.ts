import { Component, inject } from '@angular/core';
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
export class MacroDetailsComponent {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private macroService = inject(MacroService);

  macro: Macro | undefined;

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
    if (id) {
      this.macro = this.macroService.getAll().find(m => m.id === id);
    }
  }

  backToList() {
    this.router.navigate(['/macros']);
  }

  download() {
    if (this.macro) {
      const exampleContent = `# ${this.macro.name}\n\n${this.macro.description}\n\nKategorie: ${this.macro.category}`;
      const blob = new Blob([exampleContent], { type: 'text/plain' });

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = this.macro.filename || 'macro.txt';
      a.click();
      URL.revokeObjectURL(url);
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
}
