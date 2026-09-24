import { ComplianceMatrixClient } from "./compliance-matrix-client";

export default async function CompliancePage(props: PageProps<"/projects/[id]/compliance">) {
  const { id } = await props.params;
  return <ComplianceMatrixClient projectId={id} />;
}
