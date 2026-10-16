# Lakhotia architectural reference grid — governing contract (2026-10-16)

## Architectural source of truth
The user's locked project document `Lakhotia_Gate_Master_Lock.md` designates `Lakhotia_Approved_Gate_From_Final_Print.png` the **SOLE APPROVED gate master**. Its recorded SHA-256 is:
`9ccf79e7f6d7ed22c6f65ed8632d2eb29f6bb6e7056f14f9a3f8d82f905430f5`.

The master is stored in the user's project Library, **not yet vendored into this repo**. Never substitute earlier gate variants or approximate AI renders. No model-generated image can supersede this master unless the Director expressly authorizes a new locked master.

## Reference classes

1. **Plan-locked physical geometry**: gate, central tower, signs, glazing, security room, fuel/CNG canopy, weighbridge, adjoining buildings, road geometry, boundary, barriers, landscaping, warehouse positions and their surroundings **where depicted in approved plans**. No generative construction, removal, relocation, additions or redesign. Use protected placement/crop/scale or non-generative editing only.
2. **Conditional architectural elements**: sheds, warehouses and logistics buildings **outside or separate from protected site imagery**. New conceptual renders require a written brief with source drawings, siting limits, approved dimensions, perspective and contextual references; only use after Director signoff. Labels must disclose conceptual status.
3. **Free creative elements**: people, mood/lighting, graphic texture, typography, layout, abstract brand motifs and off-site generic operations imagery. These can be generated if explicitly separated from site-specific architecture; people/operations scenes must not imply unapproved operating facilities.
4. **Exact brand information**: licensed official logo, project facts, CTA, phone, website. Overlay programmatically in graphic layers; don't ask the image generator to paint text.

## Safe generation protocol (not implemented yet)
- Ingest every approved asset into a **durable, hash-addressed, versioned reference grid**: source, revision, role, approval identity, master priority and permissible regions.
- Map architectural zones as **immutable masks** and restrict AI imagery to permitted regions. Preserve protected pixels and compositing geometry; prompts are not sufficient safeguards.
- Require explicit subject/region whitelist, asset provenance and approval of the reference set **before any paid call**.
- Apply deterministic source-versus-output checks to locked regions (unaltered pixels or verified transforms). Pixel-based verification is more reliable than a model's judgment alone. Fail closed if transformation cannot be proven.
- Require human architectural signoff for new physical design work; export labelled **Illustrative concept** until project team confirms site status.
- Log reference versions, generation parameters, original image and derivative identity.

## Immediate release rule
**The existing `/api/image-lab/generate` path is suspended.** It cannot ensure site fidelity and must not be re-enabled until the safeguards above have evidence-backed tests.
Existing protected artwork can still be used, unmodified, in Brand Studio proof layouts; that approval does not alter the locked gate master.
