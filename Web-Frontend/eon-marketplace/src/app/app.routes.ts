import { Routes } from '@angular/router';
import {HomePageComponent} from './components/home-page/home-page.component';
import {MacroListComponent} from './components/macro-list/macro-list.component';
import {MacroDetailsComponent} from './components/macro-details/macro-details.component';

export const routes: Routes = [
  {path: '', redirectTo: 'home', pathMatch: 'full'},
  {path: 'home', pathMatch: 'full', component: HomePageComponent},
  {path: 'macros', pathMatch: "full", component: MacroListComponent},
  { path: 'macro/:id', component: MacroDetailsComponent },
];
