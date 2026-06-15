from datetime import datetime
from zoneinfo import ZoneInfo
from storage.db import get_conn
from llm.client import chat
import psycopg2.extras

TZ = ZoneInfo("America/New_York")

CURRICULUM = [
    {
        "module": 1,
        "title": "How Money Actually Works",
        "lessons": [
            ("Assets vs Liabilities", "What an asset is vs a liability. Why rich people buy assets and poor people buy liabilities without knowing it. Real examples: a car you drive vs a car you rent out, a house you live in vs a house that pays you rent. The concept of net worth and how it moves."),
            ("Cash Flow", "Cash flow means money coming in vs money going out every month. Why someone earning $200k can be broke and someone earning $40k can be building wealth. Fixed expenses vs variable. How to calculate your own monthly cash flow right now."),
            ("Leverage", "Leverage means using other people's money to make more than you could alone. How a bank loan lets you control a $300k property with $30k. How businesses use credit lines. The risk side: leverage can multiply losses too. Real scenarios with numbers."),
            ("Compound Growth", "How money grows on top of itself over time. The difference between $5k invested at 25 vs 35 — real dollar numbers. Why starting early matters more than amount. Compound interest on debt works against you the same way."),
            ("Why Most People Stay Broke", "The psychology and habits that keep people in cycles of broke: lifestyle inflation, no financial education, buying status instead of assets, avoiding discomfort of delayed gratification. What the pattern looks like and how to break it."),
        ],
    },
    {
        "module": 2,
        "title": "Spending Smart",
        "lessons": [
            ("How to Think About Every Purchase", "The concept of cost-per-use. A $300 jacket you wear 200 times costs $1.50 per wear. A $80 jacket you wear 3 times costs $27 per wear. How to apply this to clothes, electronics, cars, food. When cheap is expensive and expensive is cheap."),
            ("Buying Clothes and Brands Without Overpaying", "How brand pricing works — what you're actually paying for. How to buy Stone Island, CP Company, Nike, etc. at 40-70% off: outlet stores, Grailed, Depop, eBay, end-of-season sales, last season stock. How to spot fakes. What pieces hold value vs what depreciates instantly. Capsule wardrobe thinking."),
            ("Buying a Car the Right Way", "New vs used — the depreciation curve explained with numbers (a new car loses 20% the moment you drive off). What year/mileage sweet spot gives you the best value. How to inspect a used car, what to check, when to walk away. Dealer tactics: extended warranties, financing markups, add-ons. How to negotiate. Private sale vs dealer. When leasing makes sense and when it's a trap."),
            ("Negotiating Anything", "The mindset: everything has a margin, and sellers expect negotiation. How to negotiate rent, car price, phone bill, salary, contractor quotes. Specific scripts. The power of silence. Walking away as a tactic. When to negotiate and when it's not worth it."),
            ("Where Money Gets Silently Wasted", "Subscriptions you forgot about. Eating out vs cooking — real monthly numbers. Bank fees. High-interest debt compounding quietly. Buying things on emotion. Upgrading phones every year. How to audit your spending and find the leaks in an hour."),
        ],
    },
    {
        "module": 3,
        "title": "Small Hustle Businesses",
        "lessons": [
            ("Ticket Resale", "How ticket resale works end to end: buying tickets on presale or face value, selling on StubHub/Viagogo/Facebook at markup. Which events are worth targeting (sports, concerts, comedy). How to predict demand. Tools people use to buy at scale. Risks: event cancellation, price drops, platform fees eating margin. How people turn this into $2k-$5k/month side income and what scaling looks like."),
            ("Dropshipping and Online Arbitrage", "Dropshipping: you list a product online, customer buys it, supplier ships it directly, you keep the margin. How to find products, set up a Shopify store, run ads. Real margins and why most people fail (competition, ad costs). Online arbitrage: buying discounted products from retail stores or clearance and reselling on Amazon/eBay. What makes it work and what makes it not."),
            ("Vending Machines", "How the vending machine business works: buy a machine ($1,500-$3,000), place it in a location (gyms, offices, laundromats), stock it, collect cash. Real numbers: a decent machine does $300-$800/month revenue at 50-60% margin. How to negotiate placement deals. What to stock. Scaling from 1 machine to 10. What breaks and what the maintenance looks like."),
            ("Pressure Washing and Service Businesses", "Why service businesses are the easiest to start with almost no money: equipment ($300-$800 used pressure washer), Facebook Marketplace ads, door-to-door in nice neighborhoods. Real pricing: $150-$400 per driveway/house. How one person alone can do $3k-$6k/month. How you scale by hiring someone and taking a cut. The same model applies to lawn care, cleaning, window washing, junk removal."),
            ("Laundromats and Passive-ish Businesses", "How laundromats work: lease a space, buy commercial washers/dryers, charge per use. Why they're attractive (cash business, low staff needed, predictable). Real startup costs ($50k-$200k), what revenue looks like, what the profit margins are. How people buy existing laundromats instead of starting from scratch. What goes wrong. How this model extends to car washes, self-storage units, ATMs."),
        ],
    },
    {
        "module": 4,
        "title": "Real Estate",
        "lessons": [
            ("How Mortgages Actually Work", "A mortgage lets you buy a $400k property by only putting in $40k (10%) or $80k (20%). The bank owns the rest and charges you interest. How monthly payments are split between interest and principal. Amortization explained with real numbers over 25 years. Why the first years you're mostly paying interest. Fixed vs variable rates. What happens when rates go up."),
            ("Rental Properties", "Buying a property and renting it out so tenants pay your mortgage and more. How to calculate if a deal makes sense: purchase price, mortgage payment, rental income, expenses (insurance, tax, maintenance, vacancy). The 1% rule as a quick filter. Real example: $250k property, $1,800/month rent, $1,200/month mortgage — what's left and why. How people build a portfolio of 5-10 properties over time."),
            ("House Flipping", "Buying a cheap or damaged property, renovating it, selling it for profit. How to find undervalued properties: foreclosures, estate sales, MLS days-on-market. The formula: After Repair Value minus repair costs minus purchase price minus carrying costs = your profit. Real example with numbers. What goes wrong (hidden costs, contractors, timelines). Why most beginners lose money and how to not be them."),
            ("Building Equity and Using It", "Equity is the portion of your property you actually own. If you bought at $300k and it's worth $400k now and you owe $250k, you have $150k equity. How people pull that equity out via HELOC or refinancing and use it to buy the next property. The snowball effect of doing this across multiple properties. Why real estate built more middle-class wealth than anything else in the last 50 years."),
            ("Getting Into Real Estate Without Being Rich", "House hacking: buy a duplex, live in one unit, rent the other — tenant pays most or all of your mortgage. FHA loans that let you buy with 3.5% down. REITs for investing in real estate like a stock. Joint ventures: partnering with someone who has money while you find and manage the deal. Real strategies people use to get their first property with under $20k."),
        ],
    },
    {
        "module": 5,
        "title": "Buying Existing Businesses",
        "lessons": [
            ("Why Buying Beats Starting", "Starting a business from scratch: 90% fail in 5 years, no customers, no systems, no proof it works. Buying an existing one: it already has customers, revenue, staff, processes. You're buying a machine that already runs. Real comparison: spending 3 years building something vs buying something already doing $200k/year profit. Why this is how a lot of quietly wealthy people operate."),
            ("How to Find Businesses for Sale", "Where deals are listed: BizBuySell, business brokers, local networking, cold outreach to owners of businesses you like. How to evaluate listings: revenue, profit (EBITDA), asking price, why they're selling. The multiple: most small businesses sell for 2-4x annual profit. What red flags look like in a listing."),
            ("Seller Financing and Buying Without Full Cash", "Seller financing: the owner lets you pay them over time instead of needing all the cash upfront. Example: buy a $500k business with $100k down and pay the rest from the business's own profits over 5 years. SBA loans for business acquisition. Why sellers accept this (tax benefits, interest income). How people buy $1M businesses with $50k of their own money."),
            ("What to Look For and What to Avoid", "Due diligence: verifying the numbers (bank statements, tax returns, not just what they tell you). Customer concentration risk (what if 80% of revenue is one client). Owner dependency (does the business run without the owner or does it collapse). Lease terms, equipment condition, staff retention. Real checklists used in acquisitions."),
            ("Factories and Physical Production Businesses", "How manufacturing businesses work: you own machines and labor that turn raw materials into a product you sell at markup. Real example: a small metal fabrication shop buys steel, cuts and welds it into custom parts, sells to contractors at 3-4x material cost. How people find and buy these. The economics of owning the means of production vs just reselling. What makes them hard and what makes them valuable."),
        ],
    },
    {
        "module": 6,
        "title": "Startups and Equity",
        "lessons": [
            ("How Startups Actually Work", "A startup is a business built to grow very fast and eventually sell or go public for a lot of money. Why startups are different from normal businesses: they lose money on purpose to grow fast. How founders think about market size. Why a startup doing $500k revenue can be worth $10M while a normal business doing the same is worth $1.5M. The exit is the point."),
            ("How Investors Work", "Investors give you money in exchange for a percentage of your company. Seed round, Series A, B, C — what each means and what stage the company is at. Valuations: if an investor pays $1M for 10%, the company is valued at $10M. How founders dilute over time and why that's okay if the pie keeps growing. Angels vs VCs — who they are and what they want."),
            ("Equity and How People Get Rich From It", "Equity means ownership. If you own 20% of a company that sells for $50M, you get $10M. How early employees get equity (stock options) at low prices and make life-changing money when the company exits. Vesting schedules: you earn your equity over 4 years so you can't just quit on day one. Why joining an early startup as employee #5-20 can be more valuable than a big salary elsewhere."),
            ("Building a Startup vs Joining One", "When to start vs join: starting needs an idea, market, and high risk tolerance. Joining early means risk with a salary. How to evaluate an early stage company: team quality, market size, traction, funding. Red flags. What questions to ask before taking equity. How to negotiate your option grant."),
            ("Exits: How Everyone Gets Paid", "An exit is when the company is sold (acquisition) or goes public (IPO). Acquisition: a bigger company buys you, everyone with equity gets paid out. IPO: shares go on the stock market, founders and investors can sell. Liquidation preference: why investors get paid first and how that affects what founders and employees actually receive. Real exit scenarios with numbers showing who gets what."),
        ],
    },
    {
        "module": 7,
        "title": "Real Estate — Zero to Pro",
        "sections": [
            {
                "section": 1,
                "title": "Foundations",
                "lessons": [
                    ("What Real Estate Actually Is", "Real estate is land plus anything permanently attached to it — houses, apartment buildings, warehouses, shopping centers, farmland, hotels. Why it has been the single biggest wealth-builder in human history. The two ways it makes money: it produces income (rent), and the underlying asset goes up in value (appreciation). The third hidden way: leverage lets you control a $500k asset with $50k, so a 10% price gain on the property is a 100% gain on your money. Walk through this with real numbers so the concept clicks."),
                    ("The Main Asset Classes", "Residential: single-family houses, duplexes, triplexes, fourplexes, condos, apartments. Commercial: office buildings, retail strip malls, shopping centers. Industrial: warehouses, distribution centers, factories. Hospitality: hotels, motels, short-term rentals. Land: raw land, agricultural, development plots. Special use: storage facilities, mobile home parks, parking lots. What each looks like, what they cost, and who buys what at what stage of their journey."),
                    ("The Players in Every Deal", "Buyer, seller, listing agent, buyer agent, mortgage broker, lender, appraiser, inspector, title company, escrow officer, attorney, insurance agent, property manager. Who they work for, who pays them, what they actually do, and where your money goes to each one. Why understanding the cast is the first step to not being the dumbest person in the room."),
                    ("How Money Moves in a Deal", "Earnest money deposit goes to escrow. Down payment + closing costs come from buyer. Loan proceeds come from lender. Seller's existing mortgage gets paid off. Agent commissions (usually 5-6% split between both sides) come from seller's proceeds. Title insurance, transfer tax, recording fees. Walk through a $300k purchase line-by-line so you see exactly where every dollar lands."),
                    ("Real Estate Vocabulary Decoded", "All the words you'll hear and what they actually mean in plain language: principal, interest, amortization, escrow, equity, lien, deed, title, easement, encumbrance, contingency, appraisal, comp, CMA, ARV, NOI, cap rate, GRM, LTV, DTI, PITI, HOA, MLS, FSBO, REO, short sale, 1031, BRRRR. No jargon left mysterious."),
                    ("Why Real Estate Builds So Much Wealth", "Five forces working at once: cash flow (tenants pay you), appreciation (price goes up over decades), principal paydown (tenant pays your mortgage down), tax benefits (depreciation, deductions, 1031), and leverage (small money controls big asset). Show how a single $300k rental over 20 years can quietly turn into $800k+ of net wealth through all five forces combined."),
                ],
            },
            {
                "section": 2,
                "title": "Markets & Location Analysis",
                "lessons": [
                    ("How to Read a Real Estate Market", "Job growth, population growth, income growth, supply of new construction, days on market, median price trends, rent-to-price ratios. The difference between a hot market (multiple offers, prices climbing) and a cold market (price reductions, long DOM). How to pull these numbers for free from Census, BLS, Zillow, Redfin, Realtor.com. Read a market like a doctor reads vitals."),
                    ("Neighborhood Grading: A, B, C, D Areas", "A = newest, highest income, best schools, lowest cap rates, lowest cash flow but highest appreciation. B = working professionals, decent schools, balanced cash flow + appreciation. C = blue-collar, older housing stock, higher cash flow but more management headaches. D = high crime, low income, highest cash flow on paper but tenants destroy property and don't pay. How to walk a neighborhood and grade it in 20 minutes."),
                    ("Pulling and Reading Comps (Comparable Sales)", "A comp is a property similar to yours that recently sold. You use them to figure out what your property is worth. How to pull comps on Zillow/Redfin/MLS, what filters to use (same neighborhood, similar sqft within 10%, similar beds/baths, sold within 6 months). How to adjust for differences (your house has an extra bathroom, theirs has a garage). The real number you care about is price-per-square-foot and how it compares."),
                    ("MLS and How Agents Actually Search Deals", "The Multiple Listing Service is the database every agent uses. How to get access (work with an agent or pay for IDX feeds). What filters real investors use: days on market > 60, price reduced > 5%, motivated seller keywords ('must sell', 'as-is', 'estate sale', 'handyman special'). How to spot tired listings and how to spot fresh ones before they get bid up."),
                    ("Finding Off-Market Deals", "Off-market means not listed on the MLS. Where the real bargains live. Methods: direct mail to absentee owners, driving for dollars (looking for distressed houses), networking with wholesalers, cold calling owners of properties pulled from county records, probate lists, pre-foreclosure lists, expired listings. Why off-market deals are 10-30% cheaper than MLS deals. The grind nobody romanticizes."),
                    ("Supply and Demand at the Local Level", "Months of inventory: how many months it would take to sell every active listing at current pace. Under 4 months = seller's market. Over 6 months = buyer's market. Building permits: a flood of new construction kills appreciation. Apartment construction kills rents. Where to find permit data for any city. How to spot oversupply before it crushes prices."),
                    ("Demographics and Where People Are Moving", "Population in-migration drives prices up. Out-migration kills them. Why Austin and Phoenix exploded and Detroit collapsed. How to read U.S. Census migration data, IRS county-to-county migration, U-Haul rate differentials (one-way truck rentals cost 3-4x more going to hot markets). Predict the next hot market 2-3 years before everyone else does."),
                ],
            },
            {
                "section": 3,
                "title": "Buying — End to End",
                "lessons": [
                    ("The Full Buying Process Start to Finish", "Step 1: get pre-approved by a lender so you know your budget. Step 2: hire a buyer's agent (paid by seller, free to you in most U.S. markets). Step 3: search and tour properties. Step 4: make an offer. Step 5: negotiate counter-offers. Step 6: go under contract. Step 7: inspection period (usually 7-14 days). Step 8: appraisal. Step 9: loan finalization. Step 10: closing (sign 60+ pages, get keys). Real timeline: 30-45 days from offer to keys in hand."),
                    ("Choosing and Working With a Buyer's Agent", "What a good buyer's agent does: pulls comps, sets up MLS alerts, schedules tours, writes offers, negotiates, manages timelines. What a bad agent does: shows you whatever, pushes you to overbid to close fast. How to interview agents: ask about deals closed last year, what neighborhoods they specialize in, how they handle inspections. Why a great agent saves you more than they cost — even when they're 'free.'"),
                    ("Writing an Offer That Actually Wins", "Price is just one part. Other levers: earnest money amount (bigger = more serious), closing date flexibility (sellers love quick close or rent-back), contingencies waived (riskier but stronger offer), escalation clauses (auto-bid up to X), as-is offers. Real example: how a $5k-lower offer beat the highest bid by waiving the inspection contingency. When to use which lever and when to walk away."),
                    ("Negotiation: Counter-Offers and Backup Tactics", "When seller counters, you almost never accept first counter. Counter back at midpoint or with non-price concessions (they pay closing costs, include appliances, longer inspection window). The 'split the difference' trap. Walking away increases your power 90% of the time. Specific scripts your agent uses. Backup offer position when you lose the bid — about 1 in 5 deals fall through during escrow."),
                    ("The Inspection: What to Look For and What to Negotiate", "A general home inspector charges $400-$700 and takes 3 hours. They check roof, foundation, electrical, plumbing, HVAC, appliances, water heater, structural. Specialty inspectors for sewer line ($200), pool ($150), pest/termites ($100). Real costs of problems: bad roof = $15k-$30k, foundation crack = $5k-$50k+, sewer line = $5k-$15k, electrical panel = $2k-$5k. How to negotiate post-inspection — ask for credits at closing, not repairs (sellers do cheap repairs)."),
                    ("Appraisal: When It Comes In Low", "Bank sends an appraiser to confirm the property is worth what you're paying. If appraisal is below contract price, the bank only lends on the appraised value, leaving you to cover the gap in cash, renegotiate the price down, or kill the deal. Three real options: 1) pay the gap cash, 2) seller drops to appraisal, 3) split the difference. How to challenge a bad appraisal with a 'reconsideration of value' submission including comps the appraiser missed."),
                    ("Title, Escrow, and Closing Costs", "Title search makes sure the seller actually owns the property and no liens are attached. Title insurance ($800-$2,000) protects you if something was missed. Escrow holds the money during the deal. Closing costs total 2-5% of purchase price: lender fees, title fees, escrow fee, recording fee, transfer tax, prepaid property tax and insurance, prepaid interest. Real breakdown on a $300k purchase: $7,500-$15,000 in closing costs."),
                    ("Closing Day and First 30 Days After", "Closing day: review and sign the closing disclosure, wire the down payment + closing costs, sign 60+ pages including the deed and mortgage note, get keys. Immediately: change locks, transfer utilities, update insurance, set up property tax escrow. First month: read every appliance manual, test every system, find and fix small problems before they get big. The 30-day window where you're most likely to discover the inspection missed something."),
                ],
            },
            {
                "section": 4,
                "title": "Mortgages & Lending",
                "lessons": [
                    ("Mortgage Anatomy: PITI Explained", "Every monthly payment is PITI: Principal + Interest + Taxes + Insurance. Real example on a $300k loan at 7% for 30 years: $1,996 P&I + $300 taxes + $100 insurance = $2,396/month. The principal portion is forced savings — it pays down what you owe. The interest portion is the cost of the loan. Taxes and insurance go into an escrow account the bank manages. Why PITI is the only number that matters for affordability."),
                    ("How Amortization Actually Works", "Amortization is the schedule of how each payment splits between interest and principal. On a 30-year loan at 7%, year 1 you're paying $20k in interest and only $3k toward principal. By year 30 it flips. Why making one extra payment per year cuts a 30-year loan to 23 years. Real amortization table walkthrough. Why the first 7 years feel like you're getting nowhere on the loan."),
                    ("Fixed Rate vs Adjustable Rate (ARM)", "Fixed: rate locked for the entire term. Predictable, safer. ARM: rate adjusts after an initial period (5/1 ARM = fixed for 5 years, then adjusts yearly). Lower initial rate, but you eat the risk if rates rise. When ARMs make sense (short-term hold, falling rate environment) and when they wreck people (2008 crash). Real numbers showing how a 5/1 ARM saved or destroyed a buyer based on what happened next."),
                    ("Conventional vs FHA vs VA vs Jumbo", "Conventional: 5-20% down, no government backing, best rates if credit is good. FHA: 3.5% down, lenient credit, requires mortgage insurance for life. VA: 0% down for veterans, no PMI. Jumbo: loans above conforming limit ($766k+ in 2024), stricter requirements. USDA: 0% down in rural areas. Which loan type fits which buyer. Why FHA is the cheat code for first-time buyers but costs you more long-term."),
                    ("Points, Rate Buy-Downs, and Closing Cost Math", "Discount points: you pay 1% of loan upfront to lower rate by ~0.25%. Break-even = how many years until savings cover the cost. Real math on a $300k loan: paying 2 points ($6k) to drop from 7% to 6.5% saves $100/month, break-even at year 5. Lender credits work the opposite way — higher rate, less cash at closing. When to buy down rate vs take the credit."),
                    ("DTI, LTV, and How Lenders Decide", "DTI (debt-to-income): your total monthly debt payments divided by gross monthly income. Max usually 43-50%. LTV (loan-to-value): loan amount divided by property value. 80% LTV = 20% down. PMI required above 80% LTV on conventional. Credit score tiers: under 620 = subprime, 740+ = best rates. Real example of how a 700 vs 760 credit score changes your rate by 0.5% — that's $30k+ over 30 years."),
                    ("PMI and How to Get Rid of It", "PMI (private mortgage insurance) costs 0.3-1.5% of the loan annually if you put down less than 20%. On a $300k loan that's $75-$375/month for nothing — it protects the bank, not you. How to drop it: 1) reach 80% LTV through paydown and request removal, 2) reach 78% LTV (auto-drops by law), 3) refinance once you have 20% equity, 4) get a new appraisal if property value rose. The annual savings stack up fast."),
                    ("Refinancing: When and How", "Refi means replacing your existing loan with a new one. Two types: rate-and-term (lower rate or change term) and cash-out (borrow extra against equity). Closing costs are 2-5% of loan amount. Break-even = costs divided by monthly savings. Generally refi when new rate is 0.75-1% lower than current. Real example: $300k loan dropping from 7% to 6% saves $200/month, $6k in costs, break-even at 30 months."),
                    ("HELOC, Hard Money, Private Money, DSCR Loans", "HELOC: a credit line secured by your home's equity, variable rate, draw as needed — great for funding the next deal. Hard money: short-term high-interest loans from private companies (10-15% rates, 2-4 points) used for flips. Private money: borrowed from individuals (friends, family, network) at negotiated terms. DSCR loans: qualify based on the property's rental income, not your personal income — game-changer for investors. When to use each."),
                    ("Seller Financing in Real Estate", "Owner-financed: instead of the bank giving you the loan, the seller does. They get monthly payments + interest instead of cash up front. Why sellers agree: tax spreading, higher sale price, faster close, can sell hard-to-finance properties (raw land, beat-up houses). Typical terms: 10-20% down, 6-9% interest, 5-10 year balloon. How to find sellers open to it: free-and-clear properties owned by older folks. How to structure the note."),
                ],
            },
            {
                "section": 5,
                "title": "Cost Analysis & Underwriting",
                "lessons": [
                    ("The Pro Forma: Underwriting a Deal Line-by-Line", "A pro forma is the spreadsheet that decides if a deal works. Line items: Gross Scheduled Income (rent at 100% occupancy), minus Vacancy (usually 5-8%), equals Effective Gross Income. Minus Operating Expenses (taxes, insurance, maintenance, management, utilities, capex reserve, HOA), equals Net Operating Income (NOI). Minus Debt Service (mortgage payment) equals Cash Flow. Walk through a real $250k duplex from gross rent to cash flow."),
                    ("NOI: The Single Most Important Number", "Net Operating Income = income minus operating expenses, BEFORE the mortgage. Why NOI is the number — it's the property's earnings regardless of how you finance it. Banks, appraisers, and buyers all care about NOI. Real example: $30k gross rent - $2,400 vacancy - $9,600 expenses = $18,000 NOI. Common mistake: forgetting capex reserve and management fee. If you self-manage, still subtract 8-10% — your time has value."),
                    ("Cap Rate: What It Means and How to Use It", "Cap rate = NOI divided by purchase price. A $200k property with $18k NOI = 9% cap rate. Higher cap rate = better cash flow but usually worse neighborhood or older property. Lower cap rate = appreciation play, usually A-class areas. Market cap rates: 4-5% in San Francisco, 8-10% in Cleveland. Why you compare cap rates within the same market, not across markets. How to spot mispriced deals — cap rate higher than market = potential bargain."),
                    ("Cash-on-Cash Return: The Real Investor Number", "Cap rate ignores financing. Cash-on-Cash = annual cash flow divided by total cash you put in (down payment + closing costs + initial repairs). Real example: $250k property, $50k down, $10k closing, $5k repairs = $65k in. Cash flow of $6,500/year = 10% cash-on-cash. The metric that tells you what your actual money is doing. Target 8-12% for most markets, lower in expensive coastal cities where appreciation does the heavy lifting."),
                    ("GRM, 1% Rule, 50% Rule — Quick Screening Filters", "GRM (Gross Rent Multiplier) = price / annual gross rent. Lower is better. Under 10 GRM = strong cash flow market. 1% Rule = monthly rent should be 1% of purchase price (a $200k property should rent for $2,000+). Increasingly rare in 2024. 50% Rule = expenses will be 50% of gross rent over the long run. Used to sanity-check pro formas. None are gospel — they're filters to decide what's worth deeper underwriting."),
                    ("DSCR and How Lenders See the Deal", "Debt Service Coverage Ratio = NOI / annual debt service. A 1.25 DSCR means the property's income covers the mortgage 1.25x. Most investor lenders require 1.20-1.25 minimum. Real example: $24k NOI / $18k annual mortgage = 1.33 DSCR — fundable. DSCR loans qualify the property, not you — you can buy 5 rentals on DSCR even if your W-2 income is modest. Why this metric unlocks scaling."),
                    ("IRR (Internal Rate of Return) — The Long-Game Metric", "IRR rolls all cash flows + appreciation + principal paydown + tax benefits into one annualized return number over the hold period. A property might show 8% cash-on-cash but IRR over 10 years could be 18% once you factor in appreciation and paydown. How to calculate IRR in Excel/Sheets (=IRR function). Real example over 10-year hold showing how cash-on-cash and IRR diverge. Why sophisticated investors think in IRR."),
                    ("The BRRRR Math: Buy, Rehab, Rent, Refi, Repeat", "Buy a beat-up house cheap. Renovate it. Rent it. Refinance based on new higher value. Pull out most or all of your original cash. Repeat. Real example: buy $120k, rehab $40k, all-in $160k. Property now worth $230k. Refi at 75% LTV = $172k loan. You pulled out $12k MORE than you put in AND you own a cash-flowing rental. The math fails when ARV is too low, rehab costs blow up, or rates rise — the 3 ways most BRRRR deals die."),
                    ("Sensitivity Analysis: Stress-Testing Your Deal", "Build the deal at base case, then run scenarios: rent drops 10%, vacancy hits 15%, expenses spike 20%, rate jumps 1%. If the deal still breaks even at all four stresses, it's bulletproof. If it loses money on any one, you're betting on perfect conditions. Real spreadsheet walkthrough showing how a 'great' deal becomes a money loser when one variable shifts. Why this single habit separates pros from amateurs."),
                    ("Break-Even Occupancy and Margin of Safety", "Break-even occupancy = the occupancy rate where cash flow hits zero. If your break-even is 65% and the market vacancy is 5%, you have a 30-point margin of safety. If break-even is 92% and market vacancy is 5%, you have almost no cushion — one tenant leaving wipes you out. How to calculate it: divide total fixed costs (mortgage + fixed expenses) by gross rent. Always know this number before closing."),
                    ("Capex Reserve: The Number Most Beginners Skip", "Capital expenditures = big-ticket replacements over the property's life: roof ($15k every 25 years), HVAC ($8k every 15 years), water heater ($1.5k every 12 years), windows ($10k every 30 years), kitchen ($15k every 20 years). Add them up, divide by lifespan, save monthly. Typical reserve: 5-10% of rent. Beginners who skip this look profitable for 3 years, then a roof eats their entire 'profit' in one weekend."),
                    ("Building Your Own Underwriting Spreadsheet", "Walk-through of a clean pro forma template: inputs tab (price, rent, vacancy %, expenses, loan terms), calculations tab (NOI, cash flow, all returns), outputs tab (cap rate, CoC, IRR, DSCR, break-even). Why building it yourself in Excel/Sheets beats apps and calculators — you understand every number. Free templates from BiggerPockets to start. The 30-minute deal screening workflow once your spreadsheet is dialed."),
                ],
            },
            {
                "section": 6,
                "title": "Renting & Property Management",
                "lessons": [
                    ("Setting the Right Rent", "Pull rental comps the same way you pull sales comps. Tools: Zillow Rentals, Rentometer, local Facebook groups, Craigslist. Adjust for differences (your unit has in-unit laundry = +$50). The market rent vs strategic rent question: pricing slightly under market reduces vacancy and gets quality tenants faster. Real example: $1,800 listed vs $1,750 listed — the lower one rented in 4 days vs 18 days, netting more annual income."),
                    ("Tenant Screening: The Make-or-Break Step", "A bad tenant costs $5k-$20k in damage, lost rent, and eviction fees. Screening: pull credit (TransUnion SmartMove ~$25), criminal background, eviction history, employment verification (call employer, not just paystubs), landlord references (especially the one BEFORE current — current may lie to get them out). Income rule: gross monthly income 3x monthly rent minimum. Why a thorough screen takes 2 hours and saves you years of pain."),
                    ("Writing a Strong Lease", "Key clauses: monthly rent + due date + late fees, security deposit terms, who pays utilities, pet policy + pet deposit, maintenance responsibility split, lawn/snow, smoking, subletting, early termination penalty, renter's insurance requirement, inspection rights. State-specific requirements (caps on deposits, notice periods). Use your state association's standard lease as a baseline — don't write from scratch. Why a tight lease is your legal armor."),
                    ("The Move-In Inspection and Documentation", "Walk through with the tenant on move-in day. Photograph EVERY wall, floor, appliance, ceiling, window — date-stamped. Both parties sign a condition report. Why: when they move out and there's a dispute over the deposit, your photos are the only thing that matters in small claims court. Repeat the same documentation on move-out. Without this, you lose the security deposit dispute 100% of the time."),
                    ("Evictions: The Process and the Cost", "Eviction = the legal process to remove a non-paying or violating tenant. Steps: serve a notice (3-10 days depending on state and reason), file with the court if they don't comply, court hearing (30-60 days), sheriff lockout if you win. Total time: 2-6 months in tenant-friendly states (CA, NY), 3-6 weeks in landlord-friendly (TX, FL). Total cost: $2k-$8k in legal fees + lost rent + damage. Why screening matters so much."),
                    ("Property Management Companies vs Self-Managing", "PM companies charge 8-10% of gross rent + leasing fee (1 month rent per new tenant). They handle tenant calls, repairs, rent collection, evictions. Worth it when: you own 5+ doors, you live far away, you're scaling, you hate tenant calls. Self-manage when: you own 1-3 local properties and want to maximize cash flow. Real numbers showing how PM eats $2,400/year on a $2k/month rental — sometimes worth it, sometimes not."),
                    ("Section 8 and Subsidized Tenants", "Section 8 is the federal housing voucher program. Government pays 60-100% of the rent directly to the landlord. Pros: guaranteed rent, often above-market in C/D areas, tenants stay long-term. Cons: annual inspections from housing authority, slower payment startup (60-90 days), more administrative work. How to get approved as a landlord. Why Section 8 properties dominate cash flow in working-class neighborhoods."),
                ],
            },
            {
                "section": 7,
                "title": "Selling & Exits",
                "lessons": [
                    ("When to Sell vs Hold", "Sell when: market is at cyclical peak (rare to time), property is underperforming and won't recover, you need to redeploy capital to better deals, life event forces it. Hold when: cash flow positive, in path of growth, locked in low-interest rate that you can't replace. The math: every year held, principal paydown + appreciation + cash flow stack. Selling resets the clock. Most pros under-sell, not over-sell."),
                    ("Listing With an Agent vs FSBO", "Agent route: 5-6% commission ($15-$18k on a $300k sale), but they handle marketing, pricing, showings, negotiation, paperwork, and they have MLS access (where 90% of buyers are). FSBO: you save commission but stat shows FSBO homes sell for ~6% less on average — wash. When FSBO makes sense: hot seller's market, you have a buyer lined up (neighbor, family), unique buyer pool. Flat-fee MLS services as middle ground ($300-$500)."),
                    ("Pricing and Staging Strategy", "Price slightly below comps in a buyer's market (drives traffic, creates urgency). Price at comps with room to negotiate in a balanced market. Price slightly above comps in a hot seller's market (multiple offers will bid up). Staging: empty rooms feel smaller than staged ones. Pro stagers $1k-$5k, rental furniture $500-$2k/month. Photographs are everything — pro photos add $5k+ to sale price. Bad photos kill the listing in 48 hours."),
                    ("1031 Exchange: The Tax Magic", "Section 1031 lets you sell an investment property and roll all the gains into a new investment property — deferring all capital gains taxes. Real example: sell for $500k with $200k gain, would owe $50k+ tax. Do a 1031 instead, buy a $700k property with the proceeds, defer the entire tax bill. Strict rules: 45 days to identify replacement, 180 days to close, must use a Qualified Intermediary (cannot touch the cash). How serious investors compound wealth tax-free for decades."),
                    ("Capital Gains, Depreciation Recapture, and the Real Tax Bill", "Capital gains: 0%, 15%, or 20% depending on income (held over 1 year). Short-term: taxed as ordinary income. Depreciation recapture: when you sell, the IRS claws back the depreciation you wrote off, taxed up to 25%. Real example: $300k purchase, depreciated $80k over 10 years, sold for $500k. Long-term gain on $200k + recapture on $80k = real tax bill ~$50k-$70k. Why depreciation is a deferral, not free money."),
                ],
            },
            {
                "section": 8,
                "title": "Advanced Strategies",
                "lessons": [
                    ("Wholesaling: Flipping Contracts Not Houses", "Wholesaler finds a deeply discounted property, puts it under contract at $150k, assigns the contract to a flipper for $165k, pockets $15k without ever owning the property. No money, no credit, no rehab needed — just deal-finding skill. Marketing methods: direct mail, cold calling, bandit signs, driving for dollars. The grind: 100 leads to find 1 deal. Why it's the lowest barrier to entry in RE and the easiest to fail at."),
                    ("Syndications: Investing in Big Deals With Other People's Money", "A syndication is when a sponsor (operator) raises money from passive investors (LPs) to buy a big property — usually a 50+ unit apartment building. LPs put in $50k-$100k each, sponsor manages, profits split (typically 70/30 after preferred return). LPs are hands-off, get K-1s, target 15-20% IRR. How to vet a sponsor (track record, deal structure, fees). Why this is how people invest in $20M deals with $50k."),
                    ("REITs and Real Estate Stocks", "Real Estate Investment Trusts are publicly traded companies that own real estate portfolios. Buy shares on the stock market, get dividends from rent income, capture appreciation when share price rises. No property management headache, fully liquid (sell anytime), low minimum ($1 of stock). Tradeoffs: lower returns than direct ownership, no leverage advantage, no tax benefits, no control. Good for liquidity and diversification."),
                    ("Note Investing: Being the Bank", "Instead of buying property, you buy the mortgage note — the debt secured by the property. Performing notes: you collect monthly payments at 7-10% yield. Non-performing notes: you buy them at 30-60 cents on the dollar and either work out a modification with the borrower or foreclose and own the property at a deep discount. Where notes are bought: Paperstac, online marketplaces, banks selling pools. Why this is a quietly massive game."),
                    ("Tax Liens and Tax Deeds", "When owners don't pay property tax, the county auctions off either the tax lien (right to collect the debt + interest) or the tax deed (the actual property). Lien states pay 8-36% interest. Deed states give you the property for the unpaid tax (often pennies on the dollar). The catch: research, redemption periods, title problems. Florida and Arizona = popular lien states. Texas and California = deed states. How to start with $500 at an auction."),
                    ("Opportunity Zones", "Designated low-income census tracts where investors get massive tax breaks for investing capital gains in real estate or businesses there. Deferral of original gain until 2026, plus 10% reduction if held 5 years, plus zero tax on new gains if held 10 years. Real example: $500k gain from selling stock invested in an OZ project = potentially $200k tax savings. The dark side: gentrification debate, illiquid investments, deal quality varies wildly."),
                ],
            },
            {
                "section": 9,
                "title": "Predicting Markets & Crisis Points",
                "lessons": [
                    ("Leading Indicators That Markets Are Topping", "Signals to watch: price-to-income ratio above 7-8x (median home price vs median household income), price-to-rent ratio above 25, days-on-market dropping under 10, mortgage applications hitting record highs, lending standards loosening (low-down-payment loans, no-doc loans coming back), media headlines turning euphoric ('housing always goes up'). When 3+ of these all hit simultaneously, you're near a top. How to track each one for free."),
                    ("Anatomy of the 2008 U.S. Housing Crash", "Cause chain: low rates (2003) → cheap money → subprime lending explosion (2005) → liar loans, no-down-payment, NINJA loans → builders overbuilt → rates rose → ARMs reset → defaults spiked → foreclosures flooded the market → prices collapsed 30-60% nationwide. Lessons: when banks stop verifying income, panic. When prices double in 3 years with no income growth, panic. Real numbers, real timeline, what the warnings looked like in real time."),
                    ("Canada's Housing Bubble — Case Study", "Toronto and Vancouver: home prices up 300%+ from 2000-2022. Household debt-to-income at world-leading 180%+. Price-to-income ratios over 12x in major cities — among the worst in the developed world. Foreign capital inflows from Asia drove speculation. What unwound it: rate hikes 2022-2023, prices dropped 15-25% in 12 months. Why someone who sold their Toronto condo in 2022 and rented could buy back the same condo 25% cheaper today with way more cash."),
                    ("Australia, China, and Other Bubbles to Learn From", "Australia: similar to Canada, Sydney/Melbourne unaffordable, high household debt, banking system exposed. China: Evergrande collapse (2021), $300B in liabilities, entire ghost cities, real estate was 30% of GDP. Why they matter: same warning signs as Canada and many U.S. markets. Spotting overvaluation: rent-to-price below 3%, supply outpacing population growth, government distortions (subsidies, low rates) propping prices."),
                    ("How to Profit From a Predicted Crash", "If you correctly call a top and own appreciated property: sell, bank the cash, rent for 1-2 years through the crash, then buy back 20-40% cheaper with a much bigger nest egg. Real math: sell $800k house, rent for $3k/month, market drops 25%, buy a $600k equivalent 2 years later with $200k of new equity created out of thin air. Risks: timing is brutally hard, transaction costs (6%+ each way), tax on gains, you might be wrong and miss further appreciation."),
                    ("Contrarian Buying: When to Buy at the Bottom", "Signals it's a bottom: foreclosures peaking and stabilizing, days-on-market over 90, price-to-rent ratio under 15, builders bankrupt, media headlines doom-laden ('housing is dead'), cap rates blowing out to 10%+. Real examples: buying Phoenix in 2011, Detroit in 2013, Las Vegas in 2012 — properties bought for $80k now worth $400k+. Why most people can't pull the trigger when assets are cheap, and how to train yourself to."),
                ],
            },
            {
                "section": 10,
                "title": "Global Markets — Specific Locations",
                "lessons": [
                    ("Dubai: How the Market Actually Works", "Dubai allows foreigners to own freehold property in designated zones (Downtown, Marina, Palm, JBR, Dubai Hills, etc). No income tax, no property tax, no capital gains. 4% Dubai Land Department fee at purchase. Prices recovered from 2014-2019 slump and exploded post-2020 with Russian/Indian/Chinese capital. Golden Visa: invest 2M AED ($545k) in property = 10-year residency. Risks: oversupply cycles (massive off-plan pipeline), illiquid in downturns, currency pegged to USD. Rental yields 5-8% in mid-market areas."),
                    ("Baku and Azerbaijan Real Estate", "Baku market split into central (Yasamal, Nasimi, Sabail, Narimanov) and outer (Khatai, Binagadi, Surakhani). Prices in central Baku rose sharply 2020-2024 — driven by oil wealth, Karabakh reconstruction spending, and Russians/Iranians relocating. Average city center: $1,500-$2,500/sqm. Rental yields 6-9%. Currency risk minimal (manat pegged to USD). Foreign ownership: allowed for residential, restricted for land. Buying process is fast (10-30 days), notary-driven. Common gotchas: unfinished buildings, gray-market documentation, agent commissions of 2-3% each side."),
                    ("Seabreeze and Coastal Azerbaijan", "Seabreeze on the Absheron peninsula — Pasha Holding's flagship resort-town development. Mix of villas, apartments, hotels, marinas. Prices $2,500-$5,000+/sqm (premium for sea-facing). Use cases: second home for Baku families, short-term rental (Airbnb yields 8-12% in summer season, near-zero off-season), pre-construction speculation. Other coastal options: Bilgah, Mardakan, Pirshagi — older established weekend areas at $800-$1,500/sqm. The Karabakh angle: massive government infrastructure investment, long-term tourism play. Risks: seasonality, oversupply in luxury segment, exit liquidity."),
                    ("Istanbul, Turkey", "Largest market in Turkey, split into European side (Beyoglu, Sisli, Besiktas, Sariyer) and Asian side (Kadikoy, Uskudar, Atasehir). Prices in USD have been chaotic due to lira collapse — locals price in foreign currency, foreigners get hit by lira swings on exit. Citizenship by investment: $400k property = Turkish passport. Massive driver of foreign demand 2018-2023. Rental yields 3-7% in central districts. Risks: earthquake exposure (1999 + ongoing fault concerns), regulatory shifts on foreign ownership, lira inflation eating returns."),
                    ("Antalya and Turkish Coast", "Antalya, Alanya, Bodrum, Fethiye — coastal Mediterranean property. Heavy Russian, Iranian, German, British, Scandinavian buyer base. Prices $800-$2,500/sqm for apartments, more for villas. Short-term rental yields excellent in summer (10-15%), terrible off-season. Used heavily for Turkish citizenship investment ($400k threshold) since it's cheaper than Istanbul. Risks: extreme seasonality, oversupply in Alanya, lira issues, builder quality varies wildly between developers."),
                    ("London, UK", "Prime central London (Mayfair, Belgravia, Kensington, Chelsea) — global trophy assets, $3,000-$8,000/sqft. Prime outer (Notting Hill, Marylebone, Hampstead) — $1,500-$3,000/sqft. Mass market (zones 2-5) — $700-$1,500/sqft. Stamp duty brutal for foreigners (up to 17% on purchase). Leasehold vs freehold trap (most flats are leasehold — when lease drops under 80 years, value tanks). Rental yields 3-4% prime, 5-6% outer. Why London is for capital preservation and currency hedge, not cash flow."),
                    ("Miami, NYC, and Top U.S. Coastal Cities", "Miami: no state income tax, massive 2020-2023 boom from NY/CA migration, condo market dominated by foreigners. Insurance crisis ongoing (premiums tripled). NYC: highest property taxes, rent stabilization complications, condo vs co-op distinction (co-ops require board approval, lower prices). LA/SF: rent control, eviction protections that make landlords' lives hard, but appreciation dwarfs cash flow. Why high-tax states are still where appreciation lives long-term."),
                    ("Singapore, Tokyo, and Asian Markets", "Singapore: world's most expensive market by some measures, foreigners hit with 60% Additional Buyer's Stamp Duty as of 2023 — basically a no-go for foreign investment now. Tokyo: cheap by global standards ($500-$1,500/sqft central), low yields (3-4%), buildings depreciate (unlike land), population shrinking long-term but Tokyo proper still growing. Bangkok and Kuala Lumpur as cheaper Asian entry points. Currency risk dominates all returns."),
                ],
            },
            {
                "section": 11,
                "title": "Legal, Tax, Risk",
                "lessons": [
                    ("LLCs and Asset Protection", "Holding each rental in its own LLC means a tenant lawsuit can only reach that one property's equity, not your other assets. Setup cost: $100-$800 per state. Annual fees: $0-$800/state. Cons: harder to get conventional financing (most banks won't lend to LLCs), umbrella insurance often gives similar protection at lower hassle. When to use each: LLCs for higher-value or commercial properties, umbrella policy for small SFH portfolios."),
                    ("Insurance: Beyond Basic Homeowner's", "Landlord policy (replaces homeowner's for rentals): $800-$2,500/year typical. Liability coverage $1-2M minimum. Umbrella policy: $300-$500/year for $1M extra coverage that stacks on top of all your other policies. Flood insurance: separate from main policy, required in flood zones. Vacant property insurance: when a unit is empty 30+ days, regular policy may not cover it. Specific coverage gaps that wreck landlords (water backup, ordinance & law, loss of rents)."),
                    ("Depreciation: The Best Tax Benefit in the Country", "IRS lets you depreciate residential property over 27.5 years and commercial over 39 years. Real example: $300k property (minus $50k land) = $250k depreciable basis / 27.5 = $9,090/year deduction against rental income. Often eliminates your taxable rental income on paper while you collect cash flow. Why a profitable rental can show a 'loss' on taxes legally. Recapture on sale brings it back (covered in Selling section)."),
                    ("Cost Segregation: Turbocharging Depreciation", "Standard depreciation spreads $250k over 27.5 years. Cost seg study (~$3k-$8k) reclassifies components: appliances, flooring, lighting, parking lot, landscaping into 5/7/15-year schedules. Bonus depreciation lets you take big chunks year one. Real example: a $1M property cost seg can generate $200k-$300k of year-one deductions for a high-income investor. Why this is the rich person's tax cheat code and how it works at smaller scales too."),
                    ("Lawsuits, Slip-and-Falls, and the Worst-Case Scenarios", "Tenant suing for unsafe conditions (lead paint, mold, code violations) = $50k-$500k judgments. Contractor injured on your property without workers comp coverage = personal liability. Discrimination lawsuits (fair housing violations) — even unintentional language in listings can trigger. ADA accessibility issues in commercial. How to actually protect yourself: documentation, written maintenance logs, insurance, professional property management as a buffer, never act as your own contractor on rentals."),
                ],
            },
            {
                "section": 12,
                "title": "Construction",
                "lessons": [
                    ("Construction Industry Basics", "General Contractor (GC) = manages the whole job, hires and coordinates subs. Subcontractors (subs) = specialists: framing, electrical, plumbing, HVAC, drywall, roofing, painting, finish carpentry. Architect designs, engineer ensures structural integrity, inspector checks code compliance. Materials suppliers, equipment rental companies. How a typical residential build flows: design → permits → site prep → foundation → framing → mechanicals → drywall → finishes → inspections → CO (certificate of occupancy). Real timeline: 6-12 months for a SFH."),
                    ("Estimating and Bidding a Job", "Estimating = figuring out what a job will cost. Components: materials (square footage + cost per unit), labor (hours × hourly rate + burden), equipment, permits, overhead (insurance, office, management), profit margin (15-25% typical). Bid = your price to the customer. Real example: estimating a kitchen remodel: $8k cabinets + $4k counters + $2k appliances + $3k labor + $1k permits + $4k overhead/profit = $22k bid. Why most beginners underbid and lose money."),
                    ("Reading Blueprints and Plans", "Plan view (top-down), elevations (side views), sections (cutaway), details (close-ups of specific elements). Scales (1/4 inch = 1 foot residential). Symbols for doors, windows, electrical, plumbing, HVAC. Specs/schedules listing materials, fixtures, hardware. How to spot conflicts and missing info before the job starts. Why 'measure twice, build once' starts with understanding the drawings."),
                    ("Project Management and Scheduling", "Critical Path Method: which tasks must finish before others can start (foundation before framing, framing before mechanicals). Gantt charts. Buffer days between trades. Coordinating multiple subs so they don't trip over each other or sit idle. The biggest construction killer: trades waiting on other trades. Real schedule for a SFH build week-by-week. Software: Buildertrend, CoConstruct, even Google Sheets."),
                    ("Permits and Working With Inspectors", "Most work requires permits: structural changes, electrical, plumbing, HVAC, additions. Cosmetic work (paint, flooring, cabinets without moving plumbing) usually doesn't. Permit process: submit plans, pay fees, get approved, schedule inspections at each phase. Inspectors check: footing, framing, rough mechanical, insulation, final. Working with them: be respectful, have plans on site, fix issues immediately. Working without permits = denied insurance claims, forced demolition, fines."),
                    ("Ground-Up Build Walkthrough", "Phase 1: land acquisition, due diligence, soil testing, survey. Phase 2: design and permits (3-6 months). Phase 3: site prep — clearing, grading, utilities, driveway. Phase 4: foundation — excavation, footings, walls, slab. Phase 5: framing — floors, walls, roof. Phase 6: mechanicals rough-in — electrical, plumbing, HVAC. Phase 7: insulation and drywall. Phase 8: finishes — flooring, cabinets, fixtures, paint. Phase 9: final inspections and CO. Total: 8-14 months for a SFH. Real cost breakdown per phase."),
                    ("Renovations and Flips: Where Construction Meets RE", "Light cosmetic flip: paint, flooring, fixtures = $15k-$30k for a typical 1,500 sqft house. Mid-level: + kitchen + bathrooms = $40k-$80k. Heavy: + layout changes + roof + mechanicals = $80k-$200k. Where flippers blow budget: foundation issues, electrical updates required by code, mold/asbestos remediation, permit delays. The 70% rule: max purchase = 70% × ARV - rehab cost. Why most flips don't make money — beginners underestimate rehab by 40%."),
                    ("Change Orders and Scope Creep", "A change order = customer changes their mind mid-job. 'Can we move that wall' = $5k. 'Can we upgrade the cabinets' = $8k. Every change costs time and money. Always document in writing, get the customer to sign, get paid before doing the work. The #1 way GCs lose money: doing change orders verbally and then arguing over the bill. Real templates for change order forms. Why scope creep without documentation = lawsuits."),
                    ("Draw Schedules and Getting Paid", "On big jobs, you don't get paid all at once. Draw schedule: percentages tied to milestones. Typical residential: 10% at signing, 20% at foundation, 25% at framing, 25% at drywall, 15% at finishes, 5% at final inspection. Why mismanaging draws bankrupts contractors: you spend the draw on the current phase but don't budget for the next, then run out of cash mid-build. Cash flow management is harder than the actual building."),
                    ("Starting a Construction Business", "Capital needs: $20k-$50k to start small (truck, tools, insurance, first job). Licenses: most states require a contractor license (exam + bond + insurance). General liability insurance $1k-$3k/year minimum. Workers comp required if you have employees. Marketing: Google ads, neighborhood Facebook groups, door knocking, referral relationships with realtors. Pricing for profit: 50% gross margin minimum. The path: handyman → finish carpenter → GC of small jobs → GC of bigger jobs → developer building your own projects."),
                ],
            },
        ],
    },
]

