# From data to decisions: building a Cape Town housing opportunity atlas

*How I brought Python, GIS, scenario analysis and publishing into one portfolio project.*

A table can rank a location. A map can show where it is. A useful decision tool needs to explain why it ranks where it does, what could change the result, and what still needs to be checked.

That was the challenge behind my Cape Town Housing Opportunity Atlas. I’ve been developing this portfolio project to explore how geospatial analysis and clear reporting can support an early housing land-screening discussion.

The study covers 30 candidate precincts and 14 criteria. It brings together a Python analysis workflow, an interactive web atlas, a Power BI semantic model and an illustrated publication. The common thread is making the reasoning easier to inspect.

## Start with the decision

The central question is where further investigation could be most useful, given a particular set of priorities.

That wording matters. A promising score does not establish that land is available, that zoning has been verified, that services have capacity, or that a development is feasible. Those are separate questions requiring stronger evidence.

The model uses two ranking lenses: efficiency and spatial redress. Each expresses a different emphasis across the criteria. Comparing them makes the role of priorities visible and creates a more useful discussion than presenting one ranking as the inevitable answer.

## Connect a location to its surroundings

Coordinates become more useful when there is context around them.

I used the project’s saved OpenStreetMap snapshot to derive nearby rail and social-facility context. The snapshot contains 131 mapped station or halt points and 1,642 mapped facility features. These support questions about proximity and the surrounding pattern of services.

For example, 14 of the 30 candidate points fall within one kilometre of a mapped rail point. That is a straight-line calculation. It does not establish walking access, service frequency or whether a station is operating.

That distinction is part of the work: choosing a calculation that is reproducible, explaining what it measures, and avoiding a stronger claim than the data supports.

The candidate locations are screening points, rather than verified cadastral boundaries. That affects how the map should be interpreted and what a subsequent investigation would need to add.

## Make the priorities visible

One of my favourite views in the project compares how sites move between the two ranking lenses.

Culemborg moves from 18th under the efficiency lens to 10th under the redress lens. Helen Bowden moves from 15th to 8th. Wingfield moves from 8th to 4th.

The locations have not changed. The emphasis of the decision has.

A visual comparison lets a reader see that immediately. It also creates a practical opening for discussion: which priorities should guide the next stage, who should help set them, and which assumptions need better evidence?

This is the kind of analytical storytelling I enjoy — building a view that reveals the reasoning behind a result.

## Test how stable the shortlist is

A ranking can look precise even when its inputs contain uncertainty. I wanted the report to show some of that uncertainty directly.

The project includes sensitivity analysis for both criteria weights and estimated inputs. The weight analysis uses 5,000 draws; the input analysis uses 2,000 draws. Under the project’s stability threshold — remaining in the top ten in at least 90% of draws — nine candidates are stable under the weight analysis and seven under the input analysis.

These are findings within the model and its perturbation rules. They are not probabilities that a development will succeed.

For me, the practical value is knowing which results remain fairly consistent and where a little more evidence might change the shortlist. It helps turn “here is the answer” into “here is what we should examine next.”

## Design around the reader’s task

The visual redesign focused on giving the map enough space, reducing the competition between controls, and making the selected site easier to understand.

The atlas now supports filtering, site inspection and comparison. It connects the geography to charts and a structured table, so readers can move between an overview and the underlying detail.

The report serves a different reading mode. It has an executive summary, methodology, charts, site profiles, an evidence-gap discussion, a full candidate directory and indexes. The PDF has 30 pages, bookmarks and internal navigation. An EPUB and a browser edition make the same material easier to read in other settings.

That combination reflects an approach I want to bring to remote work: understand what the reader needs to do, then choose a format that makes that task easier.

## Build a model that can be reused

The technical work extends beyond the map.

The Python workflow connects source tables, derived measures, scores and publication outputs. The Power BI work defines a semantic model with a star schema and DAX measures. Its facts include 420 site-by-criterion records and 60 site-by-scenario ranking records.

This is source-defined model work. I would distinguish it from a deployed Power BI service or a finished production dashboard.

The project also includes automated checks: 33 Python tests passed for the version used in this portfolio pack, alongside browser and publication checks. Tests cannot validate every real-world assumption, but they help catch calculation, structure and output errors while the work evolves.

I used AI-assisted development to help iterate on the implementation and publication. The project still needs explicit data definitions, careful review and clear decisions about what each output can honestly say.

## Keep the evidence gaps in view

Eight qualitative criteria remain desktop estimates. Other inputs, including land area, density and some ownership or zoning assumptions, also require independent verification.

For example, the model’s housing capacity figures are scenario calculations. They are not approved projects, committed homes or delivery forecasts. Zoning has not been reconciled to the City’s cadastral layer.

Making those limitations visible improves the next conversation. It points toward practical follow-up work: parcel and ownership checks, verified zoning, infrastructure capacity, environmental constraints, local access conditions and engagement with affected communities.

A well-designed report should help people distinguish what is known, what is calculated and what is assumed.

## Housing affordability needs its own test

