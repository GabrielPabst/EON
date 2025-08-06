import { Routes } from '@angular/router';
import {HomePageComponent} from './components/home-page/home-page.component';
import {MacroListComponent} from './components/macro-list/macro-list.component';
import {MacroDetailsComponent} from './components/macro-details/macro-details.component';
import {UploadPageComponent} from './components/upload-page/upload-page.component';
import {DesktopAppDownloadComponent} from './components/desktop-app-download/desktop-app-download.component';

export const routes: Routes = [
  {path: '', redirectTo: 'home', pathMatch: 'full'},
  {path: 'home', pathMatch: 'full', component: HomePageComponent},
  {path: 'macros', pathMatch: "full", component: MacroListComponent},
  { path: 'macro/:id', component: MacroDetailsComponent },
  {path: 'upload', pathMatch: "full", component: UploadPageComponent},
  {path: 'downloadApp', pathMatch: "full", component: DesktopAppDownloadComponent}
];
