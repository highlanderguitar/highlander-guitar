from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
OUT = ROOT / "reviews" / "bh_5432" / "setlist_opportunities"

PROGRESSIONS = {
    "Walls of Time": "G | G | G | G | G | G | C | F | G | G | G | G | C | D | G | G",
    "I Feel the Blues Movin' In": "G | G | G | D/G | G | G | G | D/G | G | G | G | G | C | C | G | G | C | C | G",
    "Farewell Blues": "C/G | C | C/G | C | A7 | D/D# | C/G | C | C/G | C | C/G | C | C | A7 | D/D# | C/G | C | C",
    "Dig a Hole in the Meadow": "C | C | C | C | C | C | C/G | C | C",
    "Sarafina": "G | D | A | Bm | Em | Bm | A | A | G | D | A | Bm | Em | A | D | D | G/A | Bm | G | A | G | Bm | A | A | G/A | Bm | G/A | Bm | Em | A | D | D",
    "Trail of Tears": "Em | D | Em | Em | Em | Em | Em | Em | A | A | B7 | B7 | B7 | B7 | Em | Em",
    "Perfume, Powder and Lead": "G | G | G | D/G | C | C | G | G | G | D/G",
    "Rank Strangers": "C | C | C | G | C | C | C | C | C | C | C | D | G | G7 | C | C | C | G | C | C | C | C | C | C | C | G | C | F | C | C | C | C | C | C | C | C | C | C | C | D | G | G7 | C | C | C | F | C | C | C | C | C | C | Am | G | C | F | C",
    "Dear Old Dixie": "G | G | G | G | C | C | G | G | G | G | G | G | A | A | D | D | G | G | G | G7 | C | C | B7 | B7 | C | C | G | Em | A | D | G | G",
    "Bright Sunny South": "G | G/F | Dsus2 | Dsus2 | Dsus2 | Dsus2 | Dsus2 | G",
    "Somehow Tonight": "G | G | G | G | G | G | D | D | G | G | G | G | G | G | D | G",
    "Can't You Hear Me Calling": "G | G | G | G | C | C | G | G | C | C | G | G | C | D | G",
    "Sitting on Top of the World": "G | G/G7 | C | G | G | Em | G/D | G",
    "Southern Flavor": "Em | Em | Em | Em | Em | Em | B7 | B7 | Em | Em | Em | Em | G | B7 | Em | Em | D | D | E | E | D | D | B7 | B7 | Em | Em | Em | Em | G | B7 | Em | Em",
}

FIELDS = [
    "tune", "measure", "chord", "preceding_chord", "following_chord", "function",
    "opportunity_type", "opportunity_window", "harmonic_state", "melody_space", "musical_preconditions", "lick_family",
    "lick_segment", "operation", "strategy", "entry_beat", "pickup_allowance",
    "target_note", "exit_note", "resolution", "continuation_required",
    "minimum_harmonic_duration", "preferred_harmonic_duration", "maximum_useful_duration",
    "source_fingering_area", "practical_fingering_area", "tier", "confidence", "reason",
    "restriction", "review_example",
]


def opportunity(tune, measure, chord, preceding, following, function, kind, window,
                preconditions, family, segment, operation, entry, target, exit_note,
                resolution, continuation, minimum, preferred, maximum, tier, confidence,
                reason, restriction="", review=False, strategy="PRIMARY"):
    return dict(zip(FIELDS, [
        tune, measure, chord, preceding, following, function, kind, window, window,
        "unknown from supplied harmony; confirm against melody/rehearsal", preconditions,
        family, segment, operation, strategy, entry, "up to one beat unless marked split",
        target, exit_note, resolution, continuation, minimum, preferred, maximum,
        "canonical C / source register", "acoustic-safe; high E <=16, other strings <=15",
        tier, f"{confidence:.2f}", reason, restriction, "yes" if review else "no",
    ]))


O = []
add = O.append

