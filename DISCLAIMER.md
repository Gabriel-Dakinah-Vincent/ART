# Project Disclaimer, Safety, and Legal Notice

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/Home-README-1F6FEB?style=for-the-badge&logo=readme&logoColor=white" alt="Home README" /></a>
  <a href="#project-disclaimer-and-legal-notice"><img src="https://img.shields.io/badge/Legal-Notice-BD561D?style=for-the-badge&logo=law&logoColor=white" alt="Legal Notice" /></a>
  <a href="#minimum-authorization-standard"><img src="https://img.shields.io/badge/Use-Authorized%20Only-8B0000?style=for-the-badge" alt="Authorized Use Only" /></a>
</p>

<p align="center">
  <a href="#student-and-academic-use"><img src="https://img.shields.io/badge/Audience-Students-6F42C1?style=for-the-badge&logo=bookstack&logoColor=white" alt="Audience Students" /></a>
  <a href="#guidance-for-instructors-schools-and-training-programs"><img src="https://img.shields.io/badge/Audience-Instructors-8250DF?style=for-the-badge&logo=googleclassroom&logoColor=white" alt="Audience Instructors" /></a>
  <a href="#practical-compliance-checklist"><img src="https://img.shields.io/badge/Compliance-Checklist-1F883D?style=for-the-badge&logo=checkmarx&logoColor=white" alt="Compliance Checklist" /></a>
</p>

<p align="center">
  <a href="#liberia-cybercrime-act-2021"><img src="https://img.shields.io/badge/Jurisdiction-Liberia%20Act%20Summary-0A7E8C?style=for-the-badge" alt="Liberia Act Summary" /></a>
  <a href="#prohibited-use"><img src="https://img.shields.io/badge/Scope-Prohibited%20Use-D73A49?style=for-the-badge&logo=shield&logoColor=white" alt="Prohibited Use" /></a>
  <a href="#executive-summary"><img src="https://img.shields.io/badge/Format-Plain%20Language-8250DF?style=for-the-badge&logo=markdown&logoColor=white" alt="Plain Language Summary" /></a>
</p>

<p align="center">
  <strong>Compliance-first guidance for authorized research, teaching, and controlled lab use.</strong><br />
  Informational only. Not legal advice. Not permission. Not a waiver of scope, policy, or law.
</p>

> Important
> This repository is provided solely for lawful, authorized security research, controlled red-team lab activity, defensive validation, academic study, and educational analysis.
>
> It must not be used for unauthorized access, unlawful interception, credential theft, evasion of security controls, service disruption, harassment, fraud, or any activity that violates law, contract, platform rules, institutional policy, or professional standards.

---

## Quick Navigation

