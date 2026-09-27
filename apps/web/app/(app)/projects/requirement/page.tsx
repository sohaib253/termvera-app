"use client";

import { QueryParamsPage } from "@/components/shell/query-params-page";

import { RequirementDetailClient } from "./requirement-detail-client";

export default function RequirementPage() {
  return <QueryParamsPage render={(p) => <RequirementDetailClient key={p.toString()} projectId={p.get("id") ?? ""} requirementId={p.get("requirementId") ?? ""} />} />;
}
