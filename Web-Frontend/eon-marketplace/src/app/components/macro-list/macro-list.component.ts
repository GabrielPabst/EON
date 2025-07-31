import { Component, OnInit, inject } from '@angular/core';
import { Macro } from '../../models/macro.model';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClientModule, HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-macro-list',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule],
  templateUrl: './macro-list.component.html',
  styleUrls: ['./macro-list.component.css']
})
export class MacroListComponent implements OnInit {
  nameFilter = '';
  categoryFilter = 'Alle';
  showCategoryImage = false;

  categories = ['Alle', 'Word', 'Excel', 'Multimedia', 'PDF', 'Netzwerk', 'Tools'];
  macros: Macro[] = [];

  http = inject(HttpClient);

  categoryImageMap: Record<string, string> = {
    Word: 'assets/word.png',
    Excel: 'assets/excel.png',
    Multimedia: 'assets/multimedia.png',
    PDF: 'assets/pdf.png',
    Netzwerk: 'assets/network.png',
    Tools: 'assets/tools.png'
  };

  constructor(private router: Router) {}

  ngOnInit(): void {
    this.http.get<Macro[]>('assets/macros.json').subscribe(data => {
      this.macros = data.map(m => ({
        ...m,
        file: null,
        createdAt: new Date(m.createdAt)
      }));
    });
  }

  get filteredMacros(): Macro[] {
    return this.macros.filter(macro =>
      macro.name.toLowerCase().includes(this.nameFilter.toLowerCase()) &&
      (this.categoryFilter === 'Alle' || macro.category === this.categoryFilter)
    );
  }


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
    };
  }

  categoryTagClass(category: string) {
    return {
      'text-purple-400 border-purple-400': category === 'Multimedia',
      'text-pink-400 border-pink-400': category === 'PDF',
      'text-green-400 border-green-400': category === 'Excel',
      'text-blue-400 border-blue-400': category === 'Word',
      'text-yellow-400 border-yellow-400': category === 'Netzwerk' || category === 'Tools',
    };
  }


}
