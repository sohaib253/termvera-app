"use client";

import { QueryParamsPage } from "@/components/shell/query-params-page";

import { ProjectDetailClient } from "./project-detail-client";

export default function ProjectDetailPage() {
  return <QueryParamsPage render={(p) => <ProjectDetailClient key={p.toString()} projectId={p.get("id") ?? ""} />} />;
}
