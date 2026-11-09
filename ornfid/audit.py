"""HTML fragments for the audit page (kept in the package so they can be unit-tested)."""

GLIDE_OPTIONS = [("yes", "Yes (meend)"), ("no", "No"), ("unsure", "Unsure")]
OSC_OPTIONS = [("andolan", "Andolan"), ("kampit", "Kampit"), ("gamak", "Gamak"),
               ("other", "Other / not an ornament"), ("unsure", "Unsure")]


def choices_html(kind: str, sid: int) -> str:
    if kind == "glide":
        title, opts = "Is this a meend (a glide between two pitches)?", GLIDE_OPTIONS
    else:
        title, opts = "What is this oscillation?", OSC_OPTIONS
    radios = " ".join(f'<label><input type="radio" name="s{sid}" value="{v}"> {t}</label>' for v, t in opts)
    return f"<b>{title}</b><br>{radios}"
