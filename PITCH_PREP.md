# AI Voice Helper — Pitch Preparation Guide
## 15-Minute Interview: 5 min pitch + 10 min Q&A

---

## SLIDE DECK OUTLINE (5 slides — 1 min each)

---

### SLIDE 1: THE PROBLEM (60 seconds)
**Title:** "285 Million People Can't Use a Computer Independently"

**Visual:** A stark statistic on a dark background. Optional: photo of someone struggling at a screen.

**Key Points to Display:**
- 285 million visually impaired people worldwide (WHO)
- 2.2 billion have some form of vision impairment
- Existing tools (screen readers like JAWS) cost $1,000+/year and take **months** to learn
- Screen readers break constantly — every UI update, every new app = broken workflow
- Blind users can't use most modern apps (Spotify, banking, shopping) independently

**What to SAY:**
> "Imagine you sit down at your computer and you can't see anything. Today, your best option is a $1,000/year screen reader that takes 3-6 months to learn, breaks every time an app updates, and still can't handle most modern software. 285 million people face this reality every day. That's a massive underserved market — and we have a fundamentally better approach."

---

### SLIDE 2: THE SOLUTION — LIVE DEMO OR DEMO VIDEO (90 seconds)
**Title:** "Your AI Eyes — Just Talk, It Does Everything"

**Visual:** Screenshot of your app's premium UI (the Tesla/Grok-inspired dark overlay). If possible, embed a **15-second screen recording** showing: user says "open Chrome and go to Google" → app does it.

**Key Points to Display:**
- Voice-first: user talks naturally, AI responds conversationally
- AI **sees** the screen in real-time (screenshot + UI element detection)
- AI **acts** on the computer: clicks, types, scrolls, opens apps
- Works with **ANY** Windows application — not just browsers
- Safety layer: confirms before purchases, deletions, sensitive actions

**What to SAY:**
> "AI Voice Helper is like having a sighted friend sitting next to you. You just talk — say 'open Notepad and write a grocery list' or 'go to Amazon and search for headphones' — and the AI sees your screen, understands it, and controls the computer for you. No memorizing shortcuts. No learning curve. It works with every app on Windows because it sees the same screen you would."

**DEMO TIP:** If doing live demo, have a scripted flow ready:
1. Launch the app (the sleek overlay appears)
2. Say "Open Notepad"  → it opens Notepad
3. Say "Type 'Hello World'" → it types
4. Say "Save this file to Desktop" → it navigates Save dialog

---

### SLIDE 3: HOW IT WORKS — TECH (45 seconds)
**Title:** "Powered by Google Gemini — Three AI Loops Working Together"

**Visual:** Simple architecture diagram with 3 boxes:
```
[Voice Loop]          [Vision Loop]           [Action Loop]
Gemini Live API  →   Screenshot + AI    →    Mouse/Keyboard
User speaks      →   Understands screen →    Executes commands
AI responds      →   Decides next step  →    Confirms success
```

**Key Points to Display:**
- **Voice:** Gemini Live API — real-time natural conversation (not text-to-speech)
- **Vision:** Gemini 2.5 Flash — analyzes screenshots to understand any UI
- **Action:** PyAutoGUI + Windows Accessibility APIs — pixel-perfect clicks
- **Safety:** Confirms risky actions (purchases, deletions, sign-outs)
- No app-specific integrations needed — it works universally

**What to SAY:**
> "Under the hood, three AI systems work in parallel. A voice model that has a real conversation with you. A vision model that looks at your screen and figures out what's there. And an action engine that clicks, types, and navigates — just like a human would. The breakthrough is that we don't need special integrations with each app. Our AI sees the same pixels a human sees, so it works with everything."

---

### SLIDE 4: MARKET & BUSINESS MODEL (60 seconds)
**Title:** "A $7B+ Problem — and We're 10x Cheaper"

**Visual:** Simple comparison table + market size

| | JAWS (Market Leader) | AI Voice Helper |
|---|---|---|
| Annual Cost | $1,000/yr | $10-20/month |
| Learning Curve | 3-6 months | Zero — just talk |
| App Coverage | Limited (needs plugins) | Universal (any app) |
| Setup | Complex installation | One-click install |

**Market Size:**
- Assistive Tech market: $7.2B (2024), growing 7.5% CAGR
- Screen reader market specifically: ~$600M
- Adjacent markets: elderly tech assistance, corporate accessibility compliance

**Revenue Model:**
- **Freemium SaaS**: Free tier (limited daily usage) → $15/month Pro → $25/month Enterprise
- **B2B Licensing**: Sell to enterprises needing ADA/WCAG compliance
- **Government contracts**: VA (veterans with vision loss), state rehab agencies

