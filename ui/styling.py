
ARGUMENT_TYPE_COLORS = {
    "http://purl.org/spar/fabio/Work":    "#C7C7C7",  # white
    "http://purl.org/spar/amo/Argument":  "#A2F79A",  # light green
    "http://purl.org/spar/amo/Claim":     "#FFE8A3",  # yellow
    "http://purl.org/spar/amo/Evidence":  "#FFB3B3",  # rose
    "http://purl.org/spar/amo/Backing":   "#B775F5",  # mint
    "http://purl.org/spar/amo/Warrant":   "#F3606D",  # blue
    "http://purl.org/spar/amo/Rebuttal":  "#F782F1",  # peach

    # IDEA argument extensions
    "http://www.semanticweb.org/idea/Issue":        "#F3914F",
    "http://www.semanticweb.org/idea/Idea":         "#53EFFA",
    "http://www.semanticweb.org/idea/Approach":     "#E0FFE0",
}
DEFAULT_ARGUMENT_COLOR = "#515251"

legend_styles = {
    "Work": "#FFFFFF",
    "Person": "#A0C3FF",
    "Keyword": "#D0D0D0",
    "Event": "#D6B2FF",
    "Section": "#FFF5A1",

    # Argument subtypes
    "Argument": "#A2F79A",
    "Claim": "#FFE8A3",
    "Evidence": "#FFB3B3",
    "Backing": "#B775F5",
    "Warrant": "#F3606D",
    "Rebuttal": "#F782F1",
    "Issue": "#F3914F",
    "Idea": "#53EFFA",
    "Approach": "#E0FFE0",
}

CLASS_STYLE = {
    "fabio:Work": ("#FFFFFF", "box"),
    "deo:DiscourseElement": ("#FFF5A1", "ellipse"),
    "foaf:Person": ("#A0C3FF", "ellipse"),
    "bibo:Event": ("#D6B2FF", "ellipse"),
    "cso:Topic": ("#D0D0D0", "ellipse"),
    "amo:Argument": ("#C7F3C3", "box"),

    # argument children
    "amo:Claim": ("#FFE8A3", "ellipse"),
    "amo:Evidence": ("#FFB3B3", "ellipse"),
    "amo:Backing": ("#D0F0C0", "ellipse"),
    "amo:Warrant": ("#D3E0FF", "ellipse"),
    "idea:Idea": ("#E5FFE5", "ellipse"),
    "idea:Issue": ("#FFEDC2", "ellipse"),
    "idea:Approach": ("#D0FFFF", "ellipse"),
    "idea:Artifact": ("#E0E0FF", "ellipse"),
    "idea:Assumption": ("#FFE0F0", "ellipse"),
}