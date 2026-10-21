import type { APIRoute, GetStaticPaths } from "astro";
import { json } from "../../../../lib/api-data";
import { sourceNpcs as npcs } from "../../../../lib/data";

// Um NPC (localizações e o que vende).
export const getStaticPaths: GetStaticPaths = () => npcs.map((npc) => ({ params: { id: npc.id }, props: { npc } }));

export const GET: APIRoute = ({ props }) => json(props.npc);