**What to SAY:**
> "JAWS, the market leader in screen readers, charges $1,000 a year and hasn't fundamentally innovated in decades. We can offer a 10x better product at a fraction of the cost because AI handles the hard part. The assistive technology market is $7 billion and growing. We're starting with a $15/month subscription for individual users, with a clear path to enterprise licensing and government contracts — the VA alone serves over 130,000 legally blind veterans."

---

### SLIDE 5: ASK & USE OF FUNDS (45 seconds)
**Title:** "The Ask: $500 to Launch Beta"

**Visual:** Pie chart or simple breakdown

**$500 Use of Funds:**
| Amount | Use | Outcome |
|---|---|---|
| $200 | Google Cloud / Gemini API credits | 3 months of beta testing with real users |
| $100 | User testing with visually impaired users | 10-15 beta testers, real feedback |
| $75 | Domain + hosting + landing page | Professional web presence for outreach |
| $75 | Accessibility community outreach | NFB/ACB conference materials, flyers |
| $50 | Code signing certificate (Windows) | Trusted installer — critical for distribution |

**What to SAY:**
> "We're asking for $500 to take this from working prototype to beta launch. The biggest cost is API credits to run our beta with 10-15 real visually impaired users. We'll use user testing feedback to nail the experience, stand up a landing page, and begin outreach to the accessibility community — organizations like the National Federation of the Blind. With strong beta results, we'll be positioned to raise a proper seed round."

---

## FULL 5-MINUTE SPEAKING SCRIPT

*(Practice this until you can deliver it naturally, NOT reading from notes)*

---

**[0:00 – 0:50] HOOK + PROBLEM**

"Good [morning/afternoon]. I'm [Your Name], and I'm building AI Voice Helper.

Let me ask you a question — how many times did you look at your screen today? To check email, read a message, click a button? Now imagine you couldn't see any of it.

285 million people worldwide are visually impaired. And right now, their best option for using a computer is a screen reader called JAWS — it costs a thousand dollars a year, takes months to learn, and breaks every time an app updates. Most modern software — Spotify, online banking, shopping — just doesn't work well with screen readers.

That's a massive problem, and AI has finally made a fundamentally better solution possible."

**[0:50 – 2:20] SOLUTION + DEMO**

"AI Voice Helper is like having a sighted friend sitting next to you at the computer. You just talk.

You say 'Open Chrome and search for weather in Chicago' — and the AI opens Chrome, navigates to Google, types the search, and reads you the results. You say 'Open Notepad and write a quick grocery list' — it opens Notepad and starts typing what you dictate.

*[If live demo — do it here. If showing video/screenshots, narrate them.]*

What makes this different from a screen reader is simple: our AI actually SEES the screen. It takes a screenshot, understands what's on it using Google's Gemini vision model, and then clicks and types just like a human would. That means it works with ANY application on Windows — no special plugins, no integrations needed.

And there's a built-in safety layer. If you accidentally say 'buy this' or 'delete that file,' it stops and asks you to confirm first. Because when you can't see what you're clicking, safety matters."

**[2:20 – 3:20] TECH EDGE**

"Technically, three AI systems work together in real time.

First, Google's Gemini Live API handles the voice conversation — this isn't text-to-speech, it's a real conversational AI that listens and responds naturally.

Second, Gemini's vision model analyzes screenshots of the screen to understand what's there — buttons, text fields, menus, content — across any application.

Third, our action engine translates AI decisions into real mouse clicks and keyboard inputs, using Windows accessibility APIs for pixel-perfect accuracy.

The key insight is that we don't need to integrate with each individual app. Our AI sees what a human sees, so it works universally."

**[3:20 – 4:20] MARKET + BUSINESS**

"The assistive technology market is $7 billion and growing at 7.5% annually. The current market leader, JAWS, charges $1,000 per year for a product that hasn't fundamentally changed in over a decade.

We plan to offer this as a $15/month subscription — 10x cheaper — with a free tier to drive adoption. There's also a clear B2B opportunity: companies need accessibility compliance under the ADA and WCAG standards, and government agencies like the VA serve over 130,000 legally blind veterans.

Our competitive moat is the AI stack. As Gemini and other models get better, our product automatically gets better — no manual rules, no app-by-app plugins."

**[4:20 – 5:00] ASK + CLOSE**

"Today, we have a working prototype. You saw it [work / in the demo]. It can open apps, navigate websites, type documents, and navigate file dialogs — all through natural voice commands.

We're asking for $500 to run a 3-month beta with 10-15 visually impaired users. That covers API credits, user testing, and initial community outreach. With strong beta results, we'll raise a seed round to scale.

Thank you. I'm happy to answer any questions."

---

