import { RequirementDetailClient } from "./requirement-detail-client";

export default async function RequirementPage(
  props: PageProps<"/projects/[id]/compliance/[requirementId]">
) {
  const { id, requirementId } = await props.params;
  return <RequirementDetailClient projectId={id} requirementId={requirementId} />;
}
