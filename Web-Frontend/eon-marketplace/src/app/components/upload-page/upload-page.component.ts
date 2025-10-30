import { Component } from '@angular/core';
import { NgClass } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MacroService } from '../../services/macro.service';
import { unzipSync, strFromU8 } from 'fflate';

@Component({
  selector: 'app-upload-page',
  standalone: true,
  templateUrl: './upload-page.component.html',
  styleUrl: './upload-page.component.css',
  imports: [NgClass, FormsModule]
})
export class UploadPageComponent {
  constructor(private api: MacroService) {}

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
  previewFile: File | null = null;
  previewFileName = '';

  busy = false;
  message = '';
  error = '';

  async onFileSelected(event: Event) {
    this.error = '';
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const isZip = /\.zip$/i.test(file.name) || file.type === 'application/zip';
    if (!isZip) {
      this.error = 'Bitte eine ZIP-Datei auswählen.';
      input.value = '';
      return;
    }

    this.macro.file = file;
    this.macro.filename = file.name;

    try {
      const buf = new Uint8Array(await file.arrayBuffer());
      const entries = unzipSync(buf);

      const metaEntry = entries['meta.json'] || entries['meta/meta.json'] || null;
      if (metaEntry) {
        const json = JSON.parse(strFromU8(metaEntry));
        this.macro.name = json.name ?? this.macro.name ?? '';
        this.macro.description = json.description ?? json.desc ?? this.macro.description ?? '';
        this.macro.category = json.usecase ?? json.category ?? this.macro.category ?? '';
      }

      const previewKey = Object.keys(entries).find(k =>
        /^(preview|thumb|thumbnail)\.(png|jpg|jpeg|webp|mp4|webm)$/i.test(k)
      );
      if (previewKey) {
        const blob = new Blob([entries[previewKey]], { type: this._mime(previewKey) });
        const url = URL.createObjectURL(blob);
        this.thumbnailPreview = url;
        this.isVideoPreview = /mp4|webm$/i.test(previewKey);

        this.previewFile = null;
        this.previewFileName = '';
      } else {
        if (!this.previewFile) {
          this.thumbnailPreview = null;
          this.isVideoPreview = false;
        }
      }
    } catch {
      if (!this.previewFile) {
        this.thumbnailPreview = null;
        this.isVideoPreview = false;
      }
    }

    if (!this.macro.name) {
      this.macro.name = file.name.replace(/\.zip$/i, '').replace(/[_-]+/g, ' ');
    }
  }

  onThumbnailSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const isMedia = file.type.startsWith('image/') || file.type.startsWith('video/');
    if (!isMedia) {
      this.error = 'Nur Bild- oder Videodateien als Vorschau erlaubt.';
      input.value = '';
      return;
    }

    this.previewFile = file;
    this.previewFileName = file.name;

    const url = URL.createObjectURL(file);
    this.thumbnailPreview = url;
    this.isVideoPreview = file.type.startsWith('video/');
  }

  async submit() {
    this.message = '';
    this.error = '';

    if (!this.macro.file) {
      this.error = 'Bitte eine ZIP-Datei auswählen.';
      return;
    }
    if (!this.macro.name.trim()) {
      this.error = 'Bitte einen Makro-Namen angeben.';
      return;
    }

    this.busy = true;
    this.api
      .uploadZip(
        this.macro.file,
        this.macro.name || this.macro.filename.replace(/\.zip$/i, ''),
        this.macro.description || '',
        this.macro.category || '',
        this.previewFile || undefined
      )
      .subscribe({
        next: () => {
          this.message = 'Upload erfolgreich!';
          this.busy = false;
          this.resetForm();
        },
        error: (err) => {
          this.error =
            'Upload fehlgeschlagen: ' +
            (err?.error?.error || err?.error?.message || err.statusText || 'Unbekannt');
          this.busy = false;
        }
      });
  }

  private resetForm() {
    this.macro = {
      name: '',
      description: '',
      category: '',
      filename: '',
      file: null,
      createdAt: new Date()
    };
    this.thumbnailPreview = null;
    this.isVideoPreview = false;
    this.previewFile = null;
    this.previewFileName = '';
  }

  categoryBorder(category: string): string {
    switch ((category || '').toLowerCase()) {
      case 'multimedia': return 'border-purple-500 hover:border-orange-400';
      case 'pdf': return 'border-pink-500 hover:border-orange-400';
      case 'excel': return 'border-green-500 hover:border-orange-400';
      case 'word': return 'border-blue-500 hover:border-orange-400';
      case 'netzwerk': return 'border-yellow-400 hover:border-orange-400';
      case 'tools': return 'border-orange-400 hover:border-orange-500';
      default: return 'border-white/10';
    }
  }

  private _mime(name: string): string {
    if (/\.png$/i.test(name)) return 'image/png';
    if (/\.(jpg|jpeg)$/i.test(name)) return 'image/jpeg';
    if (/\.webp$/i.test(name)) return 'image/webp';
    if (/\.mp4$/i.test(name)) return 'video/mp4';
    if (/\.webm$/i.test(name)) return 'video/webm';
    return 'application/octet-stream';
  }
}
