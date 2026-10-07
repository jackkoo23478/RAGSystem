// the pill shape shared by the document and the question status badges
export const BADGE_BASE = "inline-block rounded-full px-[0.6rem] py-[0.1rem] text-[0.8rem] font-medium whitespace-nowrap"

export const BADGE_TONES = {
  neutral: "bg-surface-2 text-muted",
  accent: "bg-accent-soft text-accent",
  success: "bg-success-soft text-success",
  danger: "bg-danger-soft text-danger",
  warning: "bg-warning-soft text-warning",
} as const
