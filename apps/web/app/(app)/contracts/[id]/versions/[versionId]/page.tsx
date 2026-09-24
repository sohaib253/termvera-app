import { VersionDetailClient } from "./version-detail-client";

export default async function VersionDetailPage(
  props: PageProps<"/contracts/[id]/versions/[versionId]">
) {
  const { id, versionId } = await props.params;
  return <VersionDetailClient contractId={id} versionId={versionId} />;
}