# Tier 1 examples chosen for the playable review package.
add(opportunity("Walls of Time", 3, "G", "G", "G", "I", "static-chord development", "middle tonic", "instrumental space; repeated tonic; no busy melody", "from 5", "m1 complete", "literal transposition C->G", "1", "B", "B", "remain on G", "no", "1 measure", "2-4 tonic measures", "4 measures", 1, .93, "Long G tonic is the clearest place to develop the major-seven enclosure as melodic color.", review=True))
add(opportunity("Walls of Time", 14, "D", "C", "G", "V", "dominant-to-tonic resolution", "dominant immediately before tonic", "full-measure dominant; tonic follows", "from 3", "m8 complete plus added G landing", "literal transposition of G13 reading to D13", "1", "A", "A", "G or B on m15 beat 1", "yes: explicit tonic landing", "1 measure", "1 measure", "1 measure", 1, .91, "D lasts a full measure and resolves directly to G.", review=True))
add(opportunity("I Feel the Blues Movin' In", 10, "G", "G", "G", "I", "static-chord development", "repeated tonic", "long tonic; instrumental break or held vocal note", "from 5", "m1 complete", "literal transposition C->G", "1", "B", "B", "remain on G", "no", "1 measure", "2 measures", "4 measures", 1, .90, "The third four-bar G span provides room without crowding a change.", review=True))
add(opportunity("I Feel the Blues Movin' In", 13, "C", "G", "C", "IV", "IV arrival", "first static IV measure", "two-measure IV; phrase space", "from 5", "m1 complete", "original-pitch application", "1", "E", "E", "continue C or return G", "no", "1 measure", "2 measures", "2 measures", 1, .88, "Canonical C major-seven material receives two full C measures.", review=True))
add(opportunity("Dig a Hole in the Meadow", 3, "C", "C", "C", "I", "static-chord development", "middle tonic", "static tonic; instrumental break; singer holding", "from 5", "m1 complete", "original-pitch application", "1", "E", "E", "remain on C", "no", "1 measure", "2 measures", "4 measures", 1, .96, "This is the strongest unambiguous canonical-C practice window in the set.", review=True))
add(opportunity("Dig a Hole in the Meadow", 6, "C", "C", "C/G", "I", "phrase ending", "late tonic", "long tonic; approaching a split connector", "from 4", "m2 short segment", "segment extraction", "1", "C", "C", "hold C before split measure", "no", "1 measure", "1 measure", "1 measure", 1, .87, "Late static C supports the shorter tonic/add9 segment without forcing the split measure.", review=True))
add(opportunity("Sarafina", 14, "A", "Em", "D", "V of D", "dominant-to-tonic resolution", "dominant immediately before tonic", "full-measure A; D follows", "from 3", "m8 complete plus D landing", "literal transposition of G13 reading to A13", "1", "E", "E", "D or F# on m15 beat 1", "yes: explicit tonic landing", "1 measure", "1 measure", "1 measure", 1, .91, "The clearest major dominant resolution in a harmonically busy tune.", review=True))
add(opportunity("Perfume, Powder and Lead", 2, "G", "G", "G", "I", "static-chord development", "middle tonic", "three-measure opening tonic; instrumental fill", "from 5", "m1 complete", "literal transposition C->G", "1", "B", "B", "remain on G", "no", "1 measure", "2 measures", "3 measures", 1, .92, "The opening G plateau gives the phrase enough air before D/G.", review=True))
add(opportunity("Rank Strangers", 7, "C", "C", "C", "I", "static-chord development", "repeated tonic", "extended tonic; melody gap", "from 5", "m1 complete", "original-pitch application", "1", "E", "E", "remain on C", "no", "1 measure", "2 measures", "4 measures", 1, .94, "Repeated C measures are ideal for the canonical tonic family.", review=True))
add(opportunity("Rank Strangers", 42, "G7", "G", "C", "V7", "dominant-to-tonic resolution", "late dominant", "two-measure G/G7 span; C follows", "9th arp", "m21 G13 reading plus C landing", "harmonic reinterpretation", "1", "D", "D", "C or E on m43 beat 1", "yes: explicit tonic landing", "1 measure", "2 dominant measures", "2 measures", 1, .95, "The G-to-G7 expansion supplies both setup and a decisive C resolution.", review=True))
add(opportunity("Dear Old Dixie", 20, "G7", "G", "C", "V7 of IV", "dominant-to-tonic resolution", "dominant immediately before tonic", "G7 explicitly encoded; C follows", "9th arp", "m21 G13 reading plus C landing", "harmonic reinterpretation", "1", "D", "D", "C or E on m21 beat 1", "yes: explicit C landing", "1 measure", "1 measure", "1 measure", 1, .96, "This is the corpus's cleanest original-root G13/G7 application.", review=True))
add(opportunity("Dear Old Dixie", 30, "D", "A", "G", "V", "dominant-to-tonic resolution", "turnaround dominant", "full D measure; G ending follows", "from 3", "m8 complete plus G landing", "literal transposition of G13 reading to D13", "1", "A", "A", "G or B on m31 beat 1", "yes: explicit tonic landing", "1 measure", "1 measure", "1 measure", 1, .93, "End-of-form D-to-G is a natural soloistic turnaround.", review=True))
add(opportunity("Somehow Tonight", 8, "D", "D", "G", "V", "dominant-to-tonic resolution", "late dominant", "second full D measure; G follows", "from 3", "m8 complete plus G landing", "literal transposition of G13 reading to D13", "1", "A", "A", "G or B on m9 beat 1", "yes: explicit tonic landing", "1 measure", "2-measure dominant", "2 measures", 1, .95, "The second D measure is the experienced-player window: established dominant, then release.", review=True))
add(opportunity("Can't You Hear Me Calling", 14, "D", "C", "G", "V", "dominant-to-tonic resolution", "dominant immediately before tonic", "full D measure; final G follows", "from 3", "m8 complete plus G landing", "literal transposition of G13 reading to D13", "1", "A", "A", "G or B on m15 beat 1", "yes: explicit tonic landing", "1 measure", "1 measure", "1 measure", 1, .94, "The final C-D-G cadence gives clear preparation, opportunity, and resolution.", review=True))

