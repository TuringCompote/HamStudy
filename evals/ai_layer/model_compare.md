# Opus vs Sonnet — batch-explanation comparison

8 questions (4 electronics §5 no-grounding, 4 regs §1 with RBR-4/RIC grounding). Same `prompts/batch_explain.md`. Grade: per-distractor nuance + grounding fidelity.


## B-005-001-001 (§5)  If a dial marked in megahertz shows a reading of 3.525 MHz, what would it show if it were marked in kilohertz?
*correct: D · grounding: no*

### opus (claude-opus-4-8)
- core: 1 MHz = 1000 kHz, so 3.525 MHz × 1000 = 3525 kHz.
- distractor[['A', 'B', 'C']]: {"option": "A", "why_wrong": "35.25 kHz is off by a factor of 100 and in the wrong direction; converting MHz to kHz must increase the number, not shrink it.", "why_tempting": "Looks like a decimal-shift answer if you mistakenly divide or misplace the decimal twice."}
- concept: Metric prefix scaling: kilo = 10³, mega = 10⁶. To go from mega to kilo you change by 10⁶/10³ = 10³, i.e. multiply by 1000 (shift the decimal three places right). 3.525 × 10³ = 3525 kHz. This frequency sits in the 80 m amateur band, a useful sanity check.
- misconception: Confusing the kHz step (×1000) with the Hz step (×1 000 000), or shifting the decimal the wrong number of places/direction.
- link: Wavelength ↔ Frequency

### sonnet (claude-sonnet-4-6)
- core: 3.525 MHz equals 3 525 kHz because 1 MHz = 1 000 kHz, so multiplying 3.525 by 1 000 shifts the decimal three places to the right.
- distractor[['A', 'B', 'C']]: {"option": "A", "why_wrong": "35.25 kHz would result from dividing by 100 rather than multiplying by 1 000 — the decimal moves the wrong direction and by the wrong number of places.", "why_tempting": "Learners who conflate MHz-to-kHz with some other metric step (like centi-) or who mistakenly divide instead of multiply can land here."}
- concept: The SI prefix chain is: 1 MHz = 10⁶ Hz and 1 kHz = 10³ Hz, so 1 MHz = 10³ kHz exactly. Converting MHz → kHz means multiplying by 10³ (move the decimal three places right): 3.525 × 10³ = 3 525 kHz. Conversely, kHz → MHz divides by 10³. The full chain MHz → kHz → Hz each step multiplies by 1 000.
- misconception: The most common trap is mixing up which direction the decimal moves and by how many places — especially confusing the MHz-to-Hz conversion (×10⁶) with the MHz-to-kHz conversion (×10³), producing an answer that is off by a factor of 1 000 in either direction.
- link: Wavelength ↔ Frequency


## B-005-002-001 (§5)  Which of these groups lists three good electrical conductors?
*correct: D · grounding: no*

### opus (claude-opus-4-8)
- core: Gold, silver, and aluminum are all metals with abundant free conduction electrons, making them excellent electrical conductors. Only option D contains three conductors and no insulators.
- distractor[['A', 'B', 'C']]: {"option": "A", "why_wrong": "Wood is an insulator (dielectric); its electrons are tightly bound in covalent bonds, leaving no free charge carriers.", "why_tempting": "Gold and silver are top-tier conductors, so the pair feels right until you notice wood is included."}
- concept: Electrical conductivity depends on the density of mobile charge carriers. In metals, valence electrons occupy a partially filled conduction band, so they are delocalized and free to drift under an applied field. Silver has the highest conductivity (~6.3×10^7 S/m), followed closely by copper, gold, and aluminum. Insulators like wood, paper, and mica have full valence bands and a large band gap, so electrons cannot move freely. The exam's trick is mixing one insulator into otherwise-conductive lists.
- misconception: Assuming that if two of three listed items are good conductors the whole group qualifies — every item must be a conductor for the group to count.
- link: section 5

