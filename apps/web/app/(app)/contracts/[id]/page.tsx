import { ContractDetailClient } from "./contract-detail-client";

export default async function ContractDetailPage(props: PageProps<"/contracts/[id]">) {
  const { id } = await props.params;
  return <ContractDetailClient contractId={id} />;
}