# Situational, experimental, split-measure, and unsupported findings.
add(opportunity("Farewell Blues", 1, "C/G", "start", "C", "I/V split", "split-measure connector", "second half dominant", "provisional beat-3 split; exact rhythm unconfirmed", "from 3", "two-beat dominant fragment", "segment extraction", "3 provisional", "D", "D", "C on m2 beat 1", "yes", "2 beats", "2 beats", "2 beats", 2, .67, "G in the second half can prepare the next C.", "Reject until the split beat and two-beat ending are approved."))
add(opportunity("Farewell Blues", 5, "A7", "C", "D/D#", "secondary dominant", "dominant preparation", "single dominant measure", "full-measure A7; ambiguous following split", "from 3", "dominant segment", "literal transposition G13->A13", "1", "E", "E", "D candidate", "yes", "1 measure", "1 measure", "1 measure", 3, .44, "A7 fits a transformed dominant family, but D/D# prevents a confident landing.", "Following chord quality and split timing require confirmation."))
add(opportunity("Trail of Tears", 13, "B7", "B7", "B7", "V of Em", "dominant continuation", "sustained dominant", "four-measure B7; minor tonic follows", "from 3", "dominant family with minor ending", "chord-relative transformation", "1", "F#", "F#", "G on Em", "yes", "1 measure", "2 measures", "3 measures", 2, .71, "Long B7 is excellent dominant space.", "Current major-tonic ending is invalid; minor-resolution variant required."))
add(opportunity("Bright Sunny South", 6, "Dsus2", "Dsus2", "Dsus2", "V-sus", "dominant continuation", "sustained dominant", "five-measure suspended chord", "from 3", "dominant fragment without third", "chord-relative transformation", "1", "A", "A", "G on m8", "yes", "1 measure", "2 measures", "4 measures", 3, .52, "There is ample duration, but the suspended quality makes F# handling arrangement-dependent.", "Do not impose D13 until the third is confirmed."))
add(opportunity("Sitting on Top of the World", 2, "G/G7", "G", "C", "I/V7 of IV split", "split-measure connector", "second half dominant", "provisional half-measure G7; C follows", "9th arp", "two-beat G13 fragment", "segment extraction", "3 provisional", "D", "D", "C on m3 beat 1", "yes", "2 beats", "2 beats", "2 beats", 2, .78, "Explicit G7-to-C motion is attractive.", "A new approved two-beat ending is needed."))
add(opportunity("Sitting on Top of the World", 7, "G/D", "Em", "G", "I/V split", "split-measure connector", "second half dominant", "provisional half-measure D; G follows", "from 3", "two-beat D13 fragment", "literal transposition plus segment extraction", "3 provisional", "A", "A", "G on m8 beat 1", "yes", "2 beats", "2 beats", "2 beats", 2, .74, "D in the second half points directly to G.", "Exact split beat and shortened phrase require approval."))
add(opportunity("Southern Flavor", 7, "B7", "Em", "B7", "V of Em", "dominant continuation", "first dominant measure", "two-measure B7; minor tonic follows", "from 3", "dominant family with minor ending", "chord-relative transformation", "1", "F#", "F#", "G on Em", "yes", "1 measure", "2 measures", "2 measures", 2, .73, "The dominant duration is strong.", "Minor-resolution variant does not yet exist."))

