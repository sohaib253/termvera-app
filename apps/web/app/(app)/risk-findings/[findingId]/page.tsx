import { RiskFindingDetailClient } from "./risk-finding-detail-client";

export default async function RiskFindingPage(props: PageProps<"/risk-findings/[findingId]">) {
  const { findingId } = await props.params;
  return <RiskFindingDetailClient findingId={findingId} />;
}
