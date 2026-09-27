"use client";

import { QueryParamsPage } from "@/components/shell/query-params-page";

import { VersionDetailClient } from "./version-detail-client";

export default function VersionDetailPage() {
  return <QueryParamsPage render={(p) => <VersionDetailClient key={p.toString()} contractId={p.get("id") ?? ""} versionId={p.get("versionId") ?? ""} />} />;
}
