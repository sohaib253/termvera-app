"use client";

import { QueryParamsPage } from "@/components/shell/query-params-page";

import { ContractComparisonClient } from "./contract-comparison-client";

export default function ContractComparePage() {
  return <QueryParamsPage render={(p) => <ContractComparisonClient key={p.toString()} contractId={p.get("id") ?? ""} />} />;
}
