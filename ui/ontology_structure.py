ONTOLOGY_GRAPH = {
    "fabio:Work": {
        "po:contains": "deo:DiscourseElement",
        "dc:creator": "foaf:Person",
        "dc:publisher": "bibo:Event",
        "fabio:hasDiscipline": "cso:Topic",
        "amo:hasArgument": "amo:Argument",
    },

    # Argument branches
    "amo:Argument": {
        "amo:hasClaim": "amo:Claim",
        "amo:hasBacking": "amo:Backing",
        "amo:hasEvidence": "amo:Evidence",
        "amo:hasWarrant": "amo:Warrant",
        "idea:proposesIdea": "idea:Idea",
        "idea:concernsIssue": "idea:Issue",
        "idea:realizes": "idea:Approach",
    },

    # Approach branch
    "idea:Approach": {
        "idea:hasAssumption": "idea:Assumption",
        "idea:uses": "idea:Artifact",
        "idea:introduces": "idea:Artifact",
    },
}
