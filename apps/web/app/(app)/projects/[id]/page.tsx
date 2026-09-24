import { ProjectDetailClient } from "./project-detail-client";

export default async function ProjectDetailPage(props: PageProps<"/projects/[id]">) {
  const { id } = await props.params;
  return <ProjectDetailClient projectId={id} />;
}
