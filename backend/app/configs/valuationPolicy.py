"""
Which approaches a mandate requires.

Basis of value and purpose are not labels — they determine what the report has to
do. A valuation instructed for lending against a tenanted commercial building
cannot be concluded on comparable sales alone, because what secures the loan is
the income stream and a lender's credit note will ask for the yield. A
liquidation valuation for IBC proceedings cannot lean on an income approach that
assumes the business keeps trading.

Encoding it here rather than leaving it to the drafter's judgement is the point:
the requirement is checked in `reconcile.py`, so a conclusion that skips a
mandatory approach is refused rather than noticed in review, or not.

§11.1 is settled as IBBI-registered and bank panel valuation, and these rules
reflect that. They would be materially different for developer feasibility.
"""

from __future__ import annotations

from dataclasses import dataclass

SALES = "sales"
INCOME = "income"
COST = "cost"
ALL_METHODS = (SALES, INCOME, COST)

BASES = ("market", "fair", "liquidation", "distress", "insurable")
PREMISES = ("existing_use", "highest_best_use")


@dataclass(frozen=True)
class ApproachPolicy:
    required: tuple[str, ...]
    forbidden: tuple[str, ...] = ()
    note: str = ""


# Keyed by (basis, is_income_producing). A property that produces income is a
# different valuation problem from one that does not, whatever its basis.
def policy_for(
    basis: str, *, income_producing: bool, specialised: bool = False
) -> ApproachPolicy:
    """
    What this valuation must include, and what it must not.

    `specialised` means a building with no market and no letting evidence — a
    factory, a hospital. There the cost approach is not a cross-check, it is the
    method.
    """
    if basis == "insurable":
        # Insurable value is reinstatement cost. Market evidence is irrelevant to
        # it, and including it invites the wrong number onto the policy.
        return ApproachPolicy(
            required=(COST,),
            forbidden=(SALES, INCOME),
            note=(
                "Insurable value is the cost of reinstatement. Market and income "
                "evidence say what the asset is worth, not what rebuilding costs."
            ),
        )

    if basis in ("liquidation", "distress"):
        return ApproachPolicy(
            required=(SALES,),
            forbidden=(INCOME,),
            note=(
                "A forced-sale basis assumes a constrained marketing period. An "
                "income approach capitalises an income stream the assumed sale "
                "does not preserve."
            ),
        )

    if specialised:
        return ApproachPolicy(
            required=(COST,),
            note=(
                "A specialised building with no market and no letting evidence is "
                "valued on depreciated replacement cost; sales and income evidence "
                "support it where they exist."
            ),
        )

    if income_producing:
        return ApproachPolicy(
            required=(SALES, INCOME),
            note=(
                "What a buyer of a tenanted property purchases is the income "
                "stream. A conclusion on comparable sales alone does not answer "
                "what a lender's credit note asks."
            ),
        )

    return ApproachPolicy(
        required=(SALES,),
        note="An owner-occupied property with market evidence is valued on comparison.",
    )


# Purposes that additionally require the income approach wherever the property
# produces income, regardless of anything else.
PURPOSES_REQUIRING_INCOME = frozenset({"loan", "financial_reporting"})