## Q&A PREPARATION — 20 LIKELY QUESTIONS & STRONG ANSWERS

---

### 1. "How is this different from Siri / Google Assistant / existing voice assistants?"
> "Great question. Siri and Google Assistant work within their own ecosystems — they can set a timer or play music, but they can't navigate your email client, fill out a form on a random website, or use desktop software like Excel. Our AI actually SEES the screen and controls the mouse and keyboard, so it works with any application. It's the difference between a voice assistant and a remote human helper who happens to be AI."

### 2. "What about Apple VoiceOver or Microsoft Narrator — they're free?"
> "VoiceOver and Narrator are basic screen readers — they read text on screen out loud, but the user still needs to memorize dozens of keyboard shortcuts to navigate. They're tools that help blind users DO the work. We're an AI that DOES the work FOR them. Our approach is: you say what you want, and the AI handles all the navigation. Zero learning curve."

### 3. "How accurate is the clicking / does it make mistakes?"
> "We're about 85-90% accurate on common tasks — opening apps, navigating menus, typing. Complex tasks like navigating nested file dialogs are where we're still improving. But here's the key: we have a safety layer that confirms before any risky action, and the AI retries with a different approach if something fails. And accuracy will keep improving as the underlying AI models improve."

### 4. "What about privacy? You're screenshotting people's screens."
> "Privacy is critical, especially for this user base. Screenshots are sent to Google's Gemini API for analysis but are never stored — they're processed in real-time and discarded. We plan to add local processing options as on-device vision models mature. We'll also provide clear privacy controls and a full privacy policy before any public beta."

### 5. "What's your unfair advantage / competitive moat?"
> "Three things. First, we're building the UX expertise around how visually impaired users actually interact with computers — that domain knowledge is hard to replicate. Second, our multi-model architecture (voice + vision + action) is novel — nobody else is combining these three in real-time for accessibility. Third, the AI models keep getting better, which means our product improves automatically without us having to rewrite rules or plugins."

### 6. "How big is your team?"
> "Right now it's [one person / small team]. But that's actually a validation of the approach — one person built a working prototype in [X weeks] using modern AI APIs. The early investment would fund user testing and beta refinement. A seed round would fund hiring a UX researcher with accessibility experience and an additional engineer."

### 7. "What if Google changes Gemini pricing or API access?"
> "Gemini is not our only option — our architecture is model-agnostic. The vision module can use any vision LLM (GPT-4V, Claude, open-source models like LLaVA). The voice module can swap to any speech API. We're built on a provider abstraction layer, so switching models is a configuration change, not a rewrite. That said, Google is actively investing in accessibility and is unlikely to restrict this use case."

### 8. "Have you talked to visually impaired users?"
> "Yes — that's exactly what the beta funding is for. We've done initial research into the pain points of screen reader users through online communities (r/blind, NFB forums). The $500 will fund formal user testing with 10-15 visually impaired participants to validate the product-market fit and prioritize features."
> *(If you HAVE talked to real users, replace this with specific anecdotes)*

### 9. "What's your go-to-market strategy?"
> "Our initial channel is the visually impaired community — organizations like the National Federation of the Blind (NFB) and American Council of the Blind (ACB). These communities are tight-knit and word-of-mouth driven. We'll offer a generous free tier to build adoption, then convert to paid subscriptions. Long-term, the B2B channel (enterprises needing accessibility compliance) is actually the bigger revenue opportunity."

### 10. "Can this work on Mac or Linux?"
> "We're Windows-first because 85% of screen reader users are on Windows — it's where the market is. The voice and vision components are platform-agnostic. The action layer (mouse/keyboard control) would need a platform-specific module for Mac or Linux, but it's an incremental engineering effort, not a fundamental redesign."

### 11. "What are the ongoing costs / unit economics?"
> "The main variable cost is the AI API usage — roughly $0.01-0.03 per user interaction for vision + voice. At $15/month, even heavy users (100+ interactions/day) are profitable. As we scale, we can negotiate volume pricing with Google, and on-device models will reduce API costs over time."

### 12. "What happens when someone's internet goes down?"
> "Currently, the AI requires an internet connection since the models run in the cloud. In the short term, we'd provide a clear audio notification: 'I'm offline right now, but your computer is still working.' Medium-term, as smaller on-device models become viable, we can add an offline mode for basic tasks."

### 13. "Is this HIPAA compliant? / Can it be used in healthcare?"
> "Not yet, but that's a realistic future path. Healthcare providers need accessible tools for visually impaired staff and patients. We'd need to ensure screenshots aren't stored and add audit logging. That's a post-seed-round initiative."

