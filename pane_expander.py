# pane_expander.py
# Converts worksheet quantity rows into individual panes for optimization.


def expand_windows(windows):
    panes = []

    for w in windows:
        qty = w["qty"]
        width = w["width"]
        height = w["height"]
        section = w.get("section", "Unassigned")
        film = w.get("film", "Unassigned")

        for i in range(qty):
            panes.append({
                "section": section,
                "film": film,
                "width": width,
                "height": height
            })

    return panes