### sonnet (claude-sonnet-4-6)
- core: Gold, silver, and aluminum are all metals with high free-electron densities, making them excellent electrical conductors. All three have low resistivity and are widely used in electrical and electronic applications.
- distractor[['A', 'B', 'C']]: {"option": "A", "why_wrong": "Wood is an insulator, not a conductor. Its resistivity is many orders of magnitude higher than any metal, so this group cannot be three good conductors.", "why_tempting": "Gold and silver are indeed excellent conductors, so two-thirds of the list is correct — a learner might overlook that wood disqualifies the group entirely."}
- concept: Electrical conductivity depends on the availability of free charge carriers (electrons). Metals have partially filled or overlapping conduction bands, giving them a sea of mobile electrons. Resistivity ρ ranks roughly: silver (~1.59×10⁻⁸ Ω·m) < copper (~1.68×10⁻⁸ Ω·m) < gold (~2.44×10⁻⁸ Ω·m) < aluminum (~2.65×10⁻⁸ Ω·m). All four are excellent conductors. Non-metals like wood, paper, and mica are covalently bonded or ionic solids with wide band gaps and essentially no free electrons at room temperature — their resistivity is 10⁸–10¹⁵ Ω·m, making them insulators. Any group that includes one of these non-metals cannot qualify as 'three good conductors.'
- misconception: The trap is mixing familiar conductor names with familiar-sounding non-metals. Learners sometimes categorize materials by feel or common use ('paper is used in capacitors, so maybe it conducts a little') rather than by the fundamental conductor/insulator distinction.
- link: section 5


## B-005-003-001 (§5)  What term describes the rate at which electrical energy is used?
*correct: B · grounding: no*

### opus (claude-opus-4-8)
- core: Power is the rate at which electrical energy is converted or consumed per unit time, measured in watts (joules per second).
- distractor[['A', 'C', 'D']]: {"option": "A", "why_wrong": "Resistance is opposition to current flow, measured in ohms — it influences how much power dissipates but is not itself a rate of energy use.", "why_tempting": "Resistance is closely tied to power dissipation (P = I²R), so it feels related to energy consumption."}
- concept: Energy (joules) is the capacity to do work; power is its time derivative: P = dW/dt, in watts. Electrically, P = VI, and via Ohm's law P = I²R = V²/R. Note voltage is energy per charge (J/C) and current is charge per time (C/s); their product (J/C × C/s) yields J/s = watts — the rate of energy use. Energy consumed over time is then W = P·t, giving the kilowatt-hour billing unit.
- misconception: Conflating the quantity of energy with the rate of using it, or assuming any quantity described as a 'rate' (like current) automatically refers to energy.
- link: Ohm's Law & Power

### sonnet (claude-sonnet-4-6)
- core: Power is defined as the rate of doing work or converting energy — measured in watts (joules per second). It directly answers 'how fast is energy being consumed.'
- distractor[['A', 'C', 'D']]: {"option": "A", "why_wrong": "Resistance (ohms) opposes current flow and determines how much energy is dissipated as heat for a given current, but it is a property of the conductor, not a rate of energy use.", "why_tempting": "Because resistors do dissipate energy, learners conflate the element causing dissipation with the quantity describing its rate."}
- concept: Power P = dE/dt, measured in watts (W = J/s). For DC circuits: P = IV = I²R = V²/R. Power is the product of the driving potential (V) and the flow rate of charge (I), giving energy transferred per unit time. This is why both voltage and current are necessary ingredients — neither alone is a rate of energy use.
- misconception: The question targets confusion between the four fundamental electrical quantities. Learners often mix up which quantity describes energy *rate* versus energy *per charge* (voltage) or *charge rate* (current).
- link: Ohm's Law & Power


## B-005-004-001 (§5)  What is the voltage across a 2-ohm resistor if a current of 0.5 amperes flows through it?
*correct: D · grounding: no*