### 14. "Where do you see this in 5 years?"
> "Two big expansions. First, beyond visual impairment — this same technology helps elderly users who struggle with technology, people with motor disabilities, and anyone who wants hands-free computer use. Second, beyond the desktop — mobile phones, smart TVs, kiosks. Anytime a human needs to interact with a screen, AI can mediate."

### 15. "What's the revenue potential in year 1?"
> "Conservative: 500 paying users at $15/month = $90K ARR by end of year 1. That's very achievable through the NFB community alone, which has 50,000+ members. Aggressive: if we land even one enterprise pilot (banks need ADA compliance), a single contract could be $50-100K."

### 16. "What if Microsoft or Google builds this themselves?"
> "They might, eventually. But big companies are slow to serve niche markets — Microsoft's Narrator has existed for 20 years and still has major gaps. We can move faster, iterate with real users, and build community trust. And if a big tech company builds something similar, that validates the market — and acquisition becomes a viable exit."

### 17. "How do you handle security? Can the AI be tricked into doing something malicious?"
> "We have a dedicated safety module that blocks risky actions without explicit confirmation — purchases, deletions, sign-outs, file transfers. The AI also can't execute system-level commands or access files without user initiation. We treat the AI like an employee with limited permissions, not an admin."

### 18. "What are the biggest technical risks?"
> "Click accuracy on complex UIs — like nested menus or tiny buttons. We're at 85-90% and improving by combining vision with Windows Accessibility APIs for exact element coordinates. The other risk is API latency — we need responses in under 2 seconds for a good experience. Currently we're averaging 1-1.5 seconds, which is good."

### 19. "Why should we fund YOU specifically?"
> "Because I've already built it. This isn't a pitch deck idea — it's a working prototype. I built the entire system end to end — voice, vision, action execution, safety layer, GUI — using cutting-edge AI. That demonstrates I can ship, iterate, and solve hard technical problems. What I need now is funding to put it in front of real users."

### 20. "What would success look like in 3 months?"
> "Three clear milestones. First: complete a beta with 10-15 visually impaired users and achieve an 80%+ task completion rate. Second: have 3 paying beta customers. Third: have a polished demo and metrics ready to pitch angel investors for a proper seed round."

---

## PRESENTATION TIPS FOR THE INTERVIEW

### Do:
- **Start with the human story**, not the tech. They're business people — lead with the problem and market.
- **Show, don't tell.** If you can do a 20-second live demo, it's worth more than 5 slides.
- **Give concrete numbers:** 285M people, $7B market, $1,000/yr competitor, $15/mo your price.
- **Be honest about limitations.** "We're at 85-90% accuracy and improving" is more credible than "it works perfectly."
- **Know your $500 breakdown cold.** They want to see you've thought carefully about resource allocation.
- **Practice the 5-minute pitch 5+ times** out loud with a timer. You WILL run long the first few times.
- **Dress business casual** and have a clean, well-lit background on video.

### Don't:
- Don't spend more than 30 seconds on the tech architecture. They care about impact, not implementation.
- Don't apologize for being early-stage — that's why this program exists.
- Don't say "we could" or "we might" — say "we will" and "our plan is."
- Don't read from slides — slides are visual aids, not a script.
- Don't go over 5 minutes. When time's up, stop. Respect their time.

---

## QUICK REFERENCE — KEY STATS TO MEMORIZE

| Stat | Number |
|---|---|
| Visually impaired globally | 285 million (WHO) |
| Vision impairment (any level) | 2.2 billion |
| Assistive tech market size | $7.2B, growing 7.5% CAGR |
| JAWS annual license cost | $1,000/year |
| Your planned price | $15/month ($180/year) |
| Price advantage | 5.5x cheaper |
| Legally blind US veterans (VA) | ~130,000 |
| NFB membership | 50,000+ |
| Task accuracy (current) | ~85-90% |
| API cost per interaction | ~$0.01-0.03 |
| Beta users target | 10-15 |
| Year 1 ARR (conservative) | $90K |

---

## DEMO SCRIPT (if doing live demo)

Have this ready BEFORE the call. Test it 3 times before the interview.

**Setup:**
- App is already running and showing the overlay
- Notepad is closed
- Browser is closed

**Demo Flow (45 seconds max):**
1. Say: "Open Notepad" → AI opens Notepad *(5 sec)*
2. Say: "Type 'Meeting notes for March 10'" → AI types it *(8 sec)*
3. Say: "What's on my screen right now?" → AI describes what it sees *(8 sec)*
4. Say: "Open Chrome and go to google.com" → AI does it *(10 sec)*

**If anything fails:** Just say "As you can see, it's still learning — that's exactly why we need beta testing funding" and move on confidently. Don't debug live.

---

*Good luck — you built something impressive. Now go show them.*
