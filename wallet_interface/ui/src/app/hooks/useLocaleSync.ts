import { useEffect } from "react";
import {
  syncDocumentLocale,
  writeAssistantAutoTranslatePreference,
  writeAssistantTranslationLocalePreference,
  writeSiteLocalePreference,
  type SupportedLocale,
} from "../../shared/lib/localization";

export function useLocaleSync(
  siteLocale: SupportedLocale,
  assistantTranslationLocale: string,
  assistantAutoTranslate: boolean
) {
  useEffect(() => {
    syncDocumentLocale(siteLocale);
    writeSiteLocalePreference(siteLocale);
  }, [siteLocale]);

  useEffect(() => {
    writeAssistantTranslationLocalePreference(assistantTranslationLocale);
  }, [assistantTranslationLocale]);

  useEffect(() => {
    writeAssistantAutoTranslatePreference(assistantAutoTranslate);
  }, [assistantAutoTranslate]);
}