### opus (claude-opus-4-8)
- core: By Ohm's law, V = I × R = 0.5 A × 2 Ω = 1.0 V.
- distractor[['A', 'B', 'C']]: {"option": "A", "why_wrong": "0.25 V comes from dividing 0.5 by 2 (I/R) instead of multiplying — wrong operation.", "why_tempting": "Looks like a plausible result of combining the same two numbers, and 0.25 is the product 0.5×0.5 too."}
- concept: Ohm's law in the form V = I·R directly gives voltage from current and resistance. Here both quantities are in base SI units (amperes and ohms), so the product is in volts with no scaling: 0.5 × 2 = 1.0 V. Keep the triangle V=IR, I=V/R, R=V/I straight by covering the unknown.
- misconception: Confusing whether to multiply or divide — some learners divide current by resistance. Voltage is the product of current and resistance, never a quotient.
- link: Ohm's Law & Power

### sonnet (claude-sonnet-4-6)
- core: Applying Ohm's Law directly: V = I × R = 0.5 A × 2 Ω = 1.0 V. The voltage across the resistor is 1.0 volt.
- distractor[['A', 'B', 'C']]: {"option": "A", "why_wrong": "0.25 V results from dividing I by R (0.5 ÷ 2), inverting the Ohm's Law relationship for voltage.", "why_tempting": "Division feels intuitive when a value less than 1 is involved, and the numbers do divide cleanly."}
- concept: Ohm's Law in voltage form: V = I × R. With I = 0.5 A and R = 2 Ω, V = 0.5 × 2 = 1.0 V. The three rearrangements are V = IR, I = V/R, and R = V/I. A useful dimensional check: [A] × [Ω] = [V], confirming the operation is multiplication, not division.
- misconception: The key trap is confusing which quantity to solve for. When finding voltage, multiply I by R — don't divide R by I or I by R, both of which produce wrong answers that still use the given numbers.
- link: Ohm's Law & Power


## B-001-001-001 (§1)  Which document assigns the authority to make Canadian regulations governing radiocommunications?
*correct: C · grounding: yes*

### opus (claude-opus-4-8)
- core: The Radiocommunication Act is the enabling federal statute that grants the authority to make regulations (including the Radiocommunication Regulations) governing radiocommunication in Canada.
- distractor[['A', 'B', 'D']]: {"option": "A", "why_wrong": "RBR-4 (Standards for the Operation of Radio Stations in the Amateur Radio Service) is a subordinate document that sets operating standards; it operates under the authority of the Act and the Regulations, not the other way around.", "why_tempting": "It is the document amateurs actually read for their operating rules, so it feels like the source of authority."}
- concept: Canadian radio law follows a hierarchy: the Radiocommunication Act (the statute passed by Parliament) is the enabling legislation. It delegates power to the Governor in Council/Minister to make the Radiocommunication Regulations, and documents like RBR-4 are issued under that regulatory framework (RBR-4 itself notes operators must comply per section 45 of the Radiocommunication Regulations). Distinguish the Act (grants authority) from the Regulations (made under the Act) from standards/circulars (administrative detail). International treaty material (ITU) is implemented domestically but is not the source of Canadian legal authority.
- misconception: Confusing the document amateurs use day-to-day (RBR-4) or the international body (ITU) with the statute that actually confers regulation-making authority.
- link: section 1

### sonnet (claude-sonnet-4-6)
- core: The Radiocommunication Act is Canada's primary federal legislation that grants Parliament's authority over radiocommunications; all subordinate regulations — including the Radiocommunication Regulations and standards like RBR-4 — derive their legal force from it.
- distractor[['A', 'B', 'D']]: {"option": "A", "why_wrong": "RBR-4 (Standards for the Operation of Radio Stations in the Amateur Radio Service) is itself a subordinate standards document that operates *under* the authority of the Radiocommunication Act and Radiocommunication Regulations — it receives authority, it does not assign it.", "why_tempting": "It's the document amateurs study most closely, so it feels like the foundational rulebook, but it sits near the bottom of the regulatory hierarchy."}
- concept: Canadian spectrum law follows a hierarchy: the Radiocommunication Act (federal statute) sits at the top, empowering the Minister of Innovation, Science and Economic Development to make the Radiocommunication Regulations (Governor-in-Council). Those Regulations in turn authorize ISED to publish standards documents like RBR-4. Per RBR-4's own scope statement, operators must comply with its provisions 'in accordance with section 45 of the Radiocommunication Regulations' — tracing authority back up the chain to the Act itself. Understanding this hierarchy clarifies why changes to band plans or power limits appear in subordinate instruments rather than requiring new legislation.
- misconception: Learners often mistake the most-read document (RBR-4) or the most internationally visible body (ITU) for the primary source of Canadian regulatory authority. The key insight is that authority flows downward from domestic statute to regulation to standard — not from international treaties or operational documents.
- link: section 1


