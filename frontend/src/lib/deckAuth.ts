export type DeckShareSlice = {
  token: string | null;
  presentationId: string | null;
};

export function deckAccessToken(
  presentationId: string,
  accessToken: string | null,
  share: DeckShareSlice,
): string | null {
  if (share.token && share.presentationId === presentationId) {
    return share.token;
  }
  return accessToken;
}
