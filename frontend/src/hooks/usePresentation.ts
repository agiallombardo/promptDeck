import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  apiPresentationDiagramGet,
  apiPresentationDiagramSave,
  apiPresentationEmbed,
  apiPresentationGet,
  apiVersionUpload,
  iframeSrcForDev,
} from "../lib/api";

export function usePresentation(presentationId: string | undefined, token: string | null) {
  const qc = useQueryClient();
  const [uploadError, setUploadError] = useState<string | null>(null);

  const pres = useQuery({
    queryKey: ["presentation", presentationId, token],
    queryFn: () => apiPresentationGet(token!, presentationId!),
    enabled: Boolean(presentationId) && Boolean(token),
  });

  const embed = useQuery({
    queryKey: ["presentation-embed", presentationId, token, pres.data?.current_version_id],
    queryFn: () => apiPresentationEmbed(token!, presentationId!),
    enabled:
      Boolean(presentationId) &&
      pres.data?.kind === "deck" &&
      Boolean(pres.data?.current_version_id),
  });

  const diagram = useQuery({
    queryKey: ["presentation-diagram", presentationId, token, pres.data?.current_version_id],
    queryFn: () =>
      apiPresentationDiagramGet(token!, presentationId!, pres.data?.current_version_id),
    enabled:
      Boolean(presentationId) &&
      pres.data?.kind === "diagram" &&
      Boolean(pres.data?.current_version_id),
  });

  const upload = useMutation({
    mutationFn: (file: File) => apiVersionUpload(token!, presentationId!, file),
    onSuccess: async () => {
      setUploadError(null);
      await qc.invalidateQueries({ queryKey: ["presentation", presentationId, token] });
      await qc.invalidateQueries({ queryKey: ["presentation-embed", presentationId, token] });
    },
    onError: (err: Error) => setUploadError(err.message),
  });

  const saveDiagram = useMutation({
    mutationFn: (document: Record<string, unknown>) =>
      apiPresentationDiagramSave(token!, presentationId!, document),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["presentation", presentationId, token] });
      await qc.invalidateQueries({ queryKey: ["presentation-diagram", presentationId, token] });
    },
  });

  const iframeSrc = embed.data ? iframeSrcForDev(embed.data.iframe_src) : "";

  return {
    pres,
    embed,
    diagram,
    upload,
    saveDiagram,
    uploadError,
    iframeSrc,
    qc,
  };
}