# One explicit gap row per tune keeps unsupported regions visible instead of forcing matches.
GAPS = {
    "Walls of Time": "F m8: no approved static-IV or departing-IV phrase",
    "I Feel the Blues Movin' In": "D/G split measures: exact split beat and short connector unapproved",
    "Farewell Blues": "D/D# regions: chord quality and split function unresolved",
    "Dig a Hole in the Meadow": "C/G m7: short split connector not yet approved",
    "Sarafina": "Bm and Em measures: current major corpus does not cover minor tonic areas",
    "Trail of Tears": "Em tonic vamp: no current minor-tonic BH-5432 family",
    "Perfume, Powder and Lead": "D/G splits: need an approved two-beat D-to-G connector",
    "Rank Strangers": "Am m53: no current minor-tonic application",
    "Dear Old Dixie": "B7-to-C and G-to-Em: non-diatonic/minor landings need dedicated variants",
    "Bright Sunny South": "Dsus2 plateau: no approved suspended-dominant version",
    "Somehow Tonight": "one-measure D m15: full phrase is possible but crowded near form ending",
    "Can't You Hear Me Calling": "rapid final C-D-G: only the D measure is currently recommended",
    "Sitting on Top of the World": "Em m6 and both split measures need minor/short variants",
    "Southern Flavor": "Em tonic spans: no current minor-tonic family",
}
for tune, gap in GAPS.items():
    add(opportunity(tune, "various", "various", "various", "various", "unsupported", "currently unsupported", "unsuitable region", "minor, suspended, ambiguous, or rapid harmony", "none", "none", "none", "n/a", "n/a", "n/a", "none", "no", "n/a", "n/a", "n/a", 4, 1.0, gap, "Do not force pitch-class overlap."))


