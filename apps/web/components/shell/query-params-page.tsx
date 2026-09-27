"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, type ReactNode } from "react";

/** Reads a record page's IDs from the query string (see lib/routes.ts).
 *  useSearchParams needs a Suspense boundary in a statically exported page. */
export function QueryParamsPage({
  render,
}: {
  render: (params: URLSearchParams) => ReactNode;
}) {
  return (
    <Suspense fallback={<div className="text-sm text-muted-foreground">Loading…</div>}>
      <Inner render={render} />
    </Suspense>
  );
}

function Inner({ render }: { render: (params: URLSearchParams) => ReactNode }) {
  const params = useSearchParams();
  return <>{render(new URLSearchParams(params.toString()))}</>;
}
