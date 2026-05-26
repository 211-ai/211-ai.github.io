# Slot-Friendly Voice Response Review

Generated: 2026-05-26T17:14:58.368574+00:00

## Dedupe Summary

- uniqueFullResponses: 13660
- fullResponseSourceRefs: 13660
- uniqueSentenceChunks: 46252
- sentenceChunkSourceRefs: 66131
- reusableSentenceChunks: 3577
- uniqueMaskedTemplates: 43556
- reusableMaskedTemplates: 392
- estimatedChunkReuseRatio: 0.3006
- estimatedMaskedTemplateReuseRatio: 0.0583

## Rewrite Opportunity Summary

- opportunityCount: 62
- reportedOpportunityCount: 62
- estimatedSavedChunkCallsTop: 5600
- estimatedSavedChunkCallsAll: 5600
- familyKindCounts: {'211_phrase': 1, 'emergency_phrase': 1, 'location': 19, 'named_entity': 22, 'phone_or_number': 13, 'static_phrase': 6}
- note: Savings are static-analysis estimates. Slot audio still needs prosody validation before runtime composition.

## Highest-Value Rewrites

| Rank | Canonical frame | Kind | Saved calls | Unique chunks | Source templates | Examples |
|---:|---|---|---:|---:|---:|---|
| 1 | `Call {phone_1}.` | phone_or_number | 1257 | 1261 | 957 | You can call five-four-one, two-two-one, zero-eight-two-four. / You can call 5 0 3, 8 4 6, 3 0 9 4. |
| 2 | `The number is {phone_1}.` | phone_or_number | 1059 | 1063 | 717 | The number is five four one, two two one, zero eight two four. / The number is 5 0 3, 3 5 2, 6 0 0 0. |
| 3 | `The number is {number_1}, {number_2}, {number_3}.` | phone_or_number | 747 | 755 | 441 | The number is 503, 581, 5265. / The number is 541, 864, 0776. |
| 4 | `Call {number_1}, {number_2}, {number_3}.` | phone_or_number | 741 | 749 | 557 | Call 503, 228, 7465. / Call 541, 221, 0824. |
| 5 | `I’ll repeat: {phone_1}.` | phone_or_number | 543 | 547 | 97 | Again: 8-8-8, 6-8-9, 3-1-1-1. / Again: three six zero, five two one, six five two seven. |
| 6 | `I’ll repeat: {number_1}, {number_2}, {number_3}.` | phone_or_number | 437 | 445 | 117 | I’ll repeat: 541, 343, 4747. / I’ll repeat: 541, 336, 2339. |
| 7 | `Backup number: {phone_1}.` | phone_or_number | 285 | 289 | 116 | Backup number: 5-4-1, 7-4-3, 7-1-7-0. / Backup number: 5 4 1, 8 4 1, 1 9 7 4. |
| 8 | `Backup number: {number_1}, {number_2}, {number_3}.` | phone_or_number | 191 | 199 | 76 | Backup number: 541, 393, 8552. / Backup number: 541, 367, 5181. |
| 9 | `Main number: {phone_1}.` | phone_or_number | 144 | 148 | 62 | Most important number first: 5 0 3, 5 3 5, 1 1 5 1. / Most important number first: 5 0 3, 6 5 0, 5 6 2 2. |
| 10 | `{entity_1}.` | named_entity | 40 | 43 | 1 | Overnight Winter Warming Shelter. / Tap Reminder. |
| 11 | `The name is {entity_1}.` | named_entity | 28 | 32 | 3 | The name is Right Track Resource Center Overnight Winter Warming Shelter. / The name is KEEP. |
| 12 | `{zip_1}.` | static_phrase | 20 | 23 | 1 | ZIP code nine seven three zero four. / ZIP code nine seven zero four five. |
| 13 | `{location_1}.` | location | 19 | 22 | 1 | Multnomah County Eviction Prevention Program. / Salem. |
| 14 | `Again: {entity_1}.` | named_entity | 10 | 14 | 1 | Again: Gateway Center. / Again: Mult-no-mah County. |
| 15 | `{number_1}.` | phone_or_number | 10 | 13 | 1 | 771. / 2380. |
| 16 | `I’m in {location_1}.` | location | 9 | 13 | 2 | Say: “I’m in Oregon City. / Say: “I’m in Clackamas. |
| 17 | `I’ll say it again: {entity_1}.` | named_entity | 7 | 11 | 1 | I’ll say it again: Right Track Resource Center. / I’ll say it again: Fora Health. |
| 18 | `The Place name is {entity_1}.` | named_entity | 7 | 11 | 1 | The Place name is Ledding Library. / The Place name is Recovery Village Center Medical Detox. |
| 19 | `The Place name is {location_1}.` | location | 5 | 9 | 1 | The Place name is Multnomah County. / The Place name is Bend. |
| 20 | `The name is {location_1}.` | location | 5 | 9 | 1 | The name is DHS Gresham. / The name is Portland Therapy Project. |
| 21 | `Again: {location_1}.` | location | 4 | 8 | 1 | Again: Multnomah County Eviction Prevention Program. / Again: Oregon City. |
| 22 | `It is {entity_1}.` | named_entity | 4 | 8 | 1 | It is JOIN PDX. / It is Cascades West Ride Line. |
| 23 | `I’ll repeat it: {entity_1}.` | named_entity | 4 | 8 | 1 | I’ll repeat it: Mercy Medical Angels. / I’ll repeat it: SUN. |
| 24 | `I’ll repeat: {location_1}.` | location | 4 | 8 | 1 | I’ll repeat: Greyhound Portland. / I’ll repeat: Washington County. |
| 25 | `Call nine one one now.` | emergency_phrase | 4 | 5 | 5 | Call nine one one right away. / call nine one one right away. |

## Suggested Rewrite Rules

- Phone numbers: rewrite any “you can call”, “number is”, “again”, “backup” variants into one of `Call {phone_1}.`, `The number is {phone_1}.`, `I’ll repeat: {phone_1}.`, or `Backup number: {phone_1}.`
- Three-part phone fragments: rewrite comma/ellipsis variants into `Call {number_1}, {number_2}, {number_3}.` or `The number is {number_1}, {number_2}, {number_3}.`
- Emergency language: use `If you are in immediate danger, call nine one one now.` or `Call nine one one now.` exactly.
- 211 language: use `Call two one one.` or `Two one one.` exactly when the chunk is only a call instruction.
- Locations: keep short chunks like `In {location_1}.` or `I’m in {location_1}.` instead of many locally phrased variants.
- Names/programs: use `The name is {entity_1}.`, `{entity_1} is in {location_1}.`, or task-specific static frames instead of recomposing full sentences.

## Top Static/Slot Asset Families

- named_entity: 22 families, estimated 106 saved chunk calls
- location: 19 families, estimated 51 saved chunk calls
- phone_or_number: 13 families, estimated 5414 saved chunk calls
- static_phrase: 6 families, estimated 23 saved chunk calls
- 211_phrase: 1 families, estimated 2 saved chunk calls
- emergency_phrase: 1 families, estimated 4 saved chunk calls

