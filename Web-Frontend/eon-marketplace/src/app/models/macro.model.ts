export interface Macro {
  id: string;
  name: string;
  description: string;
  category: string;
  filename: string;
  file: File | null;
  createdAt: Date;
}
