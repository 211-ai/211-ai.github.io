// WORLDCOIN-G037 PREPARATION ARTIFACT: NOT APPROVED, NOT EXECUTED.
// G006 owns nonce/session durability and constructs the trusted server-side
// client; never pass a client from request data. This adapter makes every
// policy field and the EIP-1271 client explicit so the official helper can
// never create its default public-RPC transport.
import {
  parseSiweMessage,
  verifySiweMessage,
} from "@worldcoin/minikit-js/siwe";

const exactKeys = (value, expected, context) => {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError(`${context} must be an object`);
  }
  const observed = Object.keys(value).sort();
  const wanted = [...expected].sort();
  if (
    observed.length !== wanted.length ||
    observed.some((key, index) => key !== wanted[index])
  ) {
    throw new TypeError(`${context} has unexpected or missing fields`);
  }
};

const requiredString = (value, context) => {
  if (typeof value !== "string" || value.length === 0) {
    throw new TypeError(`${context} must be a non-empty string`);
  }
  return value;
};

const requiredTime = (value, context) => {
  const text = requiredString(value, context);
  const milliseconds = Date.parse(text);
  if (!text.endsWith("Z") || !Number.isFinite(milliseconds)) {
    throw new TypeError(`${context} must be a valid UTC timestamp`);
  }
  return milliseconds;
};

const requiredPositiveInteger = (value, context) => {
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new TypeError(`${context} must be a positive safe integer`);
  }
  return value;
};

export async function verifyWorldSiwe(envelope, policy, runtime) {
  exactKeys(envelope, ["address", "message", "signature"], "SIWE envelope");
  exactKeys(
    policy,
    [
      "chainId",
      "domain",
      "expirationTime",
      "issuedAt",
      "maxAgeSeconds",
      "nonce",
      "notBefore",
      "requestId",
      "statement",
      "uri",
      "version",
    ],
    "SIWE policy",
  );
  exactKeys(runtime, ["client", "now"], "SIWE runtime");
  const { client, now } = runtime;
  if (!client || typeof client !== "object") {
    throw new TypeError("an injected World Chain client is required");
  }

  const message = requiredString(envelope.message, "message");
  const signature = requiredString(envelope.signature, "signature");
  const address = requiredString(envelope.address, "address");
  if (!/^0x[0-9a-fA-F]{40}$/.test(address)) {
    throw new TypeError("address must be a 20-byte hexadecimal Ethereum address");
  }
  const parsed = parseSiweMessage(message);
  const chainId = requiredPositiveInteger(policy.chainId, "policy.chainId");
  const maxAgeSeconds = requiredPositiveInteger(
    policy.maxAgeSeconds,
    "policy.maxAgeSeconds",
  );
  if (maxAgeSeconds > 900) {
    throw new TypeError("policy.maxAgeSeconds cannot exceed 900");
  }
  if (
    !client.chain ||
    client.chain.id !== chainId ||
    typeof client.readContract !== "function"
  ) {
    throw new TypeError(
      "the trusted injected client must expose readContract for the policy chain",
    );
  }
  const expected = {
    domain: requiredString(policy.domain, "policy.domain"),
    uri: requiredString(policy.uri, "policy.uri"),
    version: requiredString(policy.version, "policy.version"),
    chain_id: String(chainId),
    nonce: requiredString(policy.nonce, "policy.nonce"),
    statement: requiredString(policy.statement, "policy.statement"),
    request_id: requiredString(policy.requestId, "policy.requestId"),
    issued_at: requiredString(policy.issuedAt, "policy.issuedAt"),
    expiration_time: requiredString(
      policy.expirationTime,
      "policy.expirationTime",
    ),
    not_before: requiredString(policy.notBefore, "policy.notBefore"),
  };
  if (expected.version !== "1") {
    throw new TypeError("policy.version must be exactly 1");
  }
  for (const [field, wanted] of Object.entries(expected)) {
    if (parsed[field] !== wanted) {
      throw new Error(`SIWE ${field} does not match server policy`);
    }
  }
  if (!parsed.address || parsed.address.toLowerCase() !== address.toLowerCase()) {
    throw new Error("SIWE address does not match the signed envelope");
  }
  const nowMilliseconds = requiredTime(now, "runtime.now");
  const issuedMilliseconds = requiredTime(expected.issued_at, "policy.issuedAt");
  const expirationMilliseconds = requiredTime(
    expected.expiration_time,
    "policy.expirationTime",
  );
  const notBeforeMilliseconds = requiredTime(
    expected.not_before,
    "policy.notBefore",
  );
  if (
    issuedMilliseconds > notBeforeMilliseconds ||
    notBeforeMilliseconds > nowMilliseconds ||
    nowMilliseconds >= expirationMilliseconds ||
    nowMilliseconds - issuedMilliseconds > maxAgeSeconds * 1000 ||
    expirationMilliseconds - issuedMilliseconds > maxAgeSeconds * 1000
  ) {
    throw new Error("SIWE temporal policy is stale, premature, or expired");
  }

  return verifySiweMessage(
    { address, message, signature },
    expected.nonce,
    expected.statement,
    expected.request_id,
    client,
  );
}
