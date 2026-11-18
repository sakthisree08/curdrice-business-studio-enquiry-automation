# Demo Script (about 4–5 minutes)

**Before recording**
- Start fresh: delete `database\enquiries.db` (it is recreated automatically).
- Run `streamlit run app.py`. If you have an API key, make sure the green **Live AI mode** banner is showing. Otherwise the demo works in mock mode (say so on camera).
- Optional: start the API in a second terminal (`uvicorn api:app --port 8000`) and keep <http://127.0.0.1:8000/docs> open in a tab.
- Zoom the browser to about 110% so the text is readable in the recording.

> Numbers below are from demo mode. In live AI mode the category, priority and review status should match; the wording of extracted fields and replies will differ slightly. Read the numbers from your screen.

---

### 0:00 – Introduction (20 s)
> "Hi, I'm Mounika. This is my AI-Powered Business Enquiry Automation System for Curd Rice Business Studio. It takes a customer enquiry in plain language, extracts the key information, classifies it, scores the lead with transparent business rules, recommends the next best action, drafts a safe reply, flags anything that needs a human, and stores it all in SQLite. One important design choice: the LLM does the language work, but every business decision, like the score, the priority and the review flag, is made by Python rules I can explain."

*Point at the mode banner:* "This banner shows whether it's using live OpenAI or the built-in demo engine. If the API ever fails, it falls back automatically and says so."

### 0:40 – Enquiry 1: High-value lead (002) (50 s)
*Select sample **002** from the dropdown → **Process enquiry**.*
1. **Input:** "Need a website for our manufacturing company. Budget is ₹2 lakh. Can we discuss this week?"
2. **Classification:** "Website Development."
3. **Extracted info** *(open the tab)*: "It picked up the industry, manufacturing, the budget, ₹2 lakh, and the timeline, this week. Company name and email are *Not mentioned*. It doesn't make them up."
4. **Lead score / priority:** "83 out of 100, **High**." *(Open Score breakdown.)* "Here's exactly why: 25 for buying intent, 20 for a clear requirement, 15 for the budget, 10 for urgency, and so on. The explanation sentence is generated from these same factors."
5. **Response draft:** "It thanks them, acknowledges *their* budget, and asks targeted questions. No price, no delivery date."
6. **Human review:** "No special review needed. It's still only a draft."
7. **Database:** "Saved as enquiry #1. You can see the ID up here."

### 1:30 – Innovation: Next Best Action (40 s)
*Open the **Next best action** tab on the same result.*
> "This is my innovation. A score says how good a lead is, but not what to do. The Next Best Action tells the team: schedule a discovery call, owner Sales, urgency High, internal target 24 hours. That target is internal; we never promise it to the customer. It also lists what's still missing, like company name, contact details, and website-specific things like whether they already have a domain. Those exact questions are inserted into the reply draft automatically, so our very first email collects what sales needs and saves a whole round of back-and-forth."

### 2:10 – Enquiry 2: Pricing request (007) (30 s)
*Load **007** → Process.*
> "'Please send your pricing details.' The business rule says never invent pricing. The category is General Enquiry, Low priority, because there's no concrete requirement yet. Look at the draft: it explains that pricing depends on scope and asks what they need. On top of the prompt, every AI draft goes through a guardrail that scans for currency amounts, guarantees and timeframes. If the AI ever writes '₹25,000' or 'delivered in 2 weeks', the draft is replaced with a safe template and flagged."

### 2:40 – Enquiry 3: Complaint (012) (35 s)
*Load **012** → Process.*
> "'I am unhappy with the service received and need someone to call me urgently.' Here's the red **HUMAN REVIEW REQUIRED** banner, with the reasons: it's a complaint and the sentiment is negative. The lead score is low because it isn't a sales opportunity, but the Next Best Action urgency is **Critical**: escalate to the account manager and call within 2 hours. So I keep *value* and *urgency* separate. The draft apologises and promises nothing beyond escalation."

### 3:15 – Enquiry 4: Large-scale automation (008) (25 s)
*Load **008** → Process.*
> "'AI automation for 500 customer enquiries per day, start immediately.' AI Automation, **High**, 70. The project-value factor got a bonus for the scale signal, '500 customer enquiries', and urgency got full points for 'immediately'. It doesn't ask how many enquiries they get, because they already told us."

### 3:40 – Enquiry 5: Partnership (011) and Internship (005) via batch (30 s)
*Go to **Batch Processing** → **Process all sample enquiries**.*
> "Enquiries can also come in through CSV upload or the REST API. This processes all 14 samples at once. For example, the partnership request is flagged for management review, and the internship request goes to HR with low priority. Everything is saved, and I can download the results as CSV."

*(Optional, 15 s)* *Switch to the `/docs` tab → `POST /enquiries` → Try it out.* "The same pipeline is exposed as an API, so a website form or an n8n workflow could push enquiries in automatically."

### 4:10 – History, approval and dashboard (35 s)
*Go to **Enquiry History & Approval** → open the complaint.*
> "Here's the separation between AI and human decisions. Every record is stored with status *Draft*. A reviewer can edit the reply, add notes, and approve or reject. Nothing is ever emailed by the system."
*Click **Approve**.* *Go to **Dashboard**.*
> "The dashboard shows total enquiries, high-priority leads, average score, the review queue and the category breakdown, so the team can see where their pipeline is coming from."

### 4:45 – Close (15 s)
> "On reliability: all AI output is validated with Pydantic, invalid JSON gets one self-repair retry, API failures fall back to the rule engine, and there are 21 automated tests. Thank you, I'm happy to walk through any part of the code."

---

**What to show for each enquiry (checklist):** input · category · extracted info · score · priority · draft · human-review status · saved ID.