## B-001-002-001 (§1)  What must you do within 30 days of a mailing address change?
*correct: A · grounding: yes*

### opus (claude-opus-4-8)
- core: RBR-4 section 13 requires the certificate holder to notify ISED's Amateur Radio Service Centre of a mailing-address change within 30 days. ISED (Innovation, Science and Economic Development Canada) is the federal regulator that maintains the certificate and call-sign records.
- distractor[['B', 'C', 'D']]: {"option": "B", "why_wrong": "A local club has no role in maintaining your official station record; notifying it satisfies no regulatory obligation.", "why_tempting": "Clubs are a natural point of contact for amateurs and may keep their own membership rolls, blurring the line with official records."}
- concept: In Canada the regulator for the amateur service is ISED (formerly Industry Canada). The certificate and its associated mailing address are held in ISED's database, so any change must go back to that same authority. RBR-4 section 13 sets the reporting interval at 30 days. Keeping the address current ensures official correspondence and station records remain valid.
- misconception: That amateur-radio administrative duties are handled by community organizations (clubs, RAC) rather than the federal department that actually issues the certificate.
- link: section 1

### sonnet (claude-sonnet-4-6)
- core: Per RBR-4 section 13, the holder of an Amateur Radio Operator Certificate must notify ISED's Amateur Radio Service Centre of any change of mailing address within 30 days. This is a regulatory obligation — ISED is the licensing authority and must be able to reach certificate holders.
- distractor[['B', 'C', 'D']]: {"option": "B", "why_wrong": "Your local amateur radio club has no regulatory role in maintaining your licence records. Informing them may be socially useful but carries zero legal weight.", "why_tempting": "Clubs often serve as a community hub and first point of contact for many amateur-related matters, so it feels like the natural place to report a change."}
- concept: Section 13 of RBR-4 (Issue 3, July 2022) places a specific, time-bounded obligation on certificate holders: notify ISED's Amateur Radio Service Centre within 30 days of a mailing address change. ISED issues and maintains Amateur Radio Operator Certificates under the Radiocommunication Act, so keeping your contact information current with them is a direct regulatory requirement — not a courtesy. No other organization has standing to receive this notification on ISED's behalf.
- misconception: Learners often conflate prominent amateur organizations (clubs, RAC) or exam-related officials (accredited examiners) with the actual regulatory authority. Only ISED holds the regulatory mandate and must be kept informed.
- link: section 1


## B-001-003-001 (§1)  Transmissions outside of amateur radio bands:
*correct: C · grounding: yes*

### opus (claude-opus-4-8)
- core: Amateur operators are authorized only within the frequency bands allocated to the amateur service (Schedule I of RBR-4). Transmitting outside those bands is prohibited, and the control operator is responsible for the station's compliance and can face penalties.
- distractor[['A', 'B', 'D']]: {"option": "A", "why_wrong": "There is no general low-power exemption that authorizes operation on frequencies not allocated to the amateur service; power level does not create new privileges.", "why_tempting": "Many regulations do scale with power (e.g. EIRP limits on LF bands), so a learner may assume a tiny-power loophole exists for out-of-band use."}
- concept: Amateur privileges are defined by allocation: Schedule I lists each amateur band, its maximum bandwidth, operating provisions, and the qualification required. Your authorization extends only to those listed segments. The control operator is the person responsible for the station's emissions at all times, so liability for an out-of-band transmission attaches to that operator. Other services (broadcast, aeronautical, fixed, etc.) hold the spectrum outside amateur allocations, and amateur transmissions must not cause interference to them (see RBR-4 s.8).
- misconception: That some condition—low power, a brief test, or proper identification—can authorize transmitting on a frequency not allocated to amateurs. None can; the band allocation itself is the controlling authorization.
- link: Canadian Band-Plan Explorer

