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


def _get_progress() -> dict:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT module_num, lesson_num FROM curriculum_progress ORDER BY module_num, lesson_num")
    completed = {(r["module_num"], r["lesson_num"]) for r in cur.fetchall()}
    cur.close()
    conn.close()
    return completed


def _mark_complete(module_num: int, lesson_num: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO curriculum_progress (module_num, lesson_num) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (module_num, lesson_num),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_next_lesson() -> tuple[int, int, str, str] | None:
    completed = _get_progress()
    for module in CURRICULUM:
        m = module["module"]
        for i, (title, topic) in enumerate(module["lessons"]):
            l = i + 1
            if (m, l) not in completed:
                return m, l, title, topic
    return None


def get_current_lesson() -> tuple[int, int, str, str] | None:
    completed = _get_progress()
    last = None
    for module in CURRICULUM:
        m = module["module"]
        for i, (title, topic) in enumerate(module["lessons"]):
            l = i + 1
            if (m, l) in completed:
                last = (m, l, module["lessons"][i][0], module["lessons"][i][1])
    if last:
        return last
    return get_next_lesson()


def get_status() -> str:
    completed = _get_progress()
    total_lessons = sum(len(m["lessons"]) for m in CURRICULUM)
    lines = [f"Curriculum progress: {len(completed)}/{total_lessons} lessons completed.\n"]
    for module in CURRICULUM:
        m = module["module"]
        done = sum(1 for i in range(len(module["lessons"])) if (m, i + 1) in completed)
        total = len(module["lessons"])
        status = "complete" if done == total else f"{done}/{total}"
        lines.append(f"Module {m}: {module['title']} — {status}")
    return "\n".join(lines)


async def deliver_next_lesson(mark_done: bool = True) -> str:
    next_lesson = get_next_lesson()
    if not next_lesson:
        return "You've completed the entire curriculum. Seriously impressive — feel free to ask me anything about any topic to go deeper."

    m, l, title, topic = next_lesson
    module_title = next((mod["title"] for mod in CURRICULUM if mod["module"] == m), "")
    total_in_module = len(next((mod["lessons"] for mod in CURRICULUM if mod["module"] == m), []))

    prompt = f"Module {m}: {module_title}\nLesson {l} of {total_in_module}: {title}\n\nTopic to teach:\n{topic}"

    lesson_text = await chat(messages=[
        {"role": "system", "content": LESSON_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])

    if mark_done:
        _mark_complete(m, l)

    header = f"Module {m} — {module_title}\nLesson {l}/{total_in_module}: {title}\n\n"
    return header + lesson_text


async def deliver_current_lesson() -> str:
    current = get_current_lesson()
    if not current:
        return "No lessons started yet. Say 'next lesson' to begin."

    m, l, title, topic = current
    module_title = next((mod["title"] for mod in CURRICULUM if mod["module"] == m), "")
    total_in_module = len(next((mod["lessons"] for mod in CURRICULUM if mod["module"] == m), []))

    prompt = f"Module {m}: {module_title}\nLesson {l} of {total_in_module}: {title}\n\nTopic to teach:\n{topic}"

    lesson_text = await chat(messages=[
        {"role": "system", "content": LESSON_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])

    header = f"Module {m} — {module_title}\nLesson {l}/{total_in_module}: {title}\n\n"
    return header + lesson_text
