export function resolvePublicHttpsUrl(value: string | undefined): string {
  const candidate = value?.trim();
  if (!candidate) {
    return "";
  }

  let parsed: URL;
  try {
    parsed = new URL(candidate);
  } catch {
    return "";
  }

  if (parsed.protocol !== "https:") {
    return "";
  }
  if (isPrivateOrLocalHostname(parsed.hostname)) {
    return "";
  }
  return parsed.toString();
}

function isPrivateOrLocalHostname(hostname: string): boolean {
  const normalized = hostname.trim().toLowerCase().replace(/^\[|\]$/g, "");
  if (!normalized) {
    return true;
  }
  if (
    normalized === "localhost" ||
    normalized.endsWith(".local") ||
    normalized === "::1" ||
    normalized.startsWith("fc") ||
    normalized.startsWith("fd")
  ) {
    return true;
  }

  const ipv4Match = /^(\d{1,3})(?:\.(\d{1,3})){3}$/.exec(normalized);
  if (!ipv4Match) {
    return false;
  }
  const octets = normalized.split(".").map((segment) => Number.parseInt(segment, 10));
  if (octets.some((octet) => !Number.isFinite(octet) || octet < 0 || octet > 255)) {
    return true;
  }
  const [first, second] = octets;
  if (first === 10 || first === 127) {
    return true;
  }
  if (first === 192 && second === 168) {
    return true;
  }
  if (first === 172 && second >= 16 && second <= 31) {
    return true;
  }
  if (first === 169 && second === 254) {
    return true;
  }
  return false;
}