"""Tender knowledge base: recognising requirements and judging a bid against them.

Written from the bid manager's chair. Three distinctions drive most of the
engine's judgement, and all three are the ones experienced bid teams make
instinctively:

1. A tender *requirement* (something the bid must show) versus a
   *procedural instruction* (how and when to submit) versus a *contract
   obligation* (something the winning contractor will have to do later).
   Only the first can be proven or disproven from the bid text.
2. Silence versus qualification: a bid that doesn't mention a requirement
   is incomplete; a bid that mentions it and proposes something else is a
   deviation, which is worse, because evaluators read it as intent.
3. Stated versus evidenced: "we have extensive experience" is not the
   list of three named projects the tender asked for.
"""

# Sentence-level language ------------------------------------------------------

MANDATORY_CUES = (
    r"\bshall\b", r"\bmust\b", r"\bis required to\b", r"\bare required to\b", r"\bmandatory\b",
    r"\bwill be rejected\b", r"\bshall be rejected\b", r"\bshall not be considered\b",
    r"\bwill not be considered\b", r"\bnon-?responsive\b", r"\bpre-?requisite\b", r"\bobligatory\b",
    r"\bdisqualif", r"\bis to be\b", r"\bare to be\b", r"\bis compulsory\b",
)
INDICATIVE_CUES = (
    r"\bshould\b", r"\bpreferably\b", r"\bis encouraged\b", r"\bare encouraged\b", r"\bdesirable\b",
    r"\bpreferred\b", r"\bwhere possible\b", r"\bideally\b", r"\bmay\b",
)
CONDITIONAL_CUES = (
    r"\bif\b", r"\bwhere\b(?! possible)", r"\bin the event\b", r"\bunless\b", r"\bprovided that\b",
    r"\bin case of\b", r"\bwhen applicable\b", r"\bas applicable\b", r"\bif applicable\b",
)

# Who a sentence is addressed to.
BIDDER_SUBJECT = (
    r"\b(?:the )?(?:bidder|tenderer|applicant|offeror|proposer|respondent|candidate|economic operator)s?\b",
    r"\beach (?:bid|tender|proposal|offer)\b", r"\b(?:bids|tenders|proposals|offers)\b", r"\bpricing\b",
    r"\ball prices\b", r"\bprices\b", r"\bthe (?:bid|tender|proposal|offer)\b",
)
CONTRACTOR_SUBJECT = (
    r"\bthe (?:contractor|supplier|vendor|consultant|service provider|seller)\b",
    r"\ball (?:pressure-containing )?equipment\b", r"\bthe test separator\b", r"\bpersonnel\b",
)
CLIENT_SUBJECT = (
    r"^(?:the )?(?:company|client|employer|owner|purchaser|buyer|authority|agency|ministry|department|entity|operator)\b",
    r"^responsive (?:tenders|bids)",
)

# Consequence language that marks the whole clause as mandatory.
CONSEQUENCE_CUES = (
    r"will be rejected", r"shall be rejected", r"non-?responsive", r"disqualif", r"shall not be considered",
    r"will not be (?:considered|evaluated)", r"without evaluation", r"excluded from",
)

# Procedural instructions: satisfied by the act of submitting correctly,
# not provable from the content of the bid.
PROCEDURAL_CUES = (
    r"submitted (?:electronically|through|via|by|no later than|in writing)", r"no later than \d",
    r"procurement portal", r"sealed", r"envelope", r"requests? for clarification", r"clarifications?",
    r"site visit", r"pre-?bid meeting", r"number of copies", r"(?:hard|soft) cop(?:y|ies)", r"language of (?:the )?(?:bid|tender)",
    r"bid opening", r"tender opening", r"late (?:bids|tenders|submissions)", r"received after",
)

# Language asking the bidder to explicitly accept something.
ACCEPTANCE_CUES = (
    r"confirm (?:its |their )?acceptance", r"confirm (?:that|compliance)", r"\baccept(?:ance)? of\b",
    r"without (?:qualification|alteration|deviation|exception|reservation)", r"unqualified", r"shall accept",
    r"deemed to (?:accept|have accepted)",
)

# Evidence language in a bid.
AFFIRMATIVE_CUES = (
    r"\bconfirms?\b", r"\baccepts?\b", r"\bagrees?\b", r"\bcompl(?:y|ies|iant)\b", r"\bcommits?\b",
    r"\bwill (?:provide|comply|maintain|mobili[sz]e|deliver|submit)\b", r"\bholds?\b", r"\bis enclosed\b",
    r"\bare enclosed\b", r"\battached\b", r"\bincluded\b", r"\bprovided\b", r"\bmaintains?\b",
)

DETAIL_LIST_CUE = r"(?:stating|showing|giving|specifying|indicating|detailing|listing)\s+(?:the\s+)?(.+?)(?:\.|;|$)"

# Categories (first match wins; order matters: specific before general) -----------

CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Mandatory Forms", (r"\bform\s+[a-z0-9]{1,3}\b", r"form of (?:tender|bid)", r"bid submission letter", r"declaration form", r"returnable schedule")),
    ("Tender Administration", (r"submission", r"deadline", r"closing (?:date|time)", r"portal", r"envelope", r"validity", r"\bvalid\b",
                               r"bid (?:bond|security|guarantee)", r"tender (?:bond|security)", r"clarification", r"site visit", r"pre-?bid")),
    ("Certification & Compliance", (r"\biso\b", r"certif", r"accredit", r"licen[cs]e", r"registration", r"\bpermit\b")),
    ("HSE", (r"\bhse\b", r"\bhsse\b", r"health", r"safety", r"incident", r"\btrir\b", r"\bltif\b", r"emergency", r"environmental management")),
    ("Experience & Track Record", (r"experience", r"track record", r"similar (?:projects|contracts|works)", r"references?", r"past performance",
                                   r"completed .* (?:projects|contracts)")),
    ("Financial Standing", (r"turnover", r"financial statements", r"audited", r"net worth", r"liquidity", r"credit rating", r"bank reference",
                            r"financial (?:standing|capacity)")),
    ("Insurance & Liability", (r"insurance", r"indemn", r"liabilit")),
    ("Local Content", (r"in-country", r"local content", r"\bicv\b", r"nationali[sz]ation", r"local (?:suppliers|workforce|employment)")),
    ("Commercial", (r"pric", r"payment", r"invoice", r"currency", r"day-?rate", r"lump sum", r"discount", r"escalation", r"rates?\b")),
    ("Personnel & Resources", (r"personnel", r"supervisors?", r"operators?", r"crew", r"key staff", r"\bcvs?\b", r"curriculum", r"qualified")),
    ("Quality", (r"quality (?:plan|management|assurance|control)", r"\bqa/?qc\b", r"inspection and test plan")),
    ("Technical", (r"equipment", r"capacity", r"specification", r"pressure", r"data", r"technical", r"method", r"mobili[sz]", r"calibrat", r"rated")),
    ("Legal & Ethics", (r"conflict of interest", r"brib", r"corrupt", r"sanction", r"ethic", r"terms and conditions")),
    ("Evaluation", (r"evaluat", r"scoring", r"weighting", r"award criteria")),
)

# Anchor concepts: if the requirement is about one of these, the bid must
# mention it (under any of its names) or the requirement is unevidenced,
# no matter how many generic words overlap.
ANCHORS: dict[str, tuple[str, ...]] = {
    "bid bond": (r"bid (?:bond|security|guarantee)", r"tender (?:bond|security|guarantee)"),
    "performance bond": (r"performance (?:bond|guarantee|security)",),
    "TRIR": (r"\btrir\b", r"total recordable (?:incident|injury) (?:rate|frequency)"),
    "LTIF": (r"\bltif?r?\b", r"lost[- ]time (?:injury|incident) (?:frequency|rate)"),
    "turnover": (r"turnover", r"annual revenue", r"\brevenue\b"),
    "audited financial statements": (r"audited (?:financial statements|accounts)",),
    "in-country value": (r"in-country value", r"\bicv\b", r"local content"),
    "insurance": (r"insurance",),
    "HSE management system": (r"hse management system", r"(?:health,? safety,? (?:and|&) environment(?:al)?|hsse|hse|safety) management system"),
    "emergency response": (r"emergency response",),
    "separator": (r"separator",),
    "data acquisition": (r"data acquisition",),
    "mobilisation": (r"mobili[sz]",),
    "validity": (r"\bvalid\b", r"validity"),
    "payment terms": (r"payment", r"invoice"),
    "price validity": (r"firm and fixed", r"price validity", r"prices? (?:are|shall be|remain) (?:firm|fixed|valid)"),
    "incident reporting": (r"incident report", r"report(?:ing)? (?:of )?(?:any |all )?(?:recordable )?incidents?(?! rate)"),
    "quality management": (r"quality (?:management|plan|assurance)",),
    "key personnel": (r"key personnel", r"\bcvs?\b"),
    "conflict of interest": (r"conflict of interest",),
    "method statement": (r"method statement",),
    "project schedule": (r"project (?:schedule|programme)", r"gantt", r"programme of works"),
    "liability regime": (r"liability (?:regime|position|terms)", r"indemnit(?:y|ies)", r"knock[- ]for[- ]knock"),
}

# Generic tender vocabulary: too common to signal relevance.
STOPWORDS = frozenset(
    """a an the and or of to in on at by for with from as is are be been being was were will shall must may
    should can could would this that these those it its their them they which who whom whose such any all each
    every other than then there here into onto upon within without per not no nor also only both either
    bidder bidders tender tenders tendered bid bids proposal proposals company contractor contractors client
    offer offers apex meridian submit submitted submission provide provided providing include includes included
    including state stated states following required requirement requirements document documents shall
    have has had having does did done make made use used using least minimum maximum less more over under last
    first second third one two three four five six seven eight nine ten days day months month years year
    period time section clause appendix envelope""".split()
)
