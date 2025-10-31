import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';
import { Macro } from '../models/macro.model';

interface AccountDto {
  id: number;
  name: string;
  created_at: string;
}

interface MakroDto {
  id: number;
  name: string;
  desc?: string;
  usecase?: string;
  author_id: number;
  author_name: string;
  created_at: string;
  updated_at: string;
  preview_url?: string | null;
}

interface PaginatedDto<T> {
  makros: T[];
  total: number;
  pages: number;
  current_page: number;
}

const baseUrl = 'http://localhost:5000';
const withCreds = { withCredentials: true as const };

@Injectable({ providedIn: 'root' })
export class MacroService {
  private macros$ = new BehaviorSubject<Macro[]>([]);

  private account$ = new BehaviorSubject<AccountDto | null>(null);
  isLoggedIn$ = this.account$.pipe(map(a => !!a));

  constructor(private http: HttpClient) {
    this.fetchMarketplace()
      .pipe(catchError((_err) => this.loadFromJson()))
      .subscribe();

    this.getAccount()
      .pipe(catchError((_err) => of(null)))
      .subscribe(r => this.account$.next(r?.account ?? null));
  }

  stream(): Observable<Macro[]> {
    return this.macros$.asObservable();
  }

  getAll(): Macro[] {
    return this.macros$.value;
  }

  // ---------- Accounts ----------
  register(name: string, password: string) {
    return this.http.post<{ message: string; account: AccountDto }>(
      `${baseUrl}/api/accounts/register`,
      { name, password },
      withCreds
    ).pipe(tap(res => this.account$.next(res.account)));
  }

  login(name: string, password: string) {
    return this.http.post<{ message: string; account: AccountDto }>(
      `${baseUrl}/api/accounts/login`,
      { name, password },
      withCreds
    ).pipe(tap(res => this.account$.next(res.account)));
  }

  logout() {
    return this.http.post<{ message: string }>(
      `${baseUrl}/api/accounts/logout`,
      {},
      withCreds
    ).pipe(tap(() => this.account$.next(null)));
  }

  getAccount() {
    return this.http.get<{ account: AccountDto }>(
      `${baseUrl}/api/accounts/data`,
      withCreds
    );
  }

  updateAccount(patch: { name?: string; password?: string }) {
    return this.http.put<{ message: string; account: AccountDto }>(
      `${baseUrl}/api/accounts/data`,
      patch,
      withCreds
    ).pipe(tap(res => this.account$.next(res.account)));
  }

  // ---------- Marketplace ----------
  fetchMarketplace(page = 1, perPage = 20) {
    const params = new HttpParams()
      .set('page', String(page))
      .set('per_page', String(perPage));
    return this.http.get<PaginatedDto<MakroDto>>(
      `${baseUrl}/api/marketplace`,
      { params, ...withCreds }
    ).pipe(
      map(res => res.makros.map(this.mapDtoToMacro)),
      tap(list => this.macros$.next(list))
    );
  }

  fetchRandom(count = 10) {
    const params = new HttpParams().set('count', String(count));
    return this.http.get<{ makros: MakroDto[] }>(
      `${baseUrl}/api/marketplace/random`,
      { params, ...withCreds }
    ).pipe(
      map(res => res.makros.map(this.mapDtoToMacro)),
      tap(list => this.macros$.next(list))
    );
  }

  search(q: string, usecase?: string, author?: string, page = 1, perPage = 20) {
    let params = new HttpParams()
      .set('q', q)
      .set('page', String(page))
      .set('per_page', String(perPage));
    if (usecase) params = params.set('usecase', usecase);
    if (author) params = params.set('author', author);

    return this.http.get<PaginatedDto<MakroDto>>(
      `${baseUrl}/api/marketplace/search`,
      { params, ...withCreds }
    ).pipe(
      map(res => res.makros.map(this.mapDtoToMacro)),
      tap(list => this.macros$.next(list))
    );
  }

