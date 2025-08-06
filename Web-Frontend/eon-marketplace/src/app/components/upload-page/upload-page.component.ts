import { Component } from '@angular/core';
import { NgClass } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-upload-page',
  standalone: true,
  templateUrl: './upload-page.component.html',
  styleUrl: './upload-page.component.css',
  imports: [NgClass, FormsModule]
})
export class UploadPageComponent {
  categories = ['Multimedia', 'PDF', 'Excel', 'Word', 'Netzwerk', 'Tools'];

  macro = {
    name: '',
    description: '',
    category: '',
    filename: '',
    file: null as File | null,
    createdAt: new Date()
  };

  thumbnailPreview: string | null = null;
  isVideoPreview = false;

  // Event: Datei für das Makro (z.B. .py)
  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      this.macro.file = file;
      this.macro.filename = file.name;
    }
  }

  // Event: Thumbnail Datei (Bild oder Video)
  onThumbnailSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      this.thumbnailPreview = url;
      this.isVideoPreview = file.type.startsWith('video/');
    }
  }

  // Dynamische Border-Class nach Kategorie
  categoryBorder(category: string): string {
    switch (category.toLowerCase()) {
      case 'multimedia':
        return 'border-purple-500 hover:border-orange-400';
      case 'pdf':
        return 'border-pink-500 hover:border-orange-400';
      case 'excel':
        return 'border-green-500 hover:border-orange-400';
      case 'word':
        return 'border-blue-500 hover:border-orange-400';
      case 'netzwerk':
        return 'border-yellow-400 hover:border-orange-400';
      case 'tools':
        return 'border-orange-400 hover:border-orange-500';
      default:
        return 'border-white/10';
    }
  }
}
