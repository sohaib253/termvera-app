"use client";

import { QueryParamsPage } from "@/components/shell/query-params-page";

import { ComplianceMatrixClient } from "./compliance-matrix-client";

export default function CompliancePage() {
  return <QueryParamsPage render={(p) => <ComplianceMatrixClient key={p.toString()} projectId={p.get("id") ?? ""} />} />;
}