1. [Executive Summary](#executive-summary)
2. [At a Glance](#at-a-glance)
3. [Quick Decision Guide](#quick-decision-guide)
4. [Intended Audience](#intended-audience)
5. [Student and Academic Use](#student-and-academic-use)
6. [Guidance for Instructors, Schools, and Training Programs](#guidance-for-instructors-schools-and-training-programs)
7. [Minimum Authorization Standard](#minimum-authorization-standard)
8. [Prohibited Use](#prohibited-use)
9. [Repository-Specific Risk Factors](#repository-specific-risk-factors)
10. [Operational Risk Notice](#operational-risk-notice)
11. [Liberia Cybercrime Act, 2021](#liberia-cybercrime-act-2021)
12. [Practical Compliance Checklist](#practical-compliance-checklist)
13. [If Something Goes Wrong](#if-something-goes-wrong)
14. [No Waiver](#no-waiver)
15. [Recommendation](#recommendation)

---

## Executive Summary

Use of this repository is entirely at the operator's risk and responsibility. Nothing in this repository, its source code, its build scripts, or its documentation grants permission to access, monitor, modify, or interfere with any system, account, network, device, or data without valid authorization.

This file is an informational and compliance-oriented notice only. It is not legal advice and does not create any license, immunity, permission, waiver, or defense.

### Core Principles

- authorization must exist before any deployment, execution, monitoring, collection, or persistence activity begins
- authorization must be specific enough to identify the systems, accounts, time window, and techniques that are allowed
- educational or research intent does not override law, policy, contract, platform rules, or institutional restrictions
- uncertainty is a stop condition, not a reason to continue and clarify later

## At a Glance

| Topic | Standard |
| --- | --- |
| Allowed use | Authorized lab work, supervised research, approved classroom exercises, defensive testing |
| Not allowed | Unauthorized access, surveillance, disruption, impersonation, credential misuse, public-target testing |
| Student use | Only in approved course, lab, capstone, or isolated self-study environments with valid permission |
| Professional use | Only with written authorization and defined scope |
| Legal position | Educational intent does not override law, policy, or contract |
| Advice status | Informational only; not legal advice |

## Quick Decision Guide

| Question | If the answer is yes | If the answer is no |
| --- | --- | --- |
| Do you have prior authorization from a lawful system owner or delegate? | Continue to scope validation | Stop immediately |
| Is the activity confined to an isolated lab, approved sandbox, or written engagement scope? | Continue to rule validation | Stop immediately |
| Are persistence, credential handling, monitoring, or data collection explicitly allowed? | Continue only within those limits | Treat them as prohibited |
| Are uninvolved users, production data, public services, or third parties excluded from impact? | Continue with caution | Stop immediately |
| Can you identify who approved the work, when it is allowed, and how incidents are reported? | Proceed with documented controls | Stop until clarified |

If any prerequisite cannot be confirmed in writing or through an equivalent formal authorization channel, this repository should not be used.

## Intended Audience

This disclaimer is written to support the following readers:

- students studying cybersecurity, computer science, digital forensics, or related disciplines
- instructors, lecturers, lab coordinators, and academic supervisors
- researchers conducting approved experimentation in isolated environments
- professional red teams, internal security teams, and penetration testers acting under written authorization
- organizations evaluating or documenting legal and operational risk associated with security tooling

## Student and Academic Use

Students may only use this repository in a legitimate academic or training context where all of the following are true:

- the activity is part of a course, lab, capstone, supervised project, or approved self-study exercise
- the environment is owned by the student, owned by the institution, or expressly authorized for the exercise
- the rules of engagement are defined by an instructor, supervisor, lab owner, or system owner
- the use remains inside the approved scope and does not affect uninvolved users, institutions, or third parties

Educational purpose does not, by itself, make conduct lawful. A student can still face criminal, civil, academic, disciplinary, or employment consequences if they exceed authorization, test public systems without consent, target real users, or ignore university policy, platform terms, or local law.

### Student Pre-Use Checklist

Before any use, students should be able to confirm each of the following:

- who owns the systems or accounts involved
- who granted permission
- what exact activities are permitted
- what dates and times the authorization covers
- whether data collection, credential handling, persistence, or monitoring is prohibited
- whether faculty approval, ethics review, or departmental sign-off is required

If any answer is unclear, the activity should stop until the issue is clarified.

## Guidance for Instructors, Schools, and Training Programs

If this repository is referenced in a classroom, workshop, or training program, instructors and organizers should ensure that:

- usage is confined to isolated lab assets, sandboxed virtual machines, or clearly designated test infrastructure
- students receive written rules of engagement and acceptable-use instructions
- real accounts, personal devices, production services, and public infrastructure are excluded from scope
- any logging, monitoring, or data capture is disclosed and proportionate to the educational purpose
- students understand that offensive security techniques remain subject to legal and ethical limits even in a learning environment

Institutions should apply their own disciplinary rules, research governance, IT policies, safeguarding procedures, and local legal compliance obligations in addition to this notice.

## Minimum Authorization Standard

For purposes of this repository, use should be treated as authorized only when there is clear, prior, and preferably written permission from a person or entity with lawful authority over the relevant system, network, account, application, service, or dataset.

### Authorization Should Define

- the authorized operator or team
- the systems, accounts, and networks in scope
- the time period during which testing is allowed
- the categories of actions permitted and prohibited
- any restrictions on persistence, credential access, interception, collection, or modification of data
- incident reporting and shutdown procedures if unintended impact occurs

If there is doubt about whether access is authorized, whether scope has changed, or whether a technique is permitted, the correct course is to stop and obtain clarification before proceeding.

### Authorization Records to Retain

Operators should retain a clear record of:

- who granted authorization and in what capacity
- the approval date, testing window, and expiration date if any
- the systems, user accounts, applications, and data sets in scope
- prohibited techniques or prohibited categories of data
- escalation contacts and incident reporting procedures
- any special limits on credential access, persistence, collection, monitoring, or exfiltration

Maintaining these records does not guarantee legality, but failing to maintain them makes it harder to demonstrate good-faith compliance and scope control.

## Prohibited Use

This repository must not be used to:

- access or attempt to access any system or account without authorization
- intercept non-public communications or data without lawful approval
- capture, exfiltrate, alter, delete, suppress, or manipulate data outside approved scope
- obtain, store, share, or misuse passwords, tokens, session data, or access codes without authorization
- evade detection, conceal activity, or frustrate monitoring outside an approved assessment
- interfere with the availability, reliability, or integrity of services
- harass, stalk, threaten, extort, impersonate, or deceive individuals
- target schools, employers, public platforms, financial systems, or critical infrastructure without explicit legal authority and written permission
- conduct experiments on classmates, faculty, employers, third-party users, or the public

## Repository-Specific Risk Factors

This repository includes material that can materially increase legal, institutional, and operational risk if misused. Higher-risk categories include:

| Capability Area | Risk Concern |
| --- | --- |
| remote execution | may constitute unauthorized access or system interference if run outside approved scope |
| credential or token handling | can trigger liability for unlawful access, interception, misuse of devices, or identity misuse |
| persistence mechanisms | can exceed scope even where temporary testing was authorized |
| data transfer and artifact collection | can cross into unauthorized collection, retention, disclosure, or exfiltration |
| browser/session material handling | may expose personal, regulated, or institutionally protected data |
| build and packaging automation | can make redistribution, deployment, and reuse easier than the original scope intended |

Any operator using this repository should assume that these capabilities will be judged based on authorization, proportionality, documentation, and real-world impact, not on stated intent alone.

## Operational Risk Notice

Security tools that provide remote execution, automation, credential handling, persistence, data transfer, or command-and-control style behavior can create legal risk even when they are built or studied for research purposes. Risk increases sharply when such tools are used outside isolated labs, outside written scope, or in ways that affect real users or production systems.

Operators should assume that logs, network records, endpoint telemetry, access records, cloud audit trails, and service-provider records may be retained and later examined in civil, criminal, institutional, or employment investigations.

Where credentials, tokens, session artifacts, browser data, or other sensitive material may be encountered, operators should apply the minimum necessary handling standard: collect only if clearly authorized, retain only as long as necessary, restrict access, document custody, and securely delete when no longer needed.

---

## Liberia Cybercrime Act, 2021

The following section is a plain-language interpretation of the law text provided by the user for inclusion in this repository. It is included as a practical risk summary for readers, including students and academic users, who may otherwise underestimate how broadly cybercrime laws can apply.

### General Effect of the Act

The Liberia Cybercrime Act, 2021 establishes a broad legal framework for preventing, detecting, investigating, prosecuting, and punishing cyber-related offences in Liberia. It also protects critical national information infrastructure and grants courts and law-enforcement authorities procedural powers to preserve data, compel disclosure, search, seize, intercept, prosecute, and seek forfeiture, restitution, or compensation.

### Broad Meaning of Access and Unauthorized Conduct

Under the definitions reflected in the law text provided, access is broad. It is not limited to signing in or opening a file. It can include viewing, retrieving, copying, moving, altering, erasing, outputting, using, or otherwise making data available or usable.

The concepts of unauthorized access and unauthorized acts are also broad. In practical terms, if a person does not control the relevant access or activity, and does not have consent from someone who is lawfully entitled to give that consent, the conduct may be unauthorized.

For this repository, that means a person may face legal exposure not only for successful compromise, but also for unauthorized deployment, unauthorized command execution, unauthorized monitoring, unauthorized token use, unauthorized data retrieval, or unauthorized modification of systems or files.

### Critical National Information Infrastructure (CNII)

The Act gives enhanced protection to critical national information infrastructure, including systems or networks tied to national security, defense, international relations, communications, banking, finance, public utilities, transportation, public key infrastructure, and emergency services.

Practical interpretation:

- unauthorized access to designated critical infrastructure is treated more seriously than ordinary unauthorized access
- interference with critical systems can trigger severe penalties
- if conduct affecting such infrastructure causes serious bodily injury, penalties increase substantially
- if such conduct results in death, the Act provides for life imprisonment

No student, researcher, or professional user should use this repository against any environment that could plausibly qualify as critical infrastructure unless there is clear legal authority and formal written authorization specifically covering that environment.

### Offences Most Relevant to This Repository

The following categories in the Act are especially relevant to software capable of remote execution, data handling, monitoring, automation, credential use, persistence, or command-and-control style operation.

#### 1. Unlawful Access

The Act criminalizes intentionally accessing all or part of a computer system or infrastructure without authorization or in excess of authorization. Possessing data known to have been unlawfully acquired is also criminalized.

Practical meaning:

- running this repository or its outputs on a machine, account, or server outside approved scope can constitute unlawful access
- access that begins lawfully can still become unlawful if the operator exceeds approved scope or purpose

#### 2. Unlawful Interception of Communications

The Act criminalizes intercepting non-public computer data or transmissions without authorization.

Practical meaning:

- capturing messages, traffic, session data, credentials, tokens, or internal communications without lawful approval may constitute unlawful interception

#### 3. Unauthorized Modification of Data

The Act criminalizes damaging, deleting, deteriorating, altering, or suppressing computer data without authorization.

Practical meaning:

- editing files, deleting data, changing records, modifying logs, or altering system configuration without permission may trigger liability

#### 4. System Interference

The Act criminalizes conduct that seriously hinders the functioning of a computer system by transmitting, damaging, deleting, altering, or suppressing data.

Practical meaning:

- disruption, degradation, shutdown, instability, or operational interference caused by unauthorized use of this repository may be punishable

#### 5. Misuse of Devices

The Act criminalizes producing, supplying, procuring, importing, exporting, distributing, offering, making available, or possessing devices, passwords, access codes, or similar data intended for committing offences under the Act.

Practical meaning:

- tools, scripts, automation, password material, token lists, or access mechanisms can themselves create risk if used or possessed with criminal intent
- credential harvesting or unauthorized retrieval of passwords and access codes is treated particularly seriously

#### 6. Computer-Related Forgery, Fraud, and Identity Theft

The Act criminalizes inputting or altering data to create inauthentic data for legal reliance, causing loss by data manipulation or system interference for economic benefit, sending fraudulent electronic messages, and obtaining or using identity information to deceive or impersonate.

Practical meaning:

- fake records, manipulated logs, phishing, impersonation, spoofed communications, token misuse, or deceptive account activity may create separate offences in addition to any access offence

#### 7. Cyberstalking, Harmful Messages, and Intimate Images

The Act criminalizes threatening, harassing, extorting, cyberstalking, distributing harmful data messages, and distributing intimate images without consent.

Practical meaning:

- using this repository to harass, intimidate, extort, target, embarrass, or surveil individuals is prohibited and may create serious criminal exposure

#### 8. Cyberterrorism and Hateful or Violent Incitement

The Act includes offences relating to cyberterrorism, racist and xenophobic material, and data messages that incite violence or property damage.

Practical meaning:

- any use connected to coercion, terror, extremist propaganda, violent threats, or attacks on public systems materially increases legal risk

#### 9. Attempt, Conspiracy, Aiding, and Abetting

The Act extends liability beyond completed offences. Attempting, preparing, aiding, abetting, or conspiring to commit offences under the Act can be punished as well.

Practical meaning:

- partial deployment, staging infrastructure, preparing delivery, sharing access material, or assisting another operator can still create liability even if the final objective is never completed

#### 10. Corporate and Organizational Liability

The Act permits fines against companies and may expose officers, directors, managers, or similar officials to personal liability in some cases.

Practical meaning:

- misuse within a business, school, research lab, or institution can create consequences for both the organization and responsible individuals

### Investigation and Enforcement Powers

The Act gives Liberian authorities significant powers, including:

- expedited preservation of stored computer data
- disclosure of traffic or subscriber-related information
- production orders for data and records
- search, seizure, and arrest powers
- urgent searches in certain situations without a warrant while judicial review is sought
- interception orders for electronic communications
- duties on service providers to assist or preserve evidence
- contempt and obstruction consequences for non-compliance
- forfeiture of assets, equipment, software, and proceeds
- compensation or restitution orders

Practical interpretation:

- logs, devices, accounts, infrastructure, stored data, and proceeds tied to unlawful conduct may be preserved, compelled, seized, forfeited, or used as evidence
- attempts to conceal evidence, refuse lawful disclosure, or obstruct an investigation can create additional offences

### Jurisdiction and International Cooperation

The Act provides for jurisdiction in Liberia not only for conduct inside Liberia, but also in some circumstances for conduct on Liberian ships or aircraft, conduct by Liberians abroad, and some conduct outside Liberia where the victim is a Liberian citizen or resident or where the alleged offender is present in Liberia and not extradited.

The Act also addresses extradition, mutual legal assistance, preservation requests, evidence sharing, and designated contact points for international cooperation.

Practical interpretation:

- cross-border use of this repository does not eliminate legal exposure
- remote operation, offshore hosting, or foreign infrastructure may still leave operators exposed to Liberian or international enforcement mechanisms

---

## Repository-Specific Interpretation

Because this repository includes code and build material capable of remote execution, data handling, and operator-controlled actions, misuse of the repository may implicate the following categories under the Act, depending on the facts, the authorization in place, and the operator's intent:

- unlawful access
- unlawful interception
- unauthorized modification of data
- system interference
- misuse of devices
- fraud, forgery, or identity theft
- cyberstalking or harmful communications
- attempt, conspiracy, aiding, or abetting

### Practical Rule

- use this repository only under explicit authorization
- ensure authorization identifies the exact systems, accounts, time window, and methods permitted
- avoid any activity affecting uninvolved third parties, production data, public platforms, or critical infrastructure
- stop immediately if legality, scope, or consent is unclear

## Practical Compliance Checklist

Before using this repository, students, instructors, researchers, and professionals should be able to answer yes to each of the following:

- I know who owns the relevant systems, accounts, and data.
- I have clear permission from a person authorized to grant that permission.
- I know exactly what systems and accounts are in scope.
- I know what activities are prohibited even within scope.
- I am working in an isolated lab, sandbox, or otherwise approved environment.
- I understand what logging, monitoring, and evidence retention may occur.
- I will immediately stop if I encounter out-of-scope data, users, or systems.
- My use complies with local law, school or workplace policy, platform terms, and any contract or engagement rules.

If any answer is no, the repository should not be used until the issue is resolved.

## If Something Goes Wrong

If an operator causes unintended impact, observes out-of-scope access, or encounters data that appears outside authorization, the minimum expected response is to:

- stop the activity immediately
- preserve relevant logs, timestamps, commands, and system details
- notify the instructor, supervisor, client, or system owner identified in the authorization record
- avoid further collection, persistence, or alteration unless specifically directed by an authorized incident lead
- document what happened, what systems or accounts were involved, and what containment actions were taken

Silence, concealment, or ad hoc cleanup can increase both legal and disciplinary exposure.

## No Waiver

Nothing in this repository, its documentation, its source code, or this disclaimer authorizes the violation of law, the bypassing of consent, the exceeding of assessment scope, or the disregard of platform, institutional, contractual, or professional restrictions.

## Recommendation

Before operational, classroom, or research use, obtain or confirm:

- written authorization from the system owner or institution
- a rules-of-engagement or acceptable-use document
- a defined scope of work or lab scope
- faculty, supervisor, or client approval where applicable
- legal review appropriate to the jurisdiction involved if the activity is not plainly low-risk classroom work in an isolated lab

If Liberia is a relevant jurisdiction, review the full Cybercrime Act, 2021 and obtain qualified Liberian legal advice.