  getMyMakros(page = 1, perPage = 20) {
    const params = new HttpParams()
      .set('page', String(page))
      .set('per_page', String(perPage));
    return this.http.get<PaginatedDto<MakroDto>>(
      `${baseUrl}/api/my-makros`,
      { params, ...withCreds }
    ).pipe(
      map(res => res.makros.map(this.mapDtoToMacro)),
      tap(list => this.macros$.next(list))
    );
  }

  // ---------- CRUD ----------
  getById(id: string) {
    return this.http.get<{ makro: MakroDto }>(
      `${baseUrl}/api/makros/${id}`,
      withCreds
    ).pipe(map(res => this.mapDtoToMacro(res.makro)));
  }

  uploadZip(file: File, name: string, description = '', category = '', preview?: File) {
    const form = new FormData();
    form.append('file', file);
    form.append('name', name);
    form.append('desc', description);
    form.append('usecase', category);
    if (preview) form.append('preview', preview, preview.name);

    return this.http.post<{ message: string; makro: MakroDto }>(
      `${baseUrl}/api/makros`,
      form,
      withCreds
    ).pipe(
      map(res => this.mapDtoToMacro(res.makro)),
      tap(m => this.macros$.next([m, ...this.macros$.value]))
    );
  }

  update(id: string, patch: { name?: string; description?: string; category?: string }) {
    const body: any = {};
    if (patch.name !== undefined) body.name = patch.name;
    if (patch.description !== undefined) body.desc = patch.description;
    if (patch.category !== undefined) body.usecase = patch.category;

    return this.http.put<{ message: string; makro: MakroDto }>(
      `${baseUrl}/api/makros/${id}`,
      body,
      withCreds
    ).pipe(
      map(res => this.mapDtoToMacro(res.makro)),
      tap(updated => {
        this.macros$.next(this.macros$.value.map(m => m.id === updated.id ? updated : m));
      })
    );
  }

  delete(id: string) {
    return this.http.delete<{ message: string }>(
      `${baseUrl}/api/makros/${id}`,
      withCreds
    ).pipe(
      tap(() => this.macros$.next(this.macros$.value.filter(m => m.id !== id)))
    );
  }

  download(id: string) {
    return this.http.get(
      `${baseUrl}/api/makros/${id}/download`,
      { responseType: 'blob', ...withCreds }
    ).pipe(
      tap(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `macro_${id}.zip`;
        a.click();
        URL.revokeObjectURL(url);
      })
    );
  }

  add(macro: Macro): void {
    this.macros$.next([macro, ...this.macros$.value]);
  }

  // ---------- Helpers ----------
  private loadFromJson(): Observable<Macro[]> {
    return this.http.get<any[]>('assets/macros.json').pipe(
      map(arr => (arr ?? []).map((m: any): Macro => ({
        id: String(m.id ?? ''),
        name: m.name ?? '',
        description: m.description ?? '',
        category: m.category ?? '',
        filename: m.filename ?? '',
        file: null,
        createdAt: new Date(m.createdAt ?? Date.now()),
        // Falls im JSON eine relative URL steht, ebenfalls auf baseUrl mappen
        previewUrl: m.previewUrl ? (
          m.previewUrl.startsWith('http') ? m.previewUrl : `${baseUrl}${m.previewUrl}`
        ) : null
      })) as Macro[]),
      tap(list => this.macros$.next(list)),
      catchError(() => {
        this.macros$.next([]);
        return of([] as Macro[]);
      })
    );
  }

  private mapDtoToMacro = (dto: MakroDto): Macro => ({
    id: String(dto.id),
    name: dto.name,
    description: dto.desc ?? '',
    category: dto.usecase ?? '',
    filename: '',
    file: null,
    createdAt: new Date(dto.created_at),
    // <-- Hier absolut machen:
    previewUrl: dto.preview_url ? `${baseUrl}${dto.preview_url}` : null
  });
}
