"use client";

import { QueryParamsPage } from "@/components/shell/query-params-page";

import { ContractDetailClient } from "./contract-detail-client";

export default function ContractDetailPage() {
  return <QueryParamsPage render={(p) => <ContractDetailClient key={p.toString()} contractId={p.get("id") ?? ""} />} />;
}
