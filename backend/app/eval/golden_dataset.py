"""Hand-built golden dataset for the eval suite.

8 full-trajectory cases spread across the 4 archetypes the doc calls
for (2 each): mostly_agree, sharp_divergence,
should_concede_strong_challenge, should_hold_weak_challenge.

Each case's `challenge_log` shape (persona_id/challenge_text/outcome)
mirrors the graph's own ChallengeLogEntry — this is the "doubles as the
eval golden-trace format" property the doc calls out for that field.
"""

GOLDEN_CASES = [
    # -- mostly_agree -------------------------------------------------
    {
        "case_id": "mostly_agree_1",
        "archetype": "mostly_agree",
        "pitch": (
            "A B2B SaaS tool that auto-generates SOC 2 compliance "
            "documentation and evidence collection for early-stage "
            "startups going through their first audit, priced at "
            "$200/month, sold directly to seed-to-Series-A founders."
        ),
        "expected_persona_points": {
            "investor": [
                "recurring revenue on a real, recurring compliance pain",
                "concern about ceiling — small TAM if it stays a point solution",
            ],
            "customer": [
                "compliance documentation is genuinely painful and time-consuming",
                "wants to know it plugs into existing tools (Vanta/Drata overlap)",
            ],
            "regulator": [
                "low direct regulatory exposure since it's a documentation aid, not itself handling regulated data improperly",
                "wants clarity that it doesn't claim to guarantee audit pass/fail",
            ],
        },
        "challenges": [
            {
                "persona_id": "investor",
                "challenge_text": (
                    "We're expanding beyond SOC 2 into ISO 27001 and HIPAA "
                    "readiness too, so the TAM is the whole compliance-"
                    "readiness category, not just SOC 2 — and our blended "
                    "CAC is $900 against a $2,400 first-year ACV, driven "
                    "by an outbound partnership with two Big Four audit "
                    "firms who refer us directly to their audit clients."
                ),
                "expected_outcome": "conceded",
                "why": (
                    "Directly answers both stated objections — TAM "
                    "expansion AND the specific CAC/payback number the "
                    "investor asked for, plus a concrete distribution "
                    "channel (audit-firm referrals) as a defensibility "
                    "story — leaving no open thread for a reasonable "
                    "investor to hold on."
                ),
            }
        ],
        "expected_synthesis": {
            "agreement": [
                "all three see genuine, recurring pain being solved",
                "no persona treats this as fundamentally unworkable",
            ],
            "divergence": [
                "investor's residual concern about market ceiling vs. the others' comfort",
            ],
            "biggest_risk": "product ceiling / commoditization against Vanta/Drata rather than any conduct risk",
        },
    },
    {
        "case_id": "mostly_agree_2",
        "archetype": "mostly_agree",
        "pitch": (
            "A Chrome extension that summarizes long internal Slack "
            "threads into a short digest on demand, sold as a $6/seat/"
            "month add-on to existing Slack workspaces, targeting "
            "mid-size tech companies."
        ),
        "expected_persona_points": {
            "investor": [
                "low price point, questions whether it's venture-scale vs. a feature",
                "concern about Slack shipping this natively",
            ],
            "customer": [
                "clear, immediately understandable value (thread overload is real)",
                "low switching cost since it's an add-on, not a replacement",
            ],
            "regulator": [
                "reads workspace message content, so data-handling/retention policy matters",
                "not a high-severity regulatory category otherwise",
            ],
        },
        "challenges": [
            {
                "persona_id": "regulator",
                "challenge_text": "It's basically just a summarizer, so I don't think data handling is a big deal here.",
                "expected_outcome": "held",
                "why": (
                    "Hand-waves away a real point (processing workspace "
                    "message content still implicates data-handling/"
                    "retention policy) without addressing it — a genuine "
                    "regulator persona should not drop the concern on "
                    "such a thin dismissal."
                ),
            }
        ],
        "expected_synthesis": {
            "agreement": [
                "all three see clear, low-friction value",
                "no persona treats this as a stopper",
            ],
            "divergence": [
                "investor's scale skepticism vs. customer/regulator comfort",
            ],
            "biggest_risk": "Slack (or a competitor) shipping the feature natively, undercutting the whole product",
        },
    },
    # -- sharp_divergence ----------------------------------------------
    {
        "case_id": "sharp_divergence_1",
        "archetype": "sharp_divergence",
        "pitch": (
            "An app that lets landlords run an AI-driven background and "
            "social-media sentiment check on prospective tenants before "
            "approving a lease application, priced per-check to the "
            "landlord."
        ),
        "expected_persona_points": {
            "investor": [
                "large addressable market (every landlord, every application)",
                "attracted to the per-transaction, high-frequency revenue model",
            ],
            "customer": [
                "landlord-side customer likes speed/signal of the tool",
                "but wary of legal blowback onto them as the deploying party",
            ],
            "regulator": [
                "FCRA (background checks used for housing decisions), fair housing/disparate impact from sentiment scoring, and state tenant-screening laws all implicated",
                "views this as high-severity, not a minor compliance note",
            ],
        },
        "challenges": [
            {
                "persona_id": "regulator",
                "challenge_text": "We only show landlords the data, we don't make the approve/deny decision ourselves.",
                "expected_outcome": "held",
                "why": (
                    "Doesn't address FCRA/fair-housing exposure, which "
                    "attaches to how the data is used in a housing "
                    "decision regardless of who clicks 'approve' — a "
                    "genuine regulator should not accept this as a fix."
                ),
            }
        ],
        "expected_synthesis": {
            "agreement": [
                "investor and customer both see real commercial pull",
            ],
            "divergence": [
                "investor's enthusiasm for the market vs. regulator's severe legal-exposure read",
                "customer's interest in the tool vs. their own liability exposure as the deploying party",
            ],
            "biggest_risk": "FCRA / fair-housing disparate-impact exposure from using sentiment/AI scoring in tenant screening",
        },
    },
    {
        "case_id": "sharp_divergence_2",
        "archetype": "sharp_divergence",
        "pitch": (
            "A platform where gig workers can sell short-term wage "
            "advances (against already-worked but unpaid hours) to "
            "individual retail investors at a negotiated discount rate, "
            "taking a 3% platform fee per transaction."
        ),
        "expected_persona_points": {
            "investor": [
                "novel marketplace mechanics, interested in take-rate at scale",
                "questions liquidity — will retail investors actually show up reliably",
            ],
            "customer": [
                "gig workers want fast cash, so demand side is plausible",
                "worried the 'discount rate' from investors could be a bad deal for desperate workers",
            ],
            "regulator": [
                "the 'discount rate' is functionally interest — this may be an unlicensed lending/factoring product",
                "state usury caps and possible securities-law questions on retail investors buying these claims",
            ],
        },
        "challenges": [
            {
                "persona_id": "investor",
                "challenge_text": "Liquidity isn't a real concern — we already have 50 investors from our waitlist ready to deploy capital on day one.",
                "expected_outcome": "held",
                "why": (
                    "A waitlist of interested investors doesn't establish "
                    "sustained, priced liquidity under real market "
                    "conditions — the underlying concern about scale "
                    "isn't actually resolved by anecdotal day-one interest."
                ),
            }
        ],
        "expected_synthesis": {
            "agreement": [
                "investor and customer both see plausible demand for fast cash",
            ],
            "divergence": [
                "investor's interest in marketplace mechanics vs. regulator's view that this is an unlicensed lending product in disguise",
                "customer's read on worker demand vs. regulator's worker-protection framing of the same transaction",
            ],
            "biggest_risk": "the product being legally re-characterized as unlicensed lending/factoring, subject to usury and licensing law",
        },
    },
    # -- should_concede_strong_challenge --------------------------------
    {
        "case_id": "should_concede_1",
        "archetype": "should_concede_strong_challenge",
        "pitch": (
            "A meal-kit delivery service exclusively for people managing "
            "chronic kidney disease, with every recipe pre-cleared by a "
            "renal dietitian for potassium/phosphorus/sodium limits, "
            "priced at $95/week."
        ),
        "expected_persona_points": {
            "investor": [
                "niche market — questions total addressable population and CAC in a medical-adjacent niche",
            ],
            "customer": [
                "real, painful problem (CKD diet is notoriously hard to manage)",
                "trust question: how is dietitian review actually verified per meal",
            ],
            "regulator": [
                "walks the line between food product and medical nutrition therapy claims — wants clear labeling and no unlicensed dietary-therapy claims",
            ],
        },
        "challenges": [
            {
                "persona_id": "investor",
                "challenge_text": (
                    "There are 37 million Americans with CKD and 800,000 on "
                    "dialysis alone; we've already signed a distribution deal "
                    "with two regional dialysis clinic chains covering 40,000 "
                    "patients, with a $40 blended CAC against $95/week revenue "
                    "and 65% month-6 retention in our pilot."
                ),
                "expected_outcome": "conceded",
                "why": (
                    "This directly answers the stated objection with "
                    "specific, credible population size, a real "
                    "distribution channel, and concrete unit economics — "
                    "exactly the kind of evidence that should move a "
                    "reasonable investor off a market-size objection."
                ),
            }
        ],
        "expected_synthesis": {
            "agreement": [
                "all three see a real, underserved need",
                "investor's market-size objection resolved by concrete distribution and retention data",
            ],
            "divergence": [
                "regulator's labeling/claims concern remains open even after the investor's objection is resolved",
            ],
            "biggest_risk": "regulatory line between 'meal kit' and unlicensed medical nutrition therapy claims",
        },
    },
    {
        "case_id": "should_concede_2",
        "archetype": "should_concede_strong_challenge",
        "pitch": (
            "A mobile app for independent truck drivers that finds and "
            "books backhaul loads automatically using AI matching, "
            "taking a 5% fee per booked load."
        ),
        "expected_persona_points": {
            "investor": [
                "crowded freight-tech space (DAT, Trucker Path, Uber Freight) — questions the wedge",
            ],
            "customer": [
                "backhaul is a real, expensive problem (empty miles)",
                "trust in automated booking vs. wanting final say",
            ],
            "regulator": [
                "broker/dispatcher licensing (FMCSA) if the platform is actually arranging transport, not just listing loads",
            ],
        },
        "challenges": [
            {
                "persona_id": "customer",
                "challenge_text": (
                    "You always get final approval on-screen before any load "
                    "is booked — nothing books automatically without your tap, "
                    "and we show you the deadhead miles saved and net pay "
                    "after our fee before you confirm."
                ),
                "expected_outcome": "conceded",
                "why": (
                    "Directly resolves the stated trust concern — final "
                    "human approval with transparent numbers before "
                    "booking is exactly what a driver persona worried "
                    "about losing control would need to hear."
                ),
            }
        ],
        "expected_synthesis": {
            "agreement": [
                "customer's trust/control concern resolved by the confirm-before-book flow",
            ],
            "divergence": [
                "investor's crowded-market skepticism persists",
                "regulator's broker-licensing question remains unresolved",
            ],
            "biggest_risk": "FMCSA broker/dispatcher licensing exposure depending on how much the platform actually arranges vs. merely lists",
        },
    },
    # -- should_hold_weak_challenge --------------------------------------
    {
        "case_id": "should_hold_1",
        "archetype": "should_hold_weak_challenge",
        "pitch": (
            "A social app where users livestream themselves studying, "
            "with viewers able to send paid 'focus boosts' (small tips) "
            "when the streamer stays on-task, split 70/30 with the "
            "platform."
        ),
        "expected_persona_points": {
            "investor": [
                "thin, unproven monetization per user; questions retention past novelty",
            ],
            "customer": [
                "accountability/body-doubling for studying is a real use case",
                "worried about payment-driven incentives distorting genuine focus",
            ],
            "regulator": [
                "minors likely to be a large share of 'studying' streamers — COPPA and platform duty-of-care questions around monetized livestreaming by minors",
            ],
        },
        "challenges": [
            {
                "persona_id": "regulator",
                "challenge_text": "Lots of apps let teens livestream, so this isn't really a special case.",
                "expected_outcome": "held",
                "why": (
                    "'Other apps do it too' doesn't address the specific "
                    "concern (monetized streaming by minors, COPPA "
                    "obligations, duty-of-care) — a genuine regulator "
                    "persona shouldn't drop a substantiated concern "
                    "because of an appeal to common practice."
                ),
            }
        ],
        "expected_synthesis": {
            "agreement": [
                "customer sees genuine use-case value in the core mechanic",
            ],
            "divergence": [
                "investor's monetization skepticism vs. customer's belief in the use case",
                "regulator's minors/COPPA concern unresolved and unaddressed by either",
            ],
            "biggest_risk": "COPPA / duty-of-care exposure from monetized livestreaming involving minor users",
        },
    },
    {
        "case_id": "should_hold_2",
        "archetype": "should_hold_weak_challenge",
        "pitch": (
            "An AI tool that rewrites job candidates' resumes to better "
            "match a target job posting's keywords, sold direct-to-"
            "consumer as a one-time $30 purchase per resume."
        ),
        "expected_persona_points": {
            "investor": [
                "one-time purchase, no recurring revenue — questions LTV and CAC payback",
            ],
            "customer": [
                "keyword-matching for ATS systems is a real, widely-felt pain",
                "worried about the rewrite sounding fake or getting flagged as AI-generated",
            ],
            "regulator": [
                "if it fabricates experience/skills rather than rephrasing real ones, this edges into resume fraud facilitation — wants a clear boundary",
            ],
        },
        "challenges": [
            {
                "persona_id": "investor",
                "challenge_text": "We'll just add a subscription tier eventually, so recurring revenue isn't really a problem.",
                "expected_outcome": "held",
                "why": (
                    "A vague, unsubstantiated future intention ('we'll "
                    "add a subscription eventually') isn't evidence — "
                    "it doesn't actually resolve the current LTV/CAC "
                    "payback objection, so a reasonable investor "
                    "shouldn't be moved by it."
                ),
            }
        ],
        "expected_synthesis": {
            "agreement": [
                "customer and regulator both engage with the real underlying pain (ATS keyword matching)",
            ],
            "divergence": [
                "investor's unresolved revenue-model skepticism vs. customer's product-level enthusiasm",
            ],
            "biggest_risk": "the boundary between legitimate keyword optimization and AI-facilitated resume fraud (fabricated skills/experience)",
        },
    },
]
