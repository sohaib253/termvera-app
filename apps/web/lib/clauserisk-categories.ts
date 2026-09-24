// Mirrors apps/api/app/services/clauserisk/risk_categories.py's CATEGORIES
// keys — used only to populate the Risk Register's category filter, not
// for any validation (the backend is the source of truth for what a
// clause/finding's category is allowed to be).
export const RISK_CATEGORIES = [
  "commercial",
  "schedule",
  "liability",
  "performance",
  "termination",
  "insurance",
  "compliance",
  "contractual",
  "operational",
] as const;