LESSON_SYSTEM_PROMPT = """You are a financial and business education teacher for someone who grew up without financial education and is learning how wealth and money actually work for the first time.

Your job is to teach the lesson topic below in a way that is:
- Written in plain, everyday language — no jargon, no complicated finance words unless you immediately explain them in simple terms
- Extremely detailed and thorough — do not give a high-level overview, walk through every step and every mechanism
- Full of real examples with real numbers — dollar amounts, percentages, timelines, actual scenarios
- Honest about risks and what goes wrong, not just the success story
- Written like a smart older brother or mentor explaining something over the table, not a textbook
- Long enough to actually teach the topic — do not rush, do not summarize, explain everything

Structure each lesson like this:
1. Start with one sentence on what this lesson is about and why it matters
2. Explain the concept from scratch as if the person has never heard of it
3. Walk through at least one real detailed example with actual numbers
4. Explain the risks or common mistakes people make
5. End with 1-2 sentences on how this connects to building actual wealth

Do not use bullet points for the main explanation — write in flowing paragraphs that feel like a real explanation from a person who knows this well."""


def _iter_lessons(module):
    """Yield (section_num, section_title, lesson_num, title, topic) for every lesson in a module.
    Flat modules use section_num=0. Sectioned modules use real section numbers.
    """
    if "sections" in module:
        for section in module["sections"]:
            s = section["section"]
            stitle = section["title"]
            for i, (title, topic) in enumerate(section["lessons"]):
                yield s, stitle, i + 1, title, topic
    else:
        for i, (title, topic) in enumerate(module["lessons"]):
            yield 0, "", i + 1, title, topic


