"""Single source of truth for every fictional sample document.

The PDFs in sample_data/ are rendered from this module, and
app/services/demo_fixtures.py quotes these same strings as its
`source_excerpt`/evidence text. That's deliberate: the demo project's
whole claim is that every excerpt is a verbatim substring of the real
extracted document text, and deriving both the PDF and the fixture from
one set of strings makes that true by construction rather than by
somebody remembering to re-check after an edit.

Everything here is invented. Meridian Energy Company, Apex Well Services,
the tender reference, the figures, and the incident statistics do not
describe any real procurement, company, or contract.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Clause:
    number: str
    title: str
    text: str


@dataclass(frozen=True)
class Section:
    number: str
    title: str
    clauses: tuple[Clause, ...]


# ---------------------------------------------------------------------------
# Tender: Invitation to Tender for offshore well testing services
# ---------------------------------------------------------------------------

TENDER_TITLE = "INVITATION TO TENDER"
TENDER_SUBTITLE = "Offshore Well Testing Services Package"
TENDER_REFERENCE = "ITB-2026-DEMO-001"
TENDER_CLIENT = "Meridian Energy Company"
TENDER_PREAMBLE = (
    "Meridian Energy Company (the \"Company\") invites suitably qualified contractors to submit "
    "a tender for the provision of offshore well testing services for the North Field "
    "development. This document, together with its appendices, sets out the scope of work, "
    "the qualification requirements, and the basis on which tenders will be evaluated. "
    "This is a fictional document prepared to demonstrate tender compliance software."
)

TENDER_SECTIONS: tuple[Section, ...] = (
    Section(
        "1",
        "Instructions to Bidders",
        (
            Clause(
                "1.1",
                "Submission Deadline",
                "Tenders shall be submitted electronically through the Company's procurement "
                "portal no later than 14:00 hours local time on 30 April 2026. Tenders received "
                "after the stated deadline will be rejected without evaluation.",
            ),
            Clause(
                "1.2",
                "Tender Validity",
                "Each tender shall remain valid and open for acceptance for a period of not less "
                "than one hundred and twenty (120) days from the submission deadline. A tender "
                "offering a shorter validity period shall be treated as non-responsive.",
            ),
            Clause(
                "1.3",
                "Submission Format",
                "The Bidder shall submit its tender in three separately sealed electronic "
                "envelopes: Envelope 1 - Qualification and mandatory forms; Envelope 2 - "
                "Technical proposal; Envelope 3 - Commercial proposal. Pricing information "
                "shall not appear in Envelopes 1 or 2.",
            ),
            Clause(
                "1.4",
                "Clarifications",
                "Requests for clarification shall be submitted in writing no later than fourteen "
                "(14) days before the submission deadline. The Company will issue responses to "
                "all Bidders without identifying the requesting party.",
            ),
            Clause(
                "1.5",
                "Bid Bond",
                "The Bidder shall provide a bid bond in the amount of USD 250,000, issued by a "
                "bank acceptable to the Company and valid for thirty (30) days beyond the tender "
                "validity period.",
            ),
        ),
    ),
    Section(
        "2",
        "Scope of Work",
        (
            Clause(
                "2.1",
                "Overview",
                "The Contractor shall provide personnel, equipment, and consumables for surface "
                "well testing operations on up to six (6) exploration and appraisal wells in the "
                "North Field, including flow testing, data acquisition, and well clean-up "
                "operations.",
            ),
            Clause(
                "2.2",
                "Equipment Provision",
                "The Contractor shall provide a complete surface well test package including a "
                "test separator, surge tank, choke manifold, data header, and associated piping, "
                "rated for a working pressure of not less than 10,000 psi.",
            ),
            Clause(
                "2.3",
                "Personnel",
                "The Contractor shall provide a minimum of two (2) well test supervisors and four "
                "(4) well test operators per crew, each holding valid offshore survival and "
                "medical certification.",
            ),
            Clause(
                "2.4",
                "Mobilisation",
                "The Contractor shall achieve full mobilisation of equipment and personnel to the "
                "Company's designated offshore location within twenty-one (21) days of receipt of "
                "the Company's written call-off notice.",
            ),
        ),
    ),
    Section(
        "3",
        "Qualification Requirements",
        (
            Clause(
                "3.1",
                "Offshore Well Testing Experience",
                "The Bidder shall have completed a minimum of three (3) offshore well testing "
                "projects within the last five (5) years, each involving flow testing of at least "
                "one well. The Bidder shall list each qualifying project stating the client name, "
                "the number of wells tested, and the completion date.",
            ),
            Clause(
                "3.2",
                "Financial Standing",
                "The Bidder shall demonstrate an average annual turnover of not less than USD 20 "
                "million over the last three (3) audited financial years and shall submit audited "
                "financial statements for each of those years.",
            ),
            Clause(
                "3.3",
                "Quality and Environmental Certification",
                "The Bidder shall hold current certification to ISO 9001 (Quality Management), "
                "ISO 14001 (Environmental Management), and ISO 45001 (Occupational Health and "
                "Safety Management). Copies of all three certificates shall be included in "
                "Envelope 1.",
            ),
            Clause(
                "3.4",
                "In-Country Value",
                "The Bidder shall state the percentage of contract value to be spent in-country "
                "and shall commit to a minimum in-country value of forty percent (40%) of the "
                "total contract price.",
            ),
        ),
    ),
    Section(
        "4",
        "Health, Safety and Environment",
        (
            Clause(
                "4.1",
                "HSE Management System",
                "The Bidder shall operate a documented HSE management system and shall submit the "
                "system manual, or a detailed summary of its contents, with its tender.",
            ),
            Clause(
                "4.2",
                "Safety Performance",
                "The Bidder shall report its Total Recordable Incident Rate (TRIR) for each of the "
                "last three (3) calendar years. A Bidder whose three-year average TRIR exceeds "
                "0.50 per 200,000 man-hours shall not be considered for award.",
            ),
            Clause(
                "4.3",
                "Incident Reporting",
                "The Contractor shall report any recordable incident to the Company's HSE "
                "representative within four (4) hours of occurrence and shall submit a written "
                "investigation report within seventy-two (72) hours.",
            ),
            Clause(
                "4.4",
                "Emergency Response",
                "The Contractor shall maintain an emergency response plan covering well control "
                "incidents, hydrocarbon release, and medical evacuation, and shall participate in "
                "the Company's offshore emergency drills.",
            ),
        ),
    ),
    Section(
        "5",
        "Technical Requirements",
        (
            Clause(
                "5.1",
                "Equipment Certification",
                "All pressure-containing equipment shall hold valid third-party certification "
                "issued within the preceding twelve (12) months, and certificates shall be "
                "available for inspection prior to mobilisation.",
            ),
            Clause(
                "5.2",
                "Separator Capacity",
                "The test separator shall have a minimum liquid handling capacity of 10,000 "
                "barrels per day and a minimum gas handling capacity of 50 million standard cubic "
                "feet per day.",
            ),
            Clause(
                "5.3",
                "Data Acquisition",
                "The Contractor shall provide real-time data acquisition with a sampling interval "
                "of not more than ten (10) seconds, and shall deliver the complete test dataset to "
                "the Company within twenty-four (24) hours of the end of each test.",
            ),
        ),
    ),
    Section(
        "6",
        "Commercial Requirements",
        (
            Clause(
                "6.1",
                "Pricing Basis",
                "Pricing shall be submitted on a day-rate basis using the Company's pricing "
                "schedule (Form B) without alteration to its structure. Lump sum or alternative "
                "pricing structures will not be evaluated.",
            ),
            Clause(
                "6.2",
                "Payment Terms",
                "The Company shall pay undisputed invoices within forty-five (45) days of receipt "
                "of a valid invoice supported by Company-approved field tickets. Bidders shall "
                "confirm acceptance of these payment terms without qualification.",
            ),
            Clause(
                "6.3",
                "Currency and Price Validity",
                "All prices shall be quoted in United States Dollars (USD) and shall remain firm "
                "and fixed for the first twenty-four (24) months of the contract term.",
            ),
        ),
    ),
    Section(
        "7",
        "Insurance and Liability",
        (
            Clause(
                "7.1",
                "Insurance Requirements",
                "The Contractor shall maintain employer's liability insurance and third-party "
                "liability insurance, each with a limit of not less than USD 10,000,000 per "
                "occurrence, for the duration of the contract.",
            ),
            Clause(
                "7.2",
                "Liability Position",
                "Bidders shall confirm acceptance of the Company's standard liability regime as "
                "set out in the draft contract, under which each party indemnifies the other for "
                "injury to its own personnel and damage to its own property.",
            ),
        ),
    ),
    Section(
        "8",
        "Mandatory Submission Forms",
        (
            Clause(
                "8.1",
                "Form A - Bid Submission Letter",
                "The Bidder shall submit Form A, signed by a duly authorised representative, "
                "confirming the tender price, the validity period, and acceptance of the tender "
                "conditions.",
            ),
            Clause(
                "8.2",
                "Form B - Pricing Schedule",
                "The Bidder shall submit Form B, completing every line item of the pricing "
                "schedule. Incomplete pricing schedules will be treated as non-responsive.",
            ),
            Clause(
                "8.3",
                "Form C - HSE Statistics Return",
                "The Bidder shall submit Form C, stating lost time injuries, recordable incidents, "
                "and man-hours worked for each of the last three (3) calendar years. Form C is a "
                "mandatory submission and a tender submitted without it will be rejected.",
            ),
            Clause(
                "8.4",
                "Form D - Conflict of Interest Declaration",
                "The Bidder shall submit Form D declaring any actual or potential conflict of "
                "interest involving Company personnel or affiliates.",
            ),
            Clause(
                "8.5",
                "Form E - In-Country Value Commitment",
                "The Bidder shall submit Form E stating its committed in-country value percentage "
                "and the basis of its calculation.",
            ),
        ),
    ),
    Section(
        "9",
        "Evaluation",
        (
            Clause(
                "9.1",
                "Evaluation Criteria",
                "Responsive tenders will be evaluated on a weighted basis of seventy percent (70%) "
                "commercial and thirty percent (30%) technical, applied only to tenders that pass "
                "the qualification and HSE screening in Sections 3 and 4.",
            ),
            Clause(
                "9.2",
                "Grounds for Disqualification",
                "The Company may disqualify a tender that omits a mandatory form, contains pricing "
                "in the technical envelope, or qualifies the Company's payment or liability terms.",
            ),
        ),
    ),
)


# ---------------------------------------------------------------------------
# Bid: Apex Well Services response. Deliberately imperfect.
# ---------------------------------------------------------------------------

BID_TITLE = "TECHNICAL AND COMMERCIAL PROPOSAL"
BID_SUBTITLE = "Offshore Well Testing Services Package"
BID_BIDDER = "Apex Well Services LLC"
BID_PREAMBLE = (
    "Apex Well Services LLC is pleased to submit its proposal in response to Invitation to "
    "Tender ITB-2026-DEMO-001 for offshore well testing services. This is a fictional document "
    "prepared to demonstrate tender compliance software."
)

BID_SECTIONS: tuple[Section, ...] = (
    Section(
        "1",
        "Company Profile and Experience",
        (
            Clause(
                "1.1",
                "Company Overview",
                "Apex Well Services LLC has fifteen (15) years of experience in well testing and "
                "related services across onshore and offshore projects in the region, operating "
                "from bases in three countries with a permanent workforce of 240 personnel.",
            ),
            Clause(
                "1.2",
                "Relevant Project Experience",
                "Apex has successfully delivered numerous well testing campaigns for major "
                "operators, including recent offshore work in the region. Further project details "
                "can be provided on request.",
            ),
            Clause(
                "1.3",
                "Financial Standing",
                "Apex Well Services LLC recorded an average annual turnover of USD 26.4 million "
                "over the financial years 2023, 2024 and 2025. Audited financial statements for "
                "all three years are attached at Appendix 2.",
            ),
        ),
    ),
    Section(
        "2",
        "Certification and Compliance",
        (
            Clause(
                "2.1",
                "Management System Certification",
                "Apex holds current certification to ISO 9001:2015 for quality management and ISO "
                "45001:2018 for occupational health and safety management. Certificates are "
                "attached at Appendix 3. Apex is currently working towards ISO 14001 certification "
                "with an expected audit date in the third quarter of 2026.",
            ),
            Clause(
                "2.2",
                "In-Country Value",
                "Apex commits to an in-country value of forty-two percent (42%) of the total "
                "contract price, comprising local workforce salaries, locally procured "
                "consumables, and subcontracted logistics services. Form E is attached at "
                "Appendix 5.",
            ),
        ),
    ),
    Section(
        "3",
        "Health, Safety and Environment",
        (
            Clause(
                "3.1",
                "HSE Management System",
                "Apex operates a documented HSE management system aligned to ISO 45001, covering "
                "risk assessment, permit to work, competency assurance, and incident "
                "investigation. A summary of the system manual is attached at Appendix 4.",
            ),
            Clause(
                "3.2",
                "Safety Performance",
                "Apex recorded a Total Recordable Incident Rate of 0.71 per 200,000 man-hours "
                "averaged across 2023, 2024 and 2025, reflecting two recordable incidents during a "
                "period of significant growth in offshore activity.",
            ),
            Clause(
                "3.3",
                "Emergency Response",
                "Apex maintains an emergency response plan covering well control, hydrocarbon "
                "release, and medical evacuation, and will participate in all Company offshore "
                "drills as required.",
            ),
        ),
    ),
    Section(
        "4",
        "Technical Proposal",
        (
            Clause(
                "4.1",
                "Well Test Package",
                "Apex will provide a complete surface well test package comprising a test "
                "separator, surge tank, choke manifold, and data header, rated for a working "
                "pressure of 10,000 psi and certified by an independent third party.",
            ),
            Clause(
                "4.2",
                "Separator Capacity",
                "The proposed test separator has a liquid handling capacity of 8,000 barrels per "
                "day and a gas handling capacity of 50 million standard cubic feet per day.",
            ),
            Clause(
                "4.3",
                "Crew Composition",
                "Each crew will comprise two (2) well test supervisors and four (4) well test "
                "operators, all holding current offshore survival and offshore medical "
                "certification.",
            ),
            Clause(
                "4.4",
                "Data Acquisition",
                "Apex will provide real-time data acquisition at a five (5) second sampling "
                "interval, with the complete dataset delivered to the Company within twenty-four "
                "(24) hours of the end of each test.",
            ),
            Clause(
                "4.5",
                "Mobilisation",
                "Apex will mobilise equipment and personnel to the designated offshore location "
                "within twenty-one (21) days of the Company's written call-off notice.",
            ),
        ),
    ),
    Section(
        "5",
        "Commercial Proposal",
        (
            Clause(
                "5.1",
                "Pricing",
                "Pricing is submitted on a day-rate basis using the Company's Form B pricing "
                "schedule, completed in full and enclosed in the separate commercial envelope. "
                "All prices are quoted in United States Dollars.",
            ),
            Clause(
                "5.2",
                "Payment Terms",
                "Apex proposes payment of undisputed invoices within thirty (30) days of receipt "
                "of a valid invoice, and requests that the Company's forty-five (45) day term be "
                "amended accordingly in the final contract.",
            ),
            Clause(
                "5.3",
                "Price Validity",
                "Prices are firm and fixed for the first eighteen (18) months of the contract "
                "term, after which Apex proposes an annual adjustment linked to a published "
                "producer price index.",
            ),
            Clause(
                "5.4",
                "Bid Validity",
                "This proposal remains valid and open for acceptance for one hundred and twenty "
                "(120) days from the submission deadline stated in the tender.",
            ),
        ),
    ),
    Section(
        "6",
        "Insurance",
        (
            Clause(
                "6.1",
                "Insurance Cover",
                "Apex maintains employer's liability insurance with a limit of USD 10,000,000 per "
                "occurrence and third-party liability insurance with a limit of USD 5,000,000 per "
                "occurrence. Certificates of insurance are attached at Appendix 6.",
            ),
        ),
    ),
    Section(
        "7",
        "Enclosed Forms",
        (
            Clause(
                "7.1",
                "Forms Submitted",
                "The following forms are enclosed with this proposal: Form A (Bid Submission "
                "Letter), Form B (Pricing Schedule), Form D (Conflict of Interest Declaration), "
                "and Form E (In-Country Value Commitment).",
            ),
        ),
    ),
)


# ---------------------------------------------------------------------------
# Contract: the executed agreement that follows the tender above, plus an
# amendment. Written to span every ClauseRisk category so a reviewer sees a
# realistic spread of exposures rather than one planted problem.
# ---------------------------------------------------------------------------

CONTRACT_TITLE = "OFFSHORE WELL TESTING SERVICES AGREEMENT"
CONTRACT_REFERENCE = "MEC-NF-2026-014"
CONTRACT_PARTIES = (
    "This Agreement is made between Meridian Energy Company, a company incorporated under the "
    "laws of the State of Qatar (the \"Company\"), and Apex Well Services LLC (the "
    "\"Contractor\"). This is a fictional agreement prepared to demonstrate contract risk "
    "analysis software. It does not describe a real agreement and must not be relied on as a "
    "precedent."
)

CONTRACT_CLAUSES: tuple[Clause, ...] = (
    Clause(
        "2.1",
        "Scope of Services",
        "The Contractor shall provide surface well testing services for up to six (6) wells in "
        "the North Field, including the provision of personnel, equipment, and consumables as "
        "described in Appendix A.",
    ),
    Clause(
        "2.4",
        "Variations",
        "The Company may at any time instruct a variation to the Services. The Contractor shall "
        "proceed with any instructed variation and shall submit its claim for adjustment to the "
        "Contract Price within fourteen (14) days of the instruction, failing which the "
        "Contractor waives its right to any adjustment.",
    ),
    Clause(
        "3.1",
        "Mobilisation",
        "The Contractor shall mobilise all equipment and personnel to the Company's designated "
        "offshore location within twenty-one (21) days of the Company's written call-off notice. "
        "Mobilisation costs shall be borne by the Contractor.",
    ),
    Clause(
        "3.4",
        "Standby and Waiting on Weather",
        "Where operations are suspended due to weather conditions, the Contractor shall be paid "
        "at the standby rate stated in Appendix B for the first seventy-two (72) hours only. "
        "Standby beyond seventy-two (72) hours arising from weather shall be at the Contractor's "
        "cost.",
    ),
    Clause(
        "4.2",
        "Client-Furnished Items",
        "The Company shall provide offshore accommodation, deck space, and crane support. Delay "
        "arising from the unavailability of Company-furnished items shall entitle the Contractor "
        "to standby payment but shall not entitle the Contractor to an extension of the "
        "completion date.",
    ),
    Clause(
        "5.1",
        "Payment Terms",
        "The Company shall pay each undisputed invoice within forty-five (45) days of receipt of "
        "a valid invoice supported by Company-approved field tickets.",
    ),
    Clause(
        "5.2",
        "Set-Off",
        "The Company may set off against any amount due to the Contractor any amount owed by the "
        "Contractor to the Company or to any affiliate of the Company, whether arising under this "
        "Agreement or otherwise.",
    ),
    Clause(
        "5.3",
        "Retention",
        "The Company shall retain ten percent (10%) of each invoice value until issue of the "
        "Completion Certificate, at which point fifty percent (50%) of the retained amount shall "
        "be released and the balance released twelve (12) months thereafter.",
    ),
    Clause(
        "5.5",
        "Price Adjustment",
        "The Contract Price shall remain firm and fixed for the full term of this Agreement and "
        "shall not be subject to adjustment for inflation, changes in labour rates, or changes in "
        "the cost of consumables.",
    ),
    Clause(
        "5.7",
        "Taxes and Duties",
        "The Contractor shall be responsible for all taxes, duties, and levies imposed on it in "
        "connection with the Services, including any withholding tax assessed against payments "
        "made by the Company.",
    ),
    Clause(
        "6.2",
        "Invoicing Currency",
        "All invoices shall be issued in United States Dollars. Where the Contractor incurs cost "
        "in local currency, the exchange rate risk shall be borne by the Contractor.",
    ),
    Clause(
        "8.1",
        "Completion Milestones",
        "The Contractor shall achieve Mechanical Completion of the first well test spread by 30 "
        "June 2027 and shall complete all six (6) well tests by 31 December 2027.",
    ),
    Clause(
        "8.2",
        "Liquidated Damages for Delay",
        "For each day of delay beyond the milestone dates in Clause 8.1, the Contractor shall pay "
        "liquidated damages of USD 5,000 per day, capped in aggregate at ten percent (10%) of the "
        "Contract Price.",
    ),
    Clause(
        "8.4",
        "Extension of Time",
        "The Contractor shall be entitled to an extension of time only for delay caused by a Force "
        "Majeure event or by an instructed variation, and only if written notice is given within "
        "seven (7) days of the Contractor becoming aware of the delaying event.",
    ),
    Clause(
        "9.3",
        "Force Majeure",
        "Force Majeure means war, civil unrest, earthquake, or an act of government preventing "
        "performance. Adverse weather, labour disputes affecting the Contractor's own workforce, "
        "and supply chain disruption shall not constitute Force Majeure.",
    ),
    Clause(
        "10.1",
        "Performance Standard",
        "The Contractor shall perform the Services with the degree of skill, care, and diligence "
        "reasonably expected of a competent contractor experienced in offshore well testing "
        "operations.",
    ),
    Clause(
        "10.4",
        "Performance Guarantee",
        "The Contractor shall provide an on-demand performance guarantee issued by a bank "
        "acceptable to the Company in the amount of ten percent (10%) of the Contract Price, "
        "valid until twelve (12) months after issue of the Completion Certificate.",
    ),
    Clause(
        "11.2",
        "Warranty and Defects",
        "The Contractor warrants the Services against defects for a period of twenty-four (24) "
        "months from the date of the Completion Certificate and shall re-perform defective "
        "Services at its own cost, including all associated vessel and personnel costs.",
    ),
    Clause(
        "12.3",
        "Limitation of Liability",
        "Except in cases of gross negligence or wilful misconduct, the Contractor's aggregate "
        "liability under this Agreement shall not exceed twenty percent (20%) of the Contract "
        "Price. Neither party shall be liable to the other for indirect or consequential losses, "
        "including loss of production, loss of profit, or loss of use.",
    ),
    Clause(
        "12.4",
        "Indemnity for Personal Injury",
        "The Contractor shall indemnify, defend, and hold harmless the Company against all claims, "
        "damages, and losses arising from third-party bodily injury or death caused by the "
        "Contractor's negligence, without limit and without regard to the limitation in Clause "
        "12.3.",
    ),
    Clause(
        "12.6",
        "Pollution Liability",
        "The Contractor shall be liable for pollution originating from its equipment above the "
        "seabed, without limit as to amount, and shall indemnify the Company against all resulting "
        "claims, clean-up costs, and regulatory penalties.",
    ),
    Clause(
        "13.1",
        "Insurance",
        "The Contractor shall maintain employer's liability insurance and third-party liability "
        "insurance, each with a limit of not less than USD 10,000,000 per occurrence, throughout "
        "the term of this Agreement and for twelve (12) months thereafter.",
    ),
    Clause(
        "13.3",
        "Deductibles",
        "All deductibles under the Contractor's insurance policies shall be for the Contractor's "
        "account, and the Contractor shall waive rights of subrogation against the Company.",
    ),
    Clause(
        "14.2",
        "Health, Safety and Environment",
        "The Contractor shall comply with the Company's HSE management system and shall maintain a "
        "Total Recordable Incident Rate not exceeding 0.50 per 200,000 man-hours. A breach of this "
        "Clause shall entitle the Company to suspend the Services without payment.",
    ),
    Clause(
        "14.5",
        "Anti-Bribery and Sanctions",
        "The Contractor warrants that it and its personnel will comply with all applicable "
        "anti-bribery, anti-corruption, and sanctions laws, and that breach of this warranty shall "
        "entitle the Company to terminate this Agreement immediately for cause.",
    ),
    Clause(
        "15.1",
        "Termination for Convenience",
        "The Company may terminate this Agreement in whole or in part at any time for its "
        "convenience upon thirty (30) days' written notice to the Contractor.",
    ),
    Clause(
        "15.2",
        "Payment on Termination",
        "Upon termination under Clause 15.1, the Company shall pay the Contractor for Services "
        "properly performed up to the date of termination. The Contractor shall have no claim for "
        "loss of profit, demobilisation costs, or unrecovered overhead.",
    ),
    Clause(
        "15.4",
        "Termination for Cause",
        "The Company may terminate this Agreement immediately by written notice if the Contractor "
        "commits a material breach, becomes insolvent, or fails to remedy a notified breach within "
        "fourteen (14) days.",
    ),
    Clause(
        "15.6",
        "Suspension",
        "The Company may suspend the Services at any time for any reason. Where suspension exceeds "
        "sixty (60) days in aggregate, the Contractor's sole remedy shall be to request "
        "termination under Clause 15.1.",
    ),
    Clause(
        "17.2",
        "Assignment",
        "The Contractor shall not assign or novate this Agreement, in whole or in part, without "
        "the prior written consent of the Company, which the Company may withhold at its absolute "
        "discretion.",
    ),
    Clause(
        "17.4",
        "Subcontracting",
        "The Contractor shall not subcontract any part of the Services without the Company's prior "
        "written approval, and shall remain fully liable for the acts and omissions of any "
        "approved subcontractor.",
    ),
    Clause(
        "18.1",
        "Intellectual Property",
        "All data, reports, and interpretations generated in the performance of the Services shall "
        "vest in the Company upon creation. The Contractor grants the Company an irrevocable, "
        "royalty-free licence to use the Contractor's background intellectual property to the "
        "extent required to use the deliverables.",
    ),
    Clause(
        "20.1",
        "Confidentiality",
        "Both parties shall keep the terms of this Agreement and all information disclosed under "
        "it confidential, and shall not disclose them to any third party without prior written "
        "consent, for a period of five (5) years from termination.",
    ),
    Clause(
        "22.1",
        "Governing Law and Dispute Resolution",
        "This Agreement is governed by the laws of England and Wales. Any dispute shall be finally "
        "resolved by arbitration seated in London under the LCIA Rules, by three arbitrators, and "
        "the costs of arbitration shall be borne by the unsuccessful party.",
    ),
)

AMENDMENT_TITLE = "AMENDMENT NO. 1"
AMENDMENT_SUBTITLE = "to the Offshore Well Testing Services Agreement MEC-NF-2026-014"
AMENDMENT_PREAMBLE = (
    "This Amendment No. 1, dated 14 May 2026, amends the Offshore Well Testing Services "
    "Agreement between Meridian Energy Company and Apex Well Services LLC. The clauses set out "
    "below are deleted and replaced in their entirety. All other terms remain unchanged. This is "
    "a fictional document prepared to demonstrate contract risk analysis software."
)

# The amendment is where version comparison earns its keep: a payment term
# shortened, a liability cap reduced, LDs left untouched, insurance added,
# and a termination clause hardened.
AMENDMENT_CLAUSES: tuple[Clause, ...] = (
    Clause(
        "5.1",
        "Payment Terms",
        "The Company shall pay each undisputed invoice within sixty (60) days of receipt of a "
        "valid invoice supported by Company-approved field tickets.",
    ),
    Clause(
        "5.3",
        "Retention",
        "The Company shall retain fifteen percent (15%) of each invoice value until issue of the "
        "Completion Certificate, at which point fifty percent (50%) of the retained amount shall "
        "be released and the balance released twelve (12) months thereafter.",
    ),
    Clause(
        "8.2",
        "Liquidated Damages for Delay",
        "For each day of delay beyond the milestone dates in Clause 8.1, the Contractor shall pay "
        "liquidated damages of USD 5,000 per day, capped in aggregate at ten percent (10%) of the "
        "Contract Price.",
    ),
    Clause(
        "12.3",
        "Limitation of Liability",
        "Except in cases of gross negligence or wilful misconduct, the Contractor's aggregate "
        "liability under this Agreement shall not exceed fifteen percent (15%) of the Contract "
        "Price. Neither party shall be liable to the other for indirect or consequential losses, "
        "including loss of production, loss of profit, or loss of use.",
    ),
    Clause(
        "15.1",
        "Termination for Convenience",
        "The Company may terminate this Agreement in whole or in part at any time for its "
        "convenience upon seven (7) days' written notice to the Contractor.",
    ),
    Clause(
        "25.1",
        "Cyber Security and Data Protection",
        "The Contractor shall maintain information security controls consistent with ISO 27001 and "
        "shall notify the Company of any security incident affecting Company data within "
        "twenty-four (24) hours of becoming aware of it.",
    ),
)
