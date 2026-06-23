import { ChangeEvent, useState } from "react";
import { Field } from "../../components/ui";
import type { RegistrationProfileDraft } from "../../models/abby";
import { serviceNeeds } from "../appState";
import { t, translateServiceNeed, type SupportedLocale } from "../../lib/localization";
import { ID_DOCUMENT_ACCEPT_ATTR, isAcceptedIdentityDocument, getIdentityDocumentFileDetail } from "../utils/formatHelpers";

export function ProfileInformationForm({
  profile,
  siteLocale,
  setProfile
}: {
  profile: RegistrationProfileDraft;
  siteLocale: SupportedLocale;
  setProfile: (profile: RegistrationProfileDraft) => void;
}) {
  const update = (patch: Partial<RegistrationProfileDraft>) => setProfile({ ...profile, ...patch });
  const [photoFileDetail, setPhotoFileDetail] = useState("");
  const [photoUploadError, setPhotoUploadError] = useState("");

  async function handleProfileUploadChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (!file) {
      update({ photoAssetId: "" });
      setPhotoFileDetail("");
      setPhotoUploadError("");
      return;
    }

    if (!isAcceptedIdentityDocument(file)) {
      update({ photoAssetId: "" });
      setPhotoFileDetail("");
      setPhotoUploadError(t(siteLocale, "profile.badFile"));
      return;
    }

    update({ photoAssetId: file.name });
    setPhotoFileDetail(getIdentityDocumentFileDetail(file));
    setPhotoUploadError("");
  }

  function toggleNeed(need: string) {
    update({
      serviceNeeds: profile.serviceNeeds.includes(need)
        ? profile.serviceNeeds.filter((item) => item !== need)
        : [...profile.serviceNeeds, need]
    });
  }

  return (
    <form className="form-grid" onSubmit={(event) => event.preventDefault()}>
      <Field help={t(siteLocale, "profile.legalNameHelp")} label={t(siteLocale, "profile.legalName")} required>
        <input value={profile.legalName} onChange={(event) => update({ legalName: event.target.value })} />
      </Field>
      <Field help={t(siteLocale, "profile.preferredNameHelp")} label={t(siteLocale, "profile.preferredName")}>
        <input value={profile.preferredName} onChange={(event) => update({ preferredName: event.target.value })} />
      </Field>
      <Field help={t(siteLocale, "profile.pronounsHelp")} label={t(siteLocale, "profile.pronouns")}>
        <input
          placeholder={t(siteLocale, "profile.pronounsPlaceholder")}
          value={profile.pronouns}
          onChange={(event) => update({ pronouns: event.target.value })}
        />
      </Field>
      <Field help={t(siteLocale, "profile.birthDateHelp")} label={t(siteLocale, "profile.birthDate")} required>
        <input
          type="date"
          value={profile.dateOfBirth}
          onChange={(event) => update({ dateOfBirth: event.target.value })}
        />
      </Field>
      <Field
        error={photoUploadError}
        help={t(siteLocale, "profile.photoIdHelp")}
        label={t(siteLocale, "profile.photoId")}
        required
      >
        <input
          accept={ID_DOCUMENT_ACCEPT_ATTR}
          type="file"
          onChange={handleProfileUploadChange}
        />
        {photoFileDetail ? (
          <small className="registration-file-detail" aria-live="polite">
            {t(siteLocale, "profile.selectedFile")}: {photoFileDetail}
          </small>
        ) : null}
      </Field>
      <hr className="form-divider full-span" />
      <Field help={t(siteLocale, "profile.phoneHelp")} label={t(siteLocale, "profile.phone")}>
        <input value={profile.phone} onChange={(event) => update({ phone: event.target.value })} />
      </Field>
      <Field help={t(siteLocale, "profile.emailHelp")} label={t(siteLocale, "profile.email")}>
        <input type="email" value={profile.email} onChange={(event) => update({ email: event.target.value })} />
      </Field>
      <Field help={t(siteLocale, "profile.locationHelp")} label={t(siteLocale, "profile.location")}>
        <input value={profile.currentLocation} onChange={(event) => update({ currentLocation: event.target.value })} />
      </Field>
      <Field help={t(siteLocale, "profile.shelterHelp")} label={t(siteLocale, "profile.shelter")}>
        <input
          value={profile.shelterAffiliation}
          onChange={(event) => update({ shelterAffiliation: event.target.value })}
        />
      </Field>
      <div className="full-span">
        <span className="field-label">{t(siteLocale, "profile.serviceNeeds")}</span>
        <div className="chip-grid">
          {serviceNeeds.map((need) => (
            <button
              aria-pressed={profile.serviceNeeds.includes(need)}
              className="choice-chip"
              key={need}
              onClick={() => toggleNeed(need)}
              type="button"
            >
              {translateServiceNeed(siteLocale, need)}
            </button>
          ))}
        </div>
      </div>
    </form>
  );
}

export function togglePartnerHelpRequest(
  profile: RegistrationProfileDraft,
  setProfile: (profile: RegistrationProfileDraft) => void
) {
  setProfile({
    ...profile,
    servicePartnerHelpRequested: !profile.servicePartnerHelpRequested,
    servicePartnerHelpRequestedAt: profile.servicePartnerHelpRequested ? "" : new Date().toISOString()
  });
}