### sonnet (claude-sonnet-4-6)
- core: Transmitting outside the allocated amateur radio bands is strictly prohibited under Canadian law. The control operator bears direct legal responsibility and may face penalties including fines or loss of operating privileges.
- distractor[['A', 'B', 'D']]: {"option": "A", "why_wrong": "There is no power threshold that makes out-of-band transmission permissible. Operating outside the amateur bands is illegal regardless of power level — even 1 milliwatt would be a violation.", "why_tempting": "Low power is often treated as a mitigating factor in RF interference discussions, so learners may assume a de minimis exception exists for very low power levels."}
- concept: Amateur radio operators are licensed to use only the frequency bands specified in Schedule I of RBR-4. Operating outside those bands means transmitting in spectrum allocated to other services (aviation, military, commercial, etc.), which can cause harmful interference and violates the Radiocommunication Act. The control operator — the licensed amateur responsible for the transmission at any given moment — is the accountable party. Penalties can include fines and revocation of certification. There are no power-level exemptions, no 'brief test' carve-outs, and no identification workarounds for out-of-band operation.
- misconception: The most common trap is believing that low power, brief duration, or proper identification can excuse or legalise an out-of-band transmission. None of these factors change the fundamental prohibition; the bands themselves define the legal operating space.
- link: Canadian Band-Plan Explorer


## B-001-004-001 (§1)  How old must you be to hold an Amateur Radio Operator Certificate with Basic Qualification?
*correct: A · grounding: yes*

### opus (claude-opus-4-8)
- core: There is no minimum or maximum age to hold an Amateur Radio Operator Certificate with Basic Qualification in Canada — anyone who passes the qualifying examination may be certified.
- distractor[['B', 'C', 'D']]: {"option": "B", "why_wrong": "No upper age cap exists; certification does not expire or become invalid based on age.", "why_tempting": "It mimics rules in some other licensing schemes (e.g., driving) where older holders face restrictions or retesting."}
- concept: Canadian amateur certification is competency-based, not age-based. Eligibility hinges solely on demonstrating the required knowledge by passing the Basic Qualification examination. The standards governing operation (RBR-4) and the certificate system attach privileges to qualifications (Basic, Morse, Advanced), not to the holder's age. There is therefore neither a floor nor a ceiling — a capable child and an adult are treated identically once certified.
- misconception: Assuming amateur radio follows the age-gating common to other government-issued permits (driving, voting). The exam, not a birthdate, is the gatekeeper.
- link: None

### sonnet (claude-sonnet-4-6)
- core: There is no minimum or maximum age requirement to hold an Amateur Radio Operator Certificate with Basic Qualification in Canada. Any person who passes the required examination may be certified, regardless of age.
- distractor[['B', 'C', 'D']]: {"option": "B", "why_wrong": "No upper age limit exists in Canadian amateur radio regulations. Operators are not required to relinquish their certificate at any age.", "why_tempting": "Some licences in other fields (e.g., aviation medicals) impose upper age limits or periodic renewal requirements, so learners may assume radio licensing works similarly."}
- concept: Canadian amateur radio licensing is administered under the Radiocommunication Act and its subordinate regulations (including RBR-4). Neither RBR-4 nor the Radiocommunication Regulations impose any age restriction on obtaining or holding an Amateur Radio Operator Certificate with Basic Qualification. The exam tests technical and regulatory knowledge; if you can pass, you qualify — age is simply irrelevant. This is notably more permissive than many other licensed activities.
- misconception: Learners often assume that because a certificate is a government-issued credential tied to operating radio equipment, some minimum legal age (commonly 14 or 18) must apply, by analogy to driving licences or contracts. No such restriction exists in Canadian amateur radio regulations.
- link: section 1
