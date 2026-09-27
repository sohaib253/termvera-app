/** Product identity. Every user-facing mention of the product name comes
 *  from here, so a rename is one edit. The backend's copy is `app_name` in
 *  apps/api/app/core/config.py; the installer's is apps/desktop. */
export const BRAND = {
  name: "Termvera",
  tagline: "The truth in every term.",
  descriptor: "Tender & contract risk intelligence, private by design.",
  modules: {
    compliance: "Tender Compliance",
    contractRisk: "Contract Risk",
  },
  // Where "Buy" and "Renew" send people. Placeholder until the website and
  // store exist; keep in sync with the vendor licensing tool's emails.
  purchaseUrl: "https://termvera.app/pricing",
  supportEmail: "support@termvera.app",
  trialDays: 14,
} as const;
