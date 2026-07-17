import { FormEvent, useEffect, useState } from "react";
import { Home, KeyRound, MessageSquare, UsersRound } from "lucide-react";
import { Button, Field, StatusBanner } from "../../../components/ui";
import { t, type SupportedLocale } from "../../../shared/lib/localization";
import {
  MAGIC_LOGIN_PARAM,
  MAGIC_LOGIN_TTL_MS,
  createMagicLoginDigest,
  decodeMagicLoginPayload,
  encodeMagicLoginPayload,
  isValidLoginContact,
  normalizeLoginContact,
  randomBase64Url,
  randomOneTimePad,
  requestServerMagicLogin,
  shouldAllowLocalMagicLoginFallback,
  verifyServerMagicLogin,
  type LoginAuthResult,
  type LoginChallenge,
  type LoginPortal
} from "../../../app/utils/authHelpers";

export function LoginScreen({
  onAuthenticated,
  onOpenAssistant,
  siteLocale
}: {
  onAuthenticated: (result: LoginAuthResult) => void;
  onOpenAssistant: () => void;
  siteLocale: SupportedLocale;
}) {
  const [portal, setPortal] = useState<LoginPortal>("client");
  const [contact, setContact] = useState("");
  const [challenge, setChallenge] = useState<LoginChallenge | null>(null);
  const [oneTimePadEntry, setOneTimePadEntry] = useState("");
  const [loginMessage, setLoginMessage] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginSmsWarning, setLoginSmsWarning] = useState("");
  const [pending, setPending] = useState(false);
  const canRequestChallenge = isValidLoginContact(contact);

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get(MAGIC_LOGIN_PARAM);
    if (!token) return;
    void verifyMagicLinkToken(token);
  }, []);

  function updatePortal(nextPortal: LoginPortal) {
    setPortal(nextPortal);
    setChallenge(null);
    setOneTimePadEntry("");
    setLoginError("");
    setLoginSmsWarning("");
    setLoginMessage("");
  }

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canRequestChallenge) {
      setLoginError(t(siteLocale, "login.invalidContact"));
      return;
    }
    setPending(true);
    setLoginError("");
    setLoginSmsWarning("");
    setLoginMessage("");
    try {
      const normalizedContact = normalizeLoginContact(contact);
      try {
        const response = await requestServerMagicLogin({ contact: normalizedContact, portal });
        setChallenge(null);
        setOneTimePadEntry("");
        setLoginMessage(
          response.channel === "email"
            ? t(siteLocale, "login.emailSent")
            : t(siteLocale, "login.textSent")
        );
        return;
      } catch (error) {
        if (!shouldAllowLocalMagicLoginFallback()) {
          setLoginError(error instanceof Error ? error.message : t(siteLocale, "login.magicLinkFailed"));
          return;
        }
        setLoginSmsWarning(t(siteLocale, "login.localFallbackWarning"));
      }
      const issuedAt = Date.now();
      const expiresAt = issuedAt + MAGIC_LOGIN_TTL_MS;
      const oneTimePad = randomOneTimePad();
      const basePayload = {
        portal,
        contact: normalizedContact,
        issuedAt,
        expiresAt,
        salt: `${oneTimePad}.${randomBase64Url(18)}`
      };
      const digest = await createMagicLoginDigest(basePayload);
      const payload = { ...basePayload, digest };
      const magicUrl = new URL(window.location.href);
      magicUrl.search = "";
      magicUrl.hash = "#/";
      magicUrl.searchParams.set(MAGIC_LOGIN_PARAM, encodeMagicLoginPayload(payload));
      const magicLink = magicUrl.toString();
      setChallenge({ ...payload, oneTimePad, magicLink });
      setOneTimePadEntry("");
      setLoginMessage(t(siteLocale, "login.localReady"));
    } finally {
      setPending(false);
    }
  }

  async function verifyOneTimePad() {
    if (!challenge) return;
    if (Date.now() > challenge.expiresAt) {
      setLoginError(t(siteLocale, "login.codeExpired"));
      return;
    }
    if (oneTimePadEntry.trim() !== challenge.oneTimePad) {
      setLoginError(t(siteLocale, "login.codeMismatch"));
      return;
    }
    const digest = await createMagicLoginDigest({
      contact: challenge.contact,
      expiresAt: challenge.expiresAt,
      issuedAt: challenge.issuedAt,
      portal: challenge.portal,
      salt: challenge.salt
    });
    if (digest !== challenge.digest) {
      setLoginError(t(siteLocale, "login.codeVerifyFailed"));
      return;
    }
    completeLogin({ contact: challenge.contact, portal: challenge.portal });
  }

  async function verifyMagicLinkToken(token: string) {
    try {
      const result = await verifyServerMagicLogin(token);
      window.history.replaceState({}, "", `${window.location.pathname}${window.location.hash || "#/"}`);
      completeLogin(result);
      return;
    } catch (error) {
      if (!shouldAllowLocalMagicLoginFallback()) {
        setLoginError(error instanceof Error ? error.message : "The magic link could not be verified.");
        return;
      }
    }
    const payload = decodeMagicLoginPayload(token);
    if (!payload) {
      setLoginError(t(siteLocale, "login.magicInvalid"));
      return;
    }
    if (Date.now() > payload.expiresAt) {
      setLoginError(t(siteLocale, "login.magicExpired"));
      return;
    }
    const digest = await createMagicLoginDigest(payload);
    if (digest !== payload.digest) {
      setLoginError(t(siteLocale, "login.magicVerifyFailed"));
      return;
    }
    window.history.replaceState({}, "", `${window.location.pathname}${window.location.hash || "#/"}`);
    completeLogin({ contact: payload.contact, portal: payload.portal });
  }

  function completeLogin(result: LoginAuthResult) {
    onAuthenticated(result);
  }

  return (
    <main className="login-page">
      <form className="login-panel" onSubmit={submitLogin}>
        <div className="login-brand">
          <img alt="Abby logo" className="login-logo" src="/assets/abby-logo.png" />
          <h1 className="sr-only">{t(siteLocale, "login.signIn")}</h1>
        </div>
        <div className="login-portal-actions" aria-label={t(siteLocale, "login.choosePortal")} role="group">
          <button
            aria-pressed={portal === "client"}
            className="login-portal-option"
            onClick={() => updatePortal("client")}
            type="button"
          >
            <Home aria-hidden="true" size={20} />
            <span>{t(siteLocale, "login.client")}</span>
          </button>
          <button
            aria-pressed={portal === "provider"}
            className="login-portal-option"
            onClick={() => updatePortal("provider")}
            type="button"
          >
            <UsersRound aria-hidden="true" size={20} />
            <span>{t(siteLocale, "login.provider")}</span>
          </button>
        </div>
        <Field label={t(siteLocale, "login.contactLabel")} required>
          <input
            autoComplete="username"
            inputMode="email"
            placeholder={t(siteLocale, "login.contactPlaceholder")}
            value={contact}
            onChange={(event) => {
              setContact(event.target.value);
              setChallenge(null);
              setOneTimePadEntry("");
              setLoginError("");
              setLoginSmsWarning("");
              setLoginMessage("");
            }}
          />
        </Field>
        <Button disabled={!canRequestChallenge || pending} loading={pending} loadingLabel={t(siteLocale, "login.prepareAccess")} type="submit">
          <KeyRound aria-hidden="true" size={18} /> {t(siteLocale, "login.sendLink")}
        </Button>
        {loginError ? <StatusBanner tone="danger">{loginError}</StatusBanner> : null}
        {loginSmsWarning ? <StatusBanner tone="warning">{loginSmsWarning}</StatusBanner> : null}
        {loginMessage ? <StatusBanner tone="success">{loginMessage}</StatusBanner> : null}
        {challenge ? (
          <div className="login-challenge-panel">
            <div className="login-code-display">
              <small>{t(siteLocale, "login.demoPad")}</small>
              <code aria-label="Generated one-time pad code">{challenge.oneTimePad}</code>
            </div>
            <Field label={t(siteLocale, "login.codeLabel")} required>
              <input
                autoComplete="one-time-code"
                inputMode="numeric"
                maxLength={6}
                value={oneTimePadEntry}
                onChange={(event) => {
                  setOneTimePadEntry(event.target.value.replace(/\D/g, "").slice(0, 6));
                  setLoginError("");
                }}
              />
            </Field>
            <div className="login-challenge-actions">
              <Button disabled={oneTimePadEntry.length !== 6} onClick={verifyOneTimePad} type="button">
                {t(siteLocale, "login.verifyCode")}
              </Button>
              <a className="button button-secondary" href={challenge.magicLink}>
                {t(siteLocale, "login.openMagicLink")}
              </a>
            </div>
            <p className="login-proof-note">
              {t(siteLocale, "login.localDevNote")}
            </p>
          </div>
        ) : null}
        <Button onClick={onOpenAssistant} type="button" variant="secondary">
          <MessageSquare aria-hidden="true" size={18} /> {t(siteLocale, "login.openAssistant")}
        </Button>
      </form>
    </main>
  );
}
