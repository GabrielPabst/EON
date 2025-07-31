import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Macro } from '../models/macro.model';

@Injectable({
  providedIn: 'root'
})
export class MacroService {
  private macros: Macro[] = [];

  constructor(private http: HttpClient) {
    this.loadFromJson();
  }

  getAll(): Macro[] {
    return this.macros;
  }

  add(macro: Macro): void {
    this.macros.push(macro);
  }

  delete(id: string): void {
    this.macros = this.macros.filter(m => m.id !== id);
  }

  download(id: string): void {
    const macro = this.macros.find(m => m.id === id);
    if (macro?.file) {
      const url = URL.createObjectURL(macro.file);
      const a = document.createElement('a');
      a.href = url;
      a.download = macro.filename;
      a.click();
      URL.revokeObjectURL(url);
    }
  }

  private loadFromJson(): void {
    this.http.get<Macro[]>('assets/macros.json').subscribe(data => {
      // createdAt ist als String drin – wir konvertieren zu echten Date-Objekten
      this.macros = data.map(m => ({
        ...m,
        createdAt: new Date(m.createdAt),
        file: null // Datei-Objekt bleibt leer, nur filename vorhanden
      }));
    });
  }
}
