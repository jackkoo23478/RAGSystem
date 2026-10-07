import { clsx } from "clsx"
import type { ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

// Joins class names and resolves conflicts: when two classes set the same property
// (for example "px-4" and "px-2"), the later one wins. Plain string joining cannot do this,
// because in the generated CSS the order of the rules decides, not the order in the class attribute.
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