def write_normalization():
    lines = [
        "# BH-5432 progression normalization", "",
        "`|` separates measures. `/` means successive chords within one measure, never slash bass. Split timing is provisionally beat 3 unless confirmed. Commas in the supplied text only separated larger phrases. Repeated chords preserve duration.", "",
        "| Tune | Preserved normalized progression | Split-measure labels requiring confirmation |", "|---|---|---|",
    ]
    for tune, progression in PROGRESSIONS.items():
        splits = ", ".join(token.strip() for token in progression.split("|") if "/" in token) or "none"
        lines.append(f"| {tune} | `{progression}` | {splits} |")
    (ANALYSIS / "bh_5432_progression_normalization.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_correction():
    (ANALYSIS / "bh_5432_1625_correction.md").write_text("""# BH-5432 1625 correction

The correct progression is **I-vi-ii-V**. In C: **C-Am-Dm-G/G7**.

`vi` is A minor. `iv` is F minor. Minor-plagal `I-iv` analysis is outside this slice unless a supplied tune explicitly contains it.

Repository audit: no tracked BH-5432 report or database application encoded `C-Fm-Dm-G` as 1625, so no musical database row required mutation. This report establishes the corrected doctrine. For ii-V-I, ii is preparation, V is the primary opportunity, and I is resolution unless a row is explicitly marked `SPECIALIZED ii OPTION`.
""", encoding="utf-8")


def write_csv():
    with (ANALYSIS / "bh_5432_setlist_opportunities.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(O)


def write_map():
    lines = [
        "# BH-5432 set-list opportunity map", "",
        "The ranking asks when an experienced player would want the phrase, not where pitch classes merely overlap. Tier 1 means 'I would play this'; Tier 2 is situational; Tier 3 is experimental; Tier 4 is not recommended.", "",
        "## Strongest opportunities by tune", "",
        "| Tune | Best current opportunity | Secondary / experimental | Unsupported region |", "|---|---|---|---|",
    ]
    for tune in PROGRESSIONS:
        rows = [row for row in O if row["tune"] == tune and row["tier"] != 4]
        best = next((r for r in rows if r["tier"] == 1), None)
        secondary = next((r for r in rows if r["tier"] in (2, 3)), None)
        best_text = (f"m{best['measure']} {best['chord']}: {best['lick_family']} {best['lick_segment']} ({best['opportunity_window']})" if best else "No Tier 1 application")
        secondary_text = (f"m{secondary['measure']} {secondary['chord']}: {secondary['lick_family']} ({secondary['restriction']})" if secondary else "none")
        lines.append(f"| {tune} | {best_text} | {secondary_text} | {GAPS[tune]} |")
    lines += [
        "", "## Every-family coverage by tune", "",
        "`T1` = immediate use, `T2` = situational, `T3` = experiment/shortening required, `U` = unsupported. `D` means a dominant window exists; `S` means static major-tonic space exists.", "",
        "| Tune | from 5 | from 4 | from 3 | from 2 | ALL TOGETHER | 9th arp | m26 G lick | low m30-31 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    static_major = {"Walls of Time", "I Feel the Blues Movin' In", "Dig a Hole in the Meadow", "Perfume, Powder and Lead", "Rank Strangers", "Dear Old Dixie", "Somehow Tonight", "Can't You Hear Me Calling"}
    strong_dominant = {"Walls of Time", "Sarafina", "Rank Strangers", "Dear Old Dixie", "Somehow Tonight", "Can't You Hear Me Calling"}
    minor_tunes = {"Trail of Tears", "Southern Flavor"}
    for tune in PROGRESSIONS:
        if tune in minor_tunes:
            cells = ["U minor tonic", "U minor tonic", "T2 B7 + new minor ending", "T3 B7 beat test", "U", "T3 B7 transform", "U", "U"]
        elif tune == "Bright Sunny South":
            cells = ["T2 G only", "T3 G only", "T3 Dsus2 transform", "U", "U", "T3 suspended test", "T2 G only", "U"]
        else:
            cells = [
                "T1 S" if tune in static_major else "T2 major only",
                "T2 short S" if tune in static_major else "T3 segment",
                "T1 D" if tune in strong_dominant else "T2/T3 connector",
                "T3 beat test", "T3 segment only",
                "T1 D" if tune in {"Rank Strangers", "Dear Old Dixie"} else "T2/T3 D",
                "T2 only on G; beat review", "U",
            ]
        lines.append(f"| {tune} | " + " | ".join(cells) + " |")
    lines += [
        "", "## Application doctrine", "",
        "- `from 5`: strongest static/repeated major-tonic family; literal transposition retains major-seven color.",
        "- `from 4`: longer tonic/add9 family; only its short segment is currently recommended. Reinterpretation over ii remains a specialized option, not the default.",
        "- `from 3`: strongest current dominant opportunity, but it requires an added tonic landing.",
        "- `from 2`: chromatic approach needs beat-level approval before set-list promotion.",
        "- `ALL TOGETHER`: segment extraction only; no whole-family chord assignment.",
        "- `9th arp`: strongest on a long or explicit G7/G13 span resolving to C.",
        "- m26 `G lick`: remains G-backed, but its chromatic event order needs a dedicated beat-placement review before Tier 1 use.",
        "- Low-position m30-31: currently unsupported.",
        "", "## Tier 1 review selection", "",
    ]
    for row in [r for r in O if r["review_example"] == "yes"]:
        lines.append(f"- **{row['tune']} m{row['measure']}** — {row['chord']} — {row['lick_family']} — {row['reason']}")
    (ANALYSIS / "bh_5432_setlist_opportunity_map.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_gaps():
    lines = [
        "# BH-5432 application gaps", "",
        "## Corpus weaknesses exposed by the set list", "",
        "- **Highest-value next family:** a compact two-beat dominant-to-tonic connector with major and minor tonic endings. It unlocks D/G, C/G, G/G7, G/D, B7-Em, and fast cadences.",
        "- A minor-tonic family is needed for Trail of Tears, Southern Flavor, Sarafina, and isolated Em/Am/Bm measures.",
        "- `from 3` needs explicit major- and minor-tonic landing notes; its current ending often leaves continuation obligatory.",
        "- `9th arp` needs an approved two-beat ending for split G7-to-C measures.",
        "- Dsus2 requires a suspended-dominant variant that does not assert F# on a strong beat before the arrangement confirms it.",
        "- m26 needs beat-level chromatic annotation before it becomes a reusable set-list application.",
        "", "## Tune-level unsupported regions", "",
    ]
    lines.extend(f"- **{tune}:** {gap}" for tune, gap in GAPS.items())
    (ANALYSIS / "bh_5432_application_gaps.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest():
    tier1 = [row for row in O if row["review_example"] == "yes"]
    manifest = {
        "package": "BH-5432 Set-list Opportunity Engine",
        "status": "needs_human_tuxguitar_review",
        "doctrine": {"1625_in_c": ["C", "Am", "Dm", "G/G7"], "ii_v_i_default": ["ii preparation", "V primary opportunity", "I resolution"]},
        "tier_1_count": len(tier1),
        "tier_1_examples": [{"tune": r["tune"], "measure": r["measure"], "family": r["lick_family"], "decision": "pending"} for r in tier1],
        "user_decisions_required": [
            "Confirm split-measure changes occur on beat 3.",
            "Approve or revise each Tier 1 example in TuxGuitar before database approval.",
            "Choose major and minor landing notes for the new short dominant connector.",
            "Confirm melody space from rehearsal experience; supplied data contains harmony only.",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "BH-5432-Setlist-Application-Review.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def export_support_if_tg_exists():
    tg = OUT / "BH-5432-Setlist-Application-Review.tg"
    if not tg.exists():
        return
    from generate_bh5432_atlas_support import read_tg, musicxml_from_atlas, midi_from_atlas
    root = read_tg(tg)
    musicxml_from_atlas(root, OUT / "BH-5432-Setlist-Application-Review.musicxml")
    midi_from_atlas(root, OUT / "BH-5432-Setlist-Application-Review.mid")


def main():
    ANALYSIS.mkdir(exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    write_normalization()
    write_correction()
    write_csv()
    write_map()
    write_gaps()
    write_manifest()
    export_support_if_tg_exists()
    print(json.dumps({"opportunities": len(O), "tier_1": sum(r["review_example"] == "yes" for r in O), "tunes": len(PROGRESSIONS)}, indent=2))


if __name__ == "__main__":
    main()