A site can score well and still fail the household that is meant to live there. The wider housing discussion therefore needs to ask: affordable to whom, at what total monthly cost, and for how long?

PayProp’s Q4 2025 figures put average rent at R11,894 in the Western Cape and R9,462 nationally. These are dated provincial and national averages, not a Cape Town neighbourhood survey. They provide context rather than a rental forecast for any candidate site. [PayProp, published March 2026](https://www.payprop.com/blog/rental-growth-cooled-in-q4-says-new-payprop-rental-index)

The report now includes a deliberately simple budget illustration. At R20,000 gross monthly household income, R6,000 rent takes 30%. Add R1,000 for utilities and R1,800 for transport, and the combined share reaches 44%, before tax, food, care and debt. These are illustrative assumptions, not observed household data. The 30% line is a comparison benchmark, not a legal limit.

That is why a map of suitable land needs a second layer of questions about target incomes, unit sizes, operating costs, travel and subsidy requirements. The current ranking model does not calculate an achievable rent.

## Match housing challenges with practical responses

The revised report sets out a practical agenda for investigation:

- **Unlock serviced, well-located land.** Verify ownership, planning rights and infrastructure capacity, and follow each site through to occupied homes.
- **Expand social and affordable rental.** Pair land or subsidy with durable affordability conditions, transparent allocation and funded maintenance.
- **Support safe small-scale rental.** Explore technical help, service connections and suitable finance for compliant backyard and small-landlord housing.
- **Protect households facing hardship.** Assess targeted assistance and accessible dispute resolution, with clear eligibility and funding.
- **Measure short-term rental pressure locally.** Distinguish full-time commercial conversions from occasional letting before attributing a neighbourhood’s rent changes to tourism.

These are proposals to evaluate, rather than claims that a particular intervention has already worked in Cape Town. Cost, delivery capacity, resident participation and displacement safeguards need to be part of the design.

There is also a reporting distinction worth preserving: the City’s August 2026 announcement described more than 14,000 affordable units in active land release or project packaging. That is an announced pipeline, separate from this portfolio model and from completed housing. [City of Cape Town](https://web1.capetown.gov.za/web1/newsandnotices/Home/Release/Cape-Town-s-affordable-housing-investment-summit-seeks-partnerships-for-14-000-u?category=Media+releases)

## Where rent controls fit

“Rent control” can mean a freeze, limits on increases during a tenancy, or affordable rents secured through subsidy agreements. Those designs have different consequences.

A well-designed protection can help an existing tenant stay in their home. Its appraisal also needs to examine maintenance, investment, conversion out of long-term rental and access for people looking for their first tenancy. The OECD’s reform framework calls for balancing tenant and landlord protection with rental supply incentives. [OECD, 2024](https://www.oecd.org/content/dam/oecd/en/publications/reports/2024/10/an-agenda-for-housing-policy-reform_450b3a9a/ddb57031-en.pdf)

A San Francisco study found reduced displacement for covered tenants alongside reduced rental supply from affected landlords. That is evidence of a potential trade-off in one historical setting, not a Cape Town prediction. [Diamond, McQuade and Qian, 2019](https://www.aeaweb.org/articles?id=10.1257/aer.20181289)

The local legal framework should also be represented accurately. The Rental Housing Act repealed the former Rent Control Act. Western Cape guidance links increases to agreed lease terms and negotiation where terms are unspecified. The report does not describe 10% or CPI as an automatic legal ceiling. [Rental Housing Act](https://www.gov.za/documents/rental-housing-act) · [Western Cape tenant guidance](https://www.westerncape.gov.za/infrastructure/frequently-asked-questions-tenants)

My proposed approach is to evaluate predictable rental protections alongside affordable supply, funding and enforcement. Any stabilisation proposal needs a legal-authority check, consultation, clear coverage and cost-review rules, and monitoring of both existing tenants and new entrants. The Western Cape Rental Housing Tribunal already provides a free route for rental disputes. [Tribunal information](https://www.westerncape.gov.za/service/rental-housing-tribunal-0)

The analytical contribution is a transparent dashboard: household cost burden, occupied affordable homes, available long-term stock, delivery times, maintenance and displacement. Those are the outcomes that should shape the next iteration of the project.


## The work I’m looking for

This project brings together the work I enjoy: organising data, analysing places, designing usable visual tools and explaining the results in plain language.

I’m open to remote roles and freelance or contract projects involving:

- Python data analysis and reproducible reporting workflows.
- GIS, spatial context and location-based analysis.
- Power BI semantic modelling and analytical reporting.
- Interactive maps, dashboards and data visualisation.
- Clear reports, publications and decision-support material.

If that combination would be useful to your team, message me on LinkedIn. I’d be happy to share the atlas, the report and the approach behind them.

— Anthony Apollis

Project repository: https://github.com/anthonyapollis/Cape_Town_Housing_GIS

*Portfolio study, September 2026. The repository and publication files may represent different revisions; contact me for the edition illustrated here. OpenStreetMap contributors provide the mapped source context. This article describes a desktop screening model, not a municipal commission or a development approval.*
