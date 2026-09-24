import { ContractComparisonClient } from "./contract-comparison-client";

export default async function ContractComparePage(props: PageProps<"/contracts/[id]/compare">) {
  const { id } = await props.params;
  return <ContractComparisonClient contractId={id} />;
}