def _module_lesson_count(module):
    if "sections" in module:
        return sum(len(s["lessons"]) for s in module["sections"])
    return len(module["lessons"])


def _get_progress() -> set:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT module_num, section_num, lesson_num FROM curriculum_progress")
    completed = {(r["module_num"], r["section_num"], r["lesson_num"]) for r in cur.fetchall()}
    cur.close()
    conn.close()
    return completed


def _mark_complete(module_num: int, section_num: int, lesson_num: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO curriculum_progress (module_num, section_num, lesson_num) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        (module_num, section_num, lesson_num),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_next_lesson():
    """Returns (module_num, section_num, section_title, lesson_num, title, topic) or None."""
    completed = _get_progress()
    for module in CURRICULUM:
        m = module["module"]
        for s, stitle, l, title, topic in _iter_lessons(module):
            if (m, s, l) not in completed:
                return m, s, stitle, l, title, topic
    return None


def get_current_lesson():
    completed = _get_progress()
    last = None
    for module in CURRICULUM:
        m = module["module"]
        for s, stitle, l, title, topic in _iter_lessons(module):
            if (m, s, l) in completed:
                last = (m, s, stitle, l, title, topic)
    if last:
        return last
    return get_next_lesson()


def get_status() -> str:
    completed = _get_progress()
    total_lessons = sum(_module_lesson_count(m) for m in CURRICULUM)
    lines = [f"Curriculum progress: {len(completed)}/{total_lessons} lessons completed.\n"]
    for module in CURRICULUM:
        m = module["module"]
        total = _module_lesson_count(module)
        done = sum(1 for s, _, l, _, _ in _iter_lessons(module) if (m, s, l) in completed)
        status = "complete" if done == total else f"{done}/{total}"
        lines.append(f"Module {m}: {module['title']} — {status}")
        if "sections" in module:
            for section in module["sections"]:
                s = section["section"]
                stotal = len(section["lessons"])
                sdone = sum(1 for i in range(stotal) if (m, s, i + 1) in completed)
                sstatus = "complete" if sdone == stotal else f"{sdone}/{stotal}"
                lines.append(f"  Section {s}: {section['title']} — {sstatus}")
    return "\n".join(lines)


def _build_prompt(m, s, stitle, l, title, topic, module_title, total_in_group, group_label):
    if s == 0:
        location = f"Module {m}: {module_title}\nLesson {l} of {total_in_group}: {title}"
    else:
        location = f"Module {m}: {module_title}\nSection {s}: {stitle}\nLesson {l} of {total_in_group} in this section: {title}"
    return f"{location}\n\nTopic to teach:\n{topic}"


def _build_header(m, s, stitle, l, title, module_title, total_in_group):
    if s == 0:
        return f"Module {m} — {module_title}\nLesson {l}/{total_in_group}: {title}\n\n"
    return f"Module {m} — {module_title}\nSection {s}: {stitle}\nLesson {l}/{total_in_group}: {title}\n\n"


def _find_module(m):
    return next((mod for mod in CURRICULUM if mod["module"] == m), None)


def _section_lesson_count(module, section_num):
    if "sections" not in module:
        return len(module["lessons"])
    section = next((s for s in module["sections"] if s["section"] == section_num), None)
    return len(section["lessons"]) if section else 0


async def deliver_next_lesson(mark_done: bool = True) -> str:
    nxt = get_next_lesson()
    if not nxt:
        return "You've completed the entire curriculum. Seriously impressive — feel free to ask me anything about any topic to go deeper."

    m, s, stitle, l, title, topic = nxt
    module = _find_module(m)
    module_title = module["title"] if module else ""
    total_in_group = _section_lesson_count(module, s) if s else len(module["lessons"])

    prompt = _build_prompt(m, s, stitle, l, title, topic, module_title, total_in_group, "")

    lesson_text = await chat(messages=[
        {"role": "system", "content": LESSON_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])

    if mark_done:
        _mark_complete(m, s, l)

    header = _build_header(m, s, stitle, l, title, module_title, total_in_group)
    return header + lesson_text


async def deliver_current_lesson() -> str:
    current = get_current_lesson()
    if not current:
        return "No lessons started yet. Say 'next lesson' to begin."

    m, s, stitle, l, title, topic = current
    module = _find_module(m)
    module_title = module["title"] if module else ""
    total_in_group = _section_lesson_count(module, s) if s else len(module["lessons"])

    prompt = _build_prompt(m, s, stitle, l, title, topic, module_title, total_in_group, "")

    lesson_text = await chat(messages=[
        {"role": "system", "content": LESSON_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])

    header = _build_header(m, s, stitle, l, title, module_title, total_in_group)
    return header + lesson_text
