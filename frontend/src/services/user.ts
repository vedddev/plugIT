import type { User } from "./auth";

type UserLike = Partial<User> & { full_name?: string | null; username?: string | null };

export function getUserDisplayName(user: UserLike | null | undefined): string {
  if (!user) return "User";
  const value = user.name || user.full_name || user.username || user.email?.split("@", 1)[0];
  return value?.trim() || "User";
}

export function getUserInitials(user: UserLike | null | undefined): string {
  const displayName = getUserDisplayName(user);
  if (displayName === "User") return "U";
  const words = displayName.trim().split(/[\s._-]+/).map((word) => word.replace(/[^\p{L}\p{N}]/gu, "")).filter(Boolean);
  if (words.length > 1) return `${words[0][0]}${words[1][0]}`.toUpperCase();
  return (words[0]?.[0] || displayName[0] || "U").toUpperCase();
}
