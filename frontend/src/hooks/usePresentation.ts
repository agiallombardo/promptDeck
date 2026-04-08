import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
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
    enabled: Boolean(presentationId) && Boolean(pres.data?.current_version_id),
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

  const iframeSrc = embed.data ? iframeSrcForDev(embed.data.iframe_src) : "";

  return {
    pres,
    embed,
    upload,
    uploadError,
    iframeSrc,
    qc,
  };
}
