"use client";

import { QueryParamsPage } from "@/components/shell/query-params-page";

import { RiskFindingDetailClient } from "./risk-finding-detail-client";

export default function RiskFindingPage() {
  return <QueryParamsPage render={(p) => <RiskFindingDetailClient key={p.toString()} findingId={p.get("id") ?? ""} />} />;
}
