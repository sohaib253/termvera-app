/** Every link to a record page is built here.
 *
 *  Record IDs travel in the query string (/contracts/view?id=…) rather
 *  than the path (/contracts/…/): the web app is exported as static files
 *  so the desktop build can serve it from the local API with no Node.js
 *  server, and a static export can only contain paths known at build time. */

const withQuery = (path: string, params: Record<string, string>) =>
  `${path}?${new URLSearchParams(params).toString()}`;

export const routes = {
  project: (id: string) => withQuery("/projects/view", { id }),
  projectCompliance: (id: string) => withQuery("/projects/compliance", { id }),
  requirement: (projectId: string, requirementId: string) =>
    withQuery("/projects/requirement", { id: projectId, requirementId }),
  contract: (id: string) => withQuery("/contracts/view", { id }),
  contractCompare: (id: string) => withQuery("/contracts/compare", { id }),
  contractVersion: (contractId: string, versionId: string) =>
    withQuery("/contracts/version", { id: contractId, versionId }),
  riskFinding: (id: string) => withQuery("/risk-findings/view", { id }),
};